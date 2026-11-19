"""Inicio sencillo de escritorio con SQLite; no requiere Docker ni MySQL."""
import getpass
import threading
import webbrowser
from app import create_app
from seed import seed
from waitress import serve

if __name__ == '__main__':
    app = create_app({'DB_ENGINE': 'sqlite'})
    with app.db.transaction() as s:
        initialized = bool(s.one('SELECT id FROM users LIMIT 1'))
    if not initialized:
        print('\nPrimera apertura: elige una contraseña para entrar a la página.')
        print('Debe tener al menos 10 caracteres. Al escribirla no se verá en pantalla.')
        while True:
            password = getpass.getpass('Contraseña: ')
            if len(password) < 10:
                print('Necesitas al menos 10 caracteres. Intenta nuevamente.'); continue
            if password != getpass.getpass('Repite la contraseña: '):
                print('Las contraseñas no coinciden. Intenta nuevamente.'); continue
            break
        seed(app, password)
    print('\nUsuario para ingresar: admin')
    print('Contraseña: la que elegiste en la primera apertura.')
    print('Abre http://127.0.0.1:5000 si el navegador no se abre automáticamente.')
    print('DEJA ESTA VENTANA ABIERTA mientras utilizas la página.')
    print('Para detener la aplicación, presiona Ctrl+C. Tus registros quedan guardados.\n')
    timer = threading.Timer(2, lambda: webbrowser.open('http://127.0.0.1:5000'))
    timer.daemon = True
    timer.start()
    serve(app, host='127.0.0.1', port=5000, threads=8)
