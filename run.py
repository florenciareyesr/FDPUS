import argparse
import getpass
import os
from app import create_app
from seed import seed

parser=argparse.ArgumentParser()
parser.add_argument('--seed',action='store_true',help='Inicializar datos ficticios y seis usuarios, una sola vez')
parser.add_argument('--port',type=int,default=5000)
args=parser.parse_args()
app=create_app()
if args.seed or os.getenv('DEMO_PASSWORD'):
    password=os.getenv('DEMO_PASSWORD') or getpass.getpass('Contraseña para los usuarios demo (mínimo 10 caracteres): ')
    print('Datos ficticios creados.' if seed(app,password) else 'La base ya tiene usuarios; no se sobrescribió.')
print(f'FDPUS | Motor: {app.db.engine} | http://127.0.0.1:{args.port}', flush=True)
try:
    from waitress import serve
except ImportError:
    print('Waitress no instalado: servidor local de desarrollo. Instala requirements.txt antes de la entrega.',flush=True)
    app.run(host='127.0.0.1',port=args.port,debug=False)
else:
    serve(app,host='0.0.0.0' if app.db.engine=='mysql' else '127.0.0.1',port=args.port,threads=8)
