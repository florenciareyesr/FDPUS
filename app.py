"""Controladores HTTP y servicios transaccionales de la aplicación FDPUS."""
import csv
import hashlib
import io
import json
import os
import secrets
import time
import uuid
from datetime import date, datetime, timezone
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, request, session, g, send_file, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename
from db import Database
from pdf_report import make_pdf

BASE = Path(__file__).parent
LIMIT = 50 * 1024 * 1024
ROLES = {'admin': 'Administración', 'social': 'Trabajo Social', 'tens': 'TENS',
         'clinico': 'Profesional clínico', 'bodega': 'Bodega', 'direccion': 'Dirección'}
PERMISSIONS = {
 'applications': {'admin','social'}, 'beneficiaries': {'admin','social','tens','clinico','direccion'},
 'edit': {'admin','social'}, 'appointments': {'admin','social','tens','clinico'},
 'schedule': {'admin','tens'}, 'clinical': {'admin','clinico'},
 'warehouse': {'admin','social','bodega'}, 'stock': {'admin','bodega'},
 'reports': {'admin','social','direccion'}, 'audit': {'admin','social','direccion'}
}

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')


class BusinessError(Exception):
    def __init__(self, message, status=400): self.message, self.status = message, status


def required(data, *keys):
    for key in keys:
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise BusinessError('Completa el campo requerido: ' + key)
        if len(data[key]) > (10000 if key in ('evolution','procedures','recommendations','reason') else 200):
            raise BusinessError('Campo demasiado largo: ' + key)
        data[key] = data[key].strip()


def positive(value):
    try:
        if isinstance(value, bool) or str(int(value)) != str(value) or int(value) < 1 or int(value) > 1000000:
            raise ValueError()
        return int(value)
    except (ValueError, TypeError): raise BusinessError('La cantidad debe ser un entero positivo.')


def create_app(config=None):
    app = Flask(__name__, static_folder='static')
    instance = Path((config or {}).get('INSTANCE', BASE / 'instance'))
    instance.mkdir(parents=True, exist_ok=True)
    (instance / 'uploads').mkdir(exist_ok=True)
    keyfile = instance / 'session.key'
    if not keyfile.exists(): keyfile.write_text(secrets.token_hex(32), encoding='utf-8')
    app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or keyfile.read_text(),
        MAX_CONTENT_LENGTH=LIMIT + 1024*1024, SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE') == '1',
        PERMANENT_SESSION_LIFETIME=3600)
    app.config.update(config or {})
    db = Database(instance / 'fdpus.db', app.config.get('DB_ENGINE'))
    db.initialize(); app.db = db
    app.instance_dir = instance
    attempts = {}

    def audit(s, action, entity, before=None, after=None):
        s.insert('audit', dict(id=uid(), actor_id=(getattr(g, 'user', None) or {}).get('id'), action=action,
            entity_id=entity, before_json=json.dumps(before or {}, ensure_ascii=False),
            after_json=json.dumps(after or {}, ensure_ascii=False), created_at=now()))

    def notify(s, role, message, entity):
        s.insert('notifications', dict(id=uid(), role=role, message=message, entity_id=entity, created_at=now()))

    def get(s, table, ident):
        row = s.one(f'SELECT * FROM {table} WHERE id=?', (ident,))
        if not row: raise BusinessError('Registro no encontrado.', 404)
        return row

    def catalog(s, ident, kind, optional=False):
        if not ident and optional: return None
        row = s.one('SELECT * FROM catalogs WHERE id=? AND kind=?', (ident, kind))
        if not row: raise BusinessError('Selecciona una opción válida del catálogo: '+kind)
        return ident

    def active(s, ident):
        b = get(s, 'beneficiaries', ident)
        if b['status'] != 'activo': raise BusinessError('La ficha está cerrada.', 409)
        return b

    def protect(permission=None):
        def decorator(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                if not getattr(g,'user',None): raise BusinessError('Inicia sesión para continuar.', 401)
                if permission and g.user['role'] not in PERMISSIONS[permission]:
                    raise BusinessError('Tu rol no tiene permiso para esta operación.', 403)
                return fn(*args, **kwargs)
            return wrapped
        return decorator

    @app.before_request
    def guard():
        g.user = None
        g.upload_paths = []
        if session.get('user_id'):
            with db.transaction() as s:
                g.user = s.one('SELECT id,username,name,role FROM users WHERE id=?', (session['user_id'],))
        if request.path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
            expected = session.get('csrf')
            if not expected or not secrets.compare_digest(expected, request.headers.get('X-CSRF-Token','')):
                raise BusinessError('Sesión vencida. Recarga la página y vuelve a intentar.', 403)

    @app.after_request
    def headers(response):
        if response.status_code >= 400:
            for path in getattr(g, 'upload_paths', []):
                path.unlink(missing_ok=True)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'"
        if request.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(BusinessError)
    def business_error(e): return jsonify(error=e.message), e.status

    @app.errorhandler(413)
    def too_large(e): return jsonify(error='El archivo supera el límite de 50 MB.'), 413

    @app.errorhandler(Exception)
    def unexpected(e):
        if isinstance(e, HTTPException): return jsonify(error=e.description), e.code
        if 'IntegrityError' in type(e).__name__:
            return jsonify(error='Conflicto: el registro ya existe o la operación viola una relación. Recarga y revisa.'),409
        app.logger.exception('Error interno')
        return jsonify(error='No se pudo completar la operación. Tus cambios no fueron confirmados; puedes reintentar.'),500

    @app.get('/')
    def index(): return send_from_directory(app.static_folder, 'index.html')

    @app.get('/api/session')
    def session_info():
        if 'csrf' not in session: session['csrf'] = secrets.token_hex(24)
        return jsonify(user=g.user, csrf=session['csrf'], roles=ROLES,
                       permissions=[k for k,v in PERMISSIONS.items() if g.user and g.user['role'] in v], engine=db.engine)

    @app.post('/api/login')
    def login():
        data = request.get_json() or {}; required(data,'username','password')
        key = (request.remote_addr, data['username'].lower())
        recent = [t for t in attempts.get(key,[]) if t > time.monotonic()-300]
        if len(recent)>=8: raise BusinessError('Demasiados intentos. Espera cinco minutos.',429)
        with db.transaction() as s: user = s.one('SELECT * FROM users WHERE username=?',(data['username'].lower(),))
        if not user or not check_password_hash(user['password_hash'],data['password']):
            attempts[key]=recent+[time.monotonic()]
            raise BusinessError('Usuario o contraseña incorrectos.',401)
        attempts.pop(key,None); session.clear(); session.permanent=True
        session['user_id']=user['id']; session['csrf']=secrets.token_hex(24)
        return jsonify(ok=True)

    @app.post('/api/logout')
    def logout(): session.clear(); return jsonify(ok=True)

    def upload(s, file, application_id=None, beneficiary_id=None):
        if not file or not file.filename: raise BusinessError('Adjunta el informe o respaldo PDF requerido.')
        name = secure_filename(file.filename)[:180]
        if not name.lower().endswith('.pdf'): raise BusinessError('Solo se admiten documentos PDF.')
        content = file.read(LIMIT+1)
        if len(content)>LIMIT: raise BusinessError('El archivo supera el límite de 50 MB.',413)
        if not content.startswith(b'%PDF-') or b'%%EOF' not in content[-2048:]:
            raise BusinessError('El archivo no tiene una estructura PDF reconocible.')
        ident=uid(); path=ident+'.pdf'; destination=instance/'uploads'/path
        destination.write_bytes(content)
        g.upload_paths.append(destination)
        try:
            s.insert('documents',dict(id=ident, application_id=application_id, beneficiary_id=beneficiary_id,
                name=name,path=path,size_bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),created_at=now()))
        except Exception:
            destination.unlink(missing_ok=True); raise
        return ident

    @app.post('/api/applications')
    def apply():
        data=request.form.to_dict()
        fields=['run','names','surnames','birth','guardian','phone','email','address','region','commune']
        required(data,*fields)
        try:
            born=date.fromisoformat(data['birth'])
            if born>date.today(): raise ValueError()
        except ValueError: raise BusinessError('Fecha de nacimiento inválida.')
        if '@' not in data['email'] or len(data['email'])>120: raise BusinessError('Correo inválido.')
        for key,maxlen in {'run':32,'names':100,'surnames':100,'guardian':120,'phone':32,'region':100,'commune':100}.items():
            if len(data[key])>maxlen: raise BusinessError('Campo demasiado largo: '+key)
        if data.get('consent')!='1': raise BusinessError('Debes aceptar el uso de los datos para evaluar la postulación.')
        ident=uid(); row={k:data[k] for k in fields}; row['run']=row['run'].upper().replace(' ','')
        row.update(id=ident,status='pendiente',reason='',created_at=now())
        with db.transaction() as s:
            s.insert('applications',row); upload(s,request.files.get('document'),application_id=ident)
            notify(s,'social','Nueva postulación recibida: '+row['names'],ident)
            audit(s,'postulacion.creada',ident,after={'status':'pendiente'})
        return jsonify(id=ident,message='Postulación recibida. Conserva este comprobante; será revisada por Trabajo Social.'),201

    @app.get('/api/applications')
    @protect('applications')
    def applications():
        with db.transaction() as s:
            return jsonify(s.all('SELECT * FROM applications ORDER BY created_at DESC'))

    @app.get('/api/applications/<ident>')
    @protect('applications')
    def application_detail(ident):
        with db.transaction() as s:
            row=get(s,'applications',ident)
            row['documents']=s.all('SELECT id,name,size_bytes FROM documents WHERE application_id=?',(ident,))
            return jsonify(row)

    @app.post('/api/applications/<ident>/decision')
    @protect('applications')
    def decide(ident):
        data=request.get_json() or {}; decision=data.get('decision')
        if decision not in ('aprobar','rechazar'): raise BusinessError('Decisión inválida.')
        if decision=='rechazar': required(data,'reason')
        with db.transaction() as s:
            row=get(s,'applications',ident)
            status='aprobada' if decision=='aprobar' else 'rechazada'
            changed=s.execute('UPDATE applications SET status=?,reason=? WHERE id=? AND status=?',
                (status,data.get('reason',''),ident,'pendiente')).rowcount
            if changed!=1: raise BusinessError('La postulación ya fue evaluada.',409)
            beneficiary_id=None
            if decision=='aprobar':
                if s.one('SELECT id FROM beneficiaries WHERE active_run=?',(row['run'],)):
                    raise BusinessError('Ya existe una ficha activa para esta identificación.',409)
                beneficiary_id=uid()
                fields=['run','names','surnames','birth','guardian','phone','email','address','region','commune']
                b={k:row[k] for k in fields}
                b.update(id=beneficiary_id, application_id=ident, active_run=row['run'],
                    diagnosis_id=None,insurance_id=None,electro=0,status='activo',close_reason='',created_at=now(),version=1)
                s.insert('beneficiaries',b)
                s.execute('UPDATE documents SET beneficiary_id=? WHERE application_id=?',(beneficiary_id,ident))
                audit(s,'ficha.creada',beneficiary_id,after=b)
            audit(s,'postulacion.'+status,ident,before={'status':row['status']},after={'status':status,'reason':data.get('reason','')})
        return jsonify(ok=True,beneficiary_id=beneficiary_id)

    @app.get('/api/catalogs')
    @protect('beneficiaries')
    def catalogs():
        with db.transaction() as s: return jsonify(s.all('SELECT * FROM catalogs ORDER BY kind,label'))

    @app.post('/api/catalogs')
    @protect('edit')
    def create_catalog():
        data=request.get_json() or {}; required(data,'kind','label')
        if data['kind'] not in ('diagnosis','insurance','specialty','absence','closure') or len(data['label'])>120:
            raise BusinessError('Catálogo inválido.')
        row=dict(id=uid(),kind=data['kind'],label=data['label'])
        with db.transaction() as s: s.insert('catalogs',row); audit(s,'catalogo.creado',row['id'],after=row)
        return jsonify(row),201

    @app.get('/api/beneficiaries')
    @protect('beneficiaries')
    def beneficiaries():
        sql='SELECT * FROM beneficiaries WHERE 1=1'; args=[]
        for key in ('region','commune','status'):
            if request.args.get(key): sql+=' AND '+key+'=?'; args.append(request.args[key])
        if request.args.get('electro')=='1': sql+=' AND electro=1'
        if request.args.get('q'):
            sql+=' AND (LOWER(names) LIKE ? OR LOWER(surnames) LIKE ? OR LOWER(run) LIKE ?)'
            args.extend(['%'+request.args['q'].lower()+'%']*3)
        with db.transaction() as s: return jsonify(s.all(sql+' ORDER BY surnames,names',args))

    @app.get('/api/beneficiaries/<ident>')
    @protect('beneficiaries')
    def beneficiary_detail(ident):
        with db.transaction() as s:
            b=get(s,'beneficiaries',ident)
            b['documents']=s.all('SELECT id,name,size_bytes,sha256 FROM documents WHERE beneficiary_id=?',(ident,))
            b['appointments']=s.all('SELECT a.*,u.name professional FROM appointments a JOIN users u ON u.id=a.professional_id WHERE beneficiary_id=? ORDER BY scheduled_at DESC',(ident,))
            b['aids']=s.all('SELECT a.*,i.name item FROM aids a JOIN items i ON i.id=a.item_id WHERE beneficiary_id=? ORDER BY created_at DESC',(ident,))
            b['history']=s.all('SELECT a.*,u.name actor FROM audit a LEFT JOIN users u ON u.id=a.actor_id WHERE entity_id=? ORDER BY created_at DESC',(ident,)) if g.user['role'] in PERMISSIONS['audit'] else []
            return jsonify(b)

    @app.put('/api/beneficiaries/<ident>')
    @protect('edit')
    def edit_beneficiary(ident):
        data=request.get_json() or {}
        fields=['names','surnames','guardian','phone','email','address','region','commune']
        required(data,*fields)
        for key,maxlen in {'names':100,'surnames':100,'guardian':120,'phone':32,'email':120,'region':100,'commune':100}.items():
            if len(data[key])>maxlen: raise BusinessError('Campo demasiado largo: '+key)
        if '@' not in data['email']: raise BusinessError('Correo inválido.')
        with db.transaction() as s:
            before=active(s,ident)
            diagnosis=catalog(s,data.get('diagnosis_id'),'diagnosis',True)
            insurance=catalog(s,data.get('insurance_id'),'insurance',True)
            values={k:data[k] for k in fields}; values.update(diagnosis_id=diagnosis,insurance_id=insurance,electro=int(bool(data.get('electro'))))
            if str(data.get('version'))!=str(before['version']): raise BusinessError('Otro usuario modificó esta ficha. Recarga antes de guardar.',409)
            assignments=','.join(k+'=?' for k in values)
            changed=s.execute(f'UPDATE beneficiaries SET {assignments},version=version+1 WHERE id=? AND version=?',
                list(values.values())+[ident,before['version']]).rowcount
            if changed!=1: raise BusinessError('La ficha cambió. Recarga y reintenta.',409)
            audit(s,'ficha.corregida',ident,before={k:before[k] for k in values},after=values)
        return jsonify(ok=True)

    @app.post('/api/beneficiaries/<ident>/documents')
    @protect('edit')
    def add_document(ident):
        with db.transaction() as s:
            active(s,ident); doc=upload(s,request.files.get('document'),beneficiary_id=ident)
            audit(s,'documento.adjunto',ident,after={'document_id':doc})
        return jsonify(id=doc),201

    @app.post('/api/beneficiaries/<ident>/close')
    @protect('edit')
    def close(ident):
        with db.transaction() as s:
            before=active(s,ident); causal=catalog(s,request.form.get('closure_id'),'closure')
            if s.one("SELECT id FROM aids WHERE beneficiary_id=? AND status!='entregada'",(ident,)):
                raise BusinessError('Resuelve las ayudas pendientes antes de cerrar la ficha.',409)
            if s.one("SELECT id FROM appointments WHERE beneficiary_id=? AND status='programada'",(ident,)):
                raise BusinessError('Resuelve las citas programadas antes de cerrar la ficha.',409)
            doc=upload(s,request.files.get('document'),beneficiary_id=ident)
            reason=get(s,'catalogs',causal)['label']
            s.execute('UPDATE beneficiaries SET status=?,active_run=NULL,close_reason=?,version=version+1 WHERE id=?',('cerrado',reason,ident))
            audit(s,'ficha.baja',ident,before={'status':before['status']},after={'status':'cerrado','reason':reason,'document_id':doc})
        return jsonify(ok=True)

    @app.get('/api/documents/<ident>')
    @protect('beneficiaries')
    def document(ident):
        with db.transaction() as s:
            d=get(s,'documents',ident)
            if not d['beneficiary_id'] and g.user['role'] not in PERMISSIONS['applications']:
                raise BusinessError('No tienes acceso a documentos de postulaciones.',403)
        return send_file(instance/'uploads'/d['path'],download_name=d['name'],as_attachment=True,mimetype='application/pdf')

    @app.get('/api/professionals')
    @protect('appointments')
    def professionals():
        with db.transaction() as s: return jsonify(s.all("SELECT id,name FROM users WHERE role='clinico' ORDER BY name"))

    @app.get('/api/appointments')
    @protect('appointments')
    def appointments():
        with db.transaction() as s:
            return jsonify(s.all('SELECT a.*,b.names,b.surnames,u.name professional FROM appointments a JOIN beneficiaries b ON b.id=a.beneficiary_id JOIN users u ON u.id=a.professional_id ORDER BY scheduled_at DESC'))

    @app.post('/api/appointments')
    @protect('schedule')
    def schedule():
        data=request.get_json() or {}; required(data,'beneficiary_id','professional_id','scheduled_at','modality')
        if data['modality'] not in ('Domiciliaria','Presencial','Teleatención'): raise BusinessError('Modalidad inválida.')
        try: datetime.fromisoformat(data['scheduled_at'])
        except ValueError: raise BusinessError('Fecha de cita inválida.')
        with db.transaction() as s:
            active(s,data['beneficiary_id']); p=get(s,'users',data['professional_id'])
            if p['role']!='clinico': raise BusinessError('Selecciona un profesional clínico.')
            row={k:data[k] for k in ('beneficiary_id','professional_id','scheduled_at','modality')}
            row.update(id=uid(),status='programada',specialty_id=None,evolution='',procedures='',recommendations='',absence_id=None,completed_at=None)
            s.insert('appointments',row); audit(s,'cita.agendada',row['beneficiary_id'],after=row)
        return jsonify(row),201

    @app.post('/api/appointments/<ident>/complete')
    @protect('clinical')
    def complete(ident):
        data=request.get_json() or {}; status=data.get('status')
        if status not in ('atendida','no_atendida'): raise BusinessError('Estado inválido.')
        with db.transaction() as s:
            a=get(s,'appointments',ident); active(s,a['beneficiary_id'])
            if g.user['role']=='clinico' and a['professional_id']!=g.user['id']: raise BusinessError('Solo el profesional asignado puede registrar esta atención.',403)
            specialty=absence=None
            if status=='atendida':
                required(data,'evolution','procedures','recommendations'); specialty=catalog(s,data.get('specialty_id'),'specialty')
            else: absence=catalog(s,data.get('absence_id'),'absence')
            changed=s.execute('UPDATE appointments SET status=?,specialty_id=?,evolution=?,procedures=?,recommendations=?,absence_id=?,completed_at=? WHERE id=? AND status=?',
                (status,specialty,data.get('evolution','') if status=='atendida' else '',data.get('procedures','') if status=='atendida' else '',data.get('recommendations','') if status=='atendida' else '',absence,now(),ident,'programada')).rowcount
            if changed!=1: raise BusinessError('La cita ya fue resuelta.',409)
            b=get(s,'beneficiaries',a['beneficiary_id'])
            notify(s,'social',('Atención realizada: ' if status=='atendida' else 'Seguimiento requerido por atención no realizada: ')+b['names']+' '+b['surnames']+' · sesión '+ident, a['beneficiary_id'])
            audit(s,'atencion.'+status,a['beneficiary_id'],before=a,after=get(s,'appointments',ident))
        return jsonify(ok=True)

    @app.get('/api/items')
    @protect('warehouse')
    def items():
        with db.transaction() as s: return jsonify(s.all('SELECT * FROM items ORDER BY name'))

    @app.post('/api/items')
    @protect('stock')
    def create_item():
        data=request.get_json() or {}; required(data,'name','unit')
        if len(data['name'])>120 or len(data['unit'])>32: raise BusinessError('Nombre o unidad demasiado largo.')
        row=dict(id=uid(),name=data['name'],unit=data['unit'],stock=0)
        with db.transaction() as s: s.insert('items',row); audit(s,'insumo.creado',row['id'],after=row)
        return jsonify(row),201

    @app.post('/api/items/<ident>/receive')
    @protect('stock')
    def receive(ident):
        data=request.get_json() or {}; quantity=positive(data.get('quantity')); required(data,'note')
        with db.transaction() as s:
            get(s,'items',ident); s.execute('UPDATE items SET stock=stock+? WHERE id=?',(quantity,ident))
            s.insert('movements',dict(id=uid(),item_id=ident,aid_id=None,quantity=quantity,kind='ingreso',note=data['note'],actor_id=g.user['id'],created_at=now()))
            audit(s,'stock.ingreso',ident,after={'quantity':quantity})
        return jsonify(ok=True)

    @app.get('/api/aids')
    @protect('warehouse')
    def aids():
        with db.transaction() as s:
            return jsonify(s.all('SELECT a.*,i.name item,i.stock,b.names,b.surnames,b.guardian,b.address,b.commune,b.phone FROM aids a JOIN items i ON i.id=a.item_id JOIN beneficiaries b ON b.id=a.beneficiary_id ORDER BY a.created_at DESC'))

    @app.post('/api/aids')
    @protect('edit')
    def assign():
        data=request.get_json() or {}; quantity=positive(data.get('quantity')); required(data,'beneficiary_id','item_id')
        with db.transaction() as s:
            b=active(s,data['beneficiary_id']); item=get(s,'items',data['item_id'])
            row=dict(id=uid(),beneficiary_id=b['id'],item_id=item['id'],quantity=quantity,status='asignada',created_at=now(),delivered_at=None)
            s.insert('aids',row)
            notify(s,'bodega',f"Asignación: {quantity} {item['name']} · Apoderado: {b['guardian']} · {b['address']}, {b['commune']} · Tel. {b['phone']}",row['id'])
            audit(s,'ayuda.asignada',b['id'],after=row)
        return jsonify(row),201

    @app.post('/api/aids/<ident>/status')
    @protect('stock')
    def aid_status(ident):
        data=request.get_json() or {}; target=data.get('status')
        with db.transaction() as s:
            a=get(s,'aids',ident)
            allowed={'asignada':['preparada'],'preparada':['despachada'],'despachada':['entregada'],'sin_stock':['preparada']}
            if target not in allowed.get(a['status'],[]): raise BusinessError('Transición inválida o entrega ya registrada.',409)
            if s.execute('UPDATE aids SET status=? WHERE id=? AND status=?',(target,ident,a['status'])).rowcount!=1:
                raise BusinessError('La ayuda fue modificada por otro usuario.',409)
            if target=='entregada':
                changed=s.execute('UPDATE items SET stock=stock-? WHERE id=? AND stock>=?',(a['quantity'],a['item_id'],a['quantity'])).rowcount
                if changed!=1:
                    s.execute("UPDATE aids SET status='sin_stock' WHERE id=?",(ident,))
                    notify(s,'social','Ayuda pendiente por falta de stock: '+ident,a['beneficiary_id'])
                    audit(s,'ayuda.sin_stock',a['beneficiary_id'],after={'aid_id':ident})
                    return jsonify(error='Stock insuficiente. La ayuda queda pendiente y Trabajo Social fue notificado.'),409
                s.execute('UPDATE aids SET delivered_at=? WHERE id=?',(now(),ident))
                s.insert('movements',dict(id=uid(),item_id=a['item_id'],aid_id=ident,quantity=a['quantity'],kind='egreso',note='Entrega efectiva',actor_id=g.user['id'],created_at=now()))
            audit(s,'ayuda.'+target,a['beneficiary_id'],before={'status':a['status']},after={'status':target,'aid_id':ident})
        return jsonify(ok=True)

    @app.get('/api/movements')
    @protect('warehouse')
    def movements():
        with db.transaction() as s:
            return jsonify(s.all('SELECT m.*,i.name item,u.name actor FROM movements m JOIN items i ON i.id=m.item_id JOIN users u ON u.id=m.actor_id ORDER BY created_at DESC'))

    @app.get('/api/notifications')
    @protect()
    def notifications():
        with db.transaction() as s:
            sql='SELECT n.*,r.user_id read_by FROM notifications n LEFT JOIN notification_reads r ON r.notification_id=n.id AND r.user_id=?'
            args=[g.user['id']]
            if g.user['role']!='admin': sql+=' WHERE n.role=?'; args.append(g.user['role'])
            return jsonify(s.all(sql+' ORDER BY created_at DESC',args))

    @app.post('/api/notifications/<ident>/read')
    @protect()
    def read_notification(ident):
        with db.transaction() as s:
            n=get(s,'notifications',ident)
            if g.user['role'] not in ('admin',n['role']): raise BusinessError('Sin permiso.',403)
            if not s.one('SELECT * FROM notification_reads WHERE notification_id=? AND user_id=?',(ident,g.user['id'])):
                s.insert('notification_reads',dict(notification_id=ident,user_id=g.user['id']))
        return jsonify(ok=True)

    @app.get('/api/dashboard')
    @protect()
    def dashboard():
        with db.transaction() as s:
            result={}
            if g.user['role'] in PERMISSIONS['beneficiaries']:
                result['active']=s.one("SELECT COUNT(*) n FROM beneficiaries WHERE status='activo'")['n']
                result['closed']=s.one("SELECT COUNT(*) n FROM beneficiaries WHERE status='cerrado'")['n']
                result['sessions']=s.all("SELECT SUBSTR(scheduled_at,1,7) month,COUNT(*) total FROM appointments WHERE status='atendida' GROUP BY SUBSTR(scheduled_at,1,7) ORDER BY month")
            if g.user['role'] in PERMISSIONS['applications']:
                result['pending']=s.one("SELECT COUNT(*) n FROM applications WHERE status='pendiente'")['n']
            if g.user['role'] in PERMISSIONS['warehouse']:
                result['aids_pending']=s.one("SELECT COUNT(*) n FROM aids WHERE status!='entregada'")['n']
            return jsonify(result)

    def report_rows(s):
        start=request.args.get('start',''); end=request.args.get('end','')
        try:
            date.fromisoformat(start); date.fromisoformat(end)
            if start>end: raise ValueError()
        except ValueError: raise BusinessError('Selecciona un período válido: inicio anterior o igual al fin.')
        sql="SELECT a.id,a.scheduled_at,a.status,a.modality,b.run,b.names,b.surnames,b.region,b.commune,u.name professional FROM appointments a JOIN beneficiaries b ON b.id=a.beneficiary_id JOIN users u ON u.id=a.professional_id WHERE SUBSTR(a.scheduled_at,1,10)>=? AND SUBSTR(a.scheduled_at,1,10)<=?"
        args=[start,end]
        for key in ('region','commune'):
            if request.args.get(key): sql+=' AND b.'+key+'=?'; args.append(request.args[key])
        if request.args.get('status'): sql+=' AND a.status=?'; args.append(request.args['status'])
        return s.all(sql+' ORDER BY a.scheduled_at,a.id',args)

    @app.get('/api/reports')
    @protect('reports')
    def reports():
        with db.transaction() as s: rows=report_rows(s)
        return jsonify(rows=rows,total=len(rows),message='' if rows else 'No hay resultados para los filtros seleccionados.')

    @app.get('/api/reports/export')
    @protect('reports')
    def export_report():
        with db.transaction() as s: rows=report_rows(s)
        if not rows: raise BusinessError('No hay resultados para exportar.',404)
        if request.args.get('format')=='csv':
            output=io.StringIO(); writer=csv.DictWriter(output,fieldnames=list(rows[0])); writer.writeheader()
            for row in rows:
                writer.writerow({k: ('\''+str(v) if str(v).startswith(('=','+','-','@','\t','\r')) else v) for k,v in row.items()})
            return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),download_name='reporte_atenciones.csv',as_attachment=True,mimetype='text/csv')
        lines=[f"Período: {request.args['start']} a {request.args['end']} | Registros: {len(rows)}",'Formato de gestión propuesto; requiere validación ministerial.']
        for r in rows: lines.append(' | '.join(str(v) for v in r.values()))
        return send_file(io.BytesIO(make_pdf('Reporte de atenciones',lines)),download_name='reporte_atenciones.pdf',as_attachment=True,mimetype='application/pdf')

    @app.get('/api/beneficiaries/<ident>/pdf')
    @protect('reports')
    def beneficiary_pdf(ident):
        with db.transaction() as s:
            b=get(s,'beneficiaries',ident)
            diag=s.one('SELECT label FROM catalogs WHERE id=?',(b['diagnosis_id'],))
            insurance=s.one('SELECT label FROM catalogs WHERE id=?',(b['insurance_id'],))
            lines=[f"Identificación: {b['run']} | Estado: {b['status']}",f"Nombre: {b['names']} {b['surnames']}",f"Nacimiento: {b['birth']}",
                f"Apoderado: {b['guardian']} | Teléfono: {b['phone']}",f"Correo: {b['email']}",f"Dirección: {b['address']}, {b['commune']}, {b['region']}",
                'Diagnóstico: '+(diag['label'] if diag else 'Sin registrar'),'Previsión: '+(insurance['label'] if insurance else 'Sin registrar'),f"Electrodependencia: {'Sí' if b['electro'] else 'No'}",'', 'HISTORIAL CLÍNICO']
            for a in s.all('SELECT a.*,u.name professional,c.label specialty FROM appointments a JOIN users u ON u.id=a.professional_id LEFT JOIN catalogs c ON c.id=a.specialty_id WHERE beneficiary_id=? ORDER BY scheduled_at',(ident,)):
                lines.extend([f"{a['scheduled_at']} | {a['professional']} | {a['status']} | {a['specialty'] or ''}", 'Evolución: '+a['evolution'],'Procedimientos: '+a['procedures'],'Recomendaciones: '+a['recommendations']])
            lines.extend(['','AYUDAS'])
            for a in s.all('SELECT a.*,i.name item FROM aids a JOIN items i ON i.id=a.item_id WHERE beneficiary_id=?',(ident,)):
                lines.append(f"{a['item']} | Cantidad: {a['quantity']} | {a['status']} | {a['delivered_at'] or ''}")
        return send_file(io.BytesIO(make_pdf('Ficha consolidada',lines)),download_name='ficha_'+b['run']+'.pdf',as_attachment=True,mimetype='application/pdf')

    @app.get('/api/audit')
    @protect('audit')
    def audit_list():
        with db.transaction() as s:
            return jsonify(s.all('SELECT a.*,u.name actor FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY created_at DESC LIMIT 500'))

    return app
