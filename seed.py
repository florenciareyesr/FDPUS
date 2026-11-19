"""Datos ficticios de demostración. Ejecución explícita e idempotente."""
import os
from app import uid, now, ROLES
from werkzeug.security import generate_password_hash
from pdf_report import make_pdf
import hashlib


def seed(app, password):
    if len(password)<10: raise ValueError('Usa una contraseña de demostración de al menos 10 caracteres.')
    with app.db.transaction() as s:
        if s.one('SELECT id FROM users LIMIT 1'): return False
        users={}
        for role,label in ROLES.items():
            ident=uid(); users[role]=ident
            s.insert('users',dict(id=ident,username=role,name=label+' Demo',role=role,password_hash=generate_password_hash(password)))
        cats={}
        for kind,labels in {'diagnosis':['Diagnóstico de prueba A','Diagnóstico de prueba B'],
          'insurance':['Fonasa','Isapre','Sin previsión'], 'specialty':['Kinesiología','Enfermería','Medicina'],
          'absence':['Ausencia del beneficiario','Reagendamiento solicitado','Imposibilidad de acceso'],
          'closure':['Alta del programa','Renuncia voluntaria','Fallecimiento','Derivación']}.items():
            for label in labels:
                ident=uid(); cats[label]=ident; s.insert('catalogs',dict(id=ident,kind=kind,label=label))
        for n,(name,surname,commune,region) in enumerate([
            ('Martín Alejandro','González Pérez','La Florida','Metropolitana'),
            ('Mateo Andrés','Contreras Ríos','Viña del Mar','Valparaíso'),
            ('Sofía Elena','Fuentes Lagos','Concepción','Biobío'),
            ('Valentina','Pérez Soto','San Felipe','Valparaíso')],1):
            ident=uid(); fields=dict(run=f'DEMO-NNA-{n:03}',names=name,surnames=surname,birth='2016-03-15',
                guardian=f'Apoderado ficticio {n}',phone='+56000000000',email=f'demo{n}@example.invalid',
                address=f'Calle de demostración {n}',region=region,commune=commune)
            s.insert('applications',dict(id=ident,**fields,status='aprobada' if n<4 else 'pendiente',reason='',created_at=now()))
            bid=uid() if n<4 else None
            if bid:
                s.insert('beneficiaries',dict(id=bid,application_id=ident,**fields,active_run=fields['run'],
                    diagnosis_id=cats['Diagnóstico de prueba A'],insurance_id=cats['Fonasa'],electro=int(n==1),
                    status='activo',close_reason='',created_at=now(),version=1))
                s.insert('appointments',dict(id=uid(),beneficiary_id=bid,professional_id=users['clinico'],
                    scheduled_at='2026-11-20T10:00',modality='Domiciliaria',status='programada',specialty_id=None,
                    evolution='',procedures='',recommendations='',absence_id=None,completed_at=None))
            did=uid(); content=make_pdf('Informe médico ficticio',['Documento sintético de demostración; no corresponde a una persona real.'])
            (app.instance_dir/'uploads'/(did+'.pdf')).write_bytes(content)
            s.insert('documents',dict(id=did,application_id=ident,beneficiary_id=bid,name='informe_demo.pdf',path=did+'.pdf',
                size_bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),created_at=now()))
        for name,unit in [('Pañales','paquete'),('Suplemento nutricional','unidad'),('Kit de higiene','kit')]:
            item=uid(); s.insert('items',dict(id=item,name=name,unit=unit,stock=5))
            s.insert('movements',dict(id=uid(),item_id=item,aid_id=None,quantity=5,kind='ingreso',note='Carga ficticia inicial',actor_id=users['admin'],created_at=now()))
    return True
