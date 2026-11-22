# FDPUS · Gestión Institucional

Aplicación web desarrollada para Fundación Deportistas por un Sueño, reconstruida a partir de la propuesta original de la institución.

Autores: Florencia Reyes y Matías Ramírez

## Descripción

La aplicación gestiona procesos asociados a la atención de beneficiarios de la fundación, incluyendo postulaciones, fichas de beneficiarios, registro clínico, inventario, ayudas sociales, reportes y auditoría.

La interfaz mantiene la identidad visual de la página original de la fundación: cabecera amarilla, texto azul oscuro, tarjetas blancas, botones azules y verdes, y pie de página rojo.

## Casos de uso implementados
CU-01: Gestión de postulaciones.
CU-02: Gestión de beneficiarios.
CU-03: Registro y seguimiento de atenciones.
CU-05: Gestión de ayudas e inventario.
CU-06: Reportes y documentación.

Nota: Los datos incluidos en esta entrega son completamente ficticios y se utilizan únicamente para fines académicos.

# Inicio rápido
## Opción recomendada: abrir con doble clic en Windows
### Requisitos
Python 3.11 o superior.
Conexión a internet durante la primera ejecución.
### Pasos
1. Descomprimir completamente el archivo ZIP del proyecto.
2. Ejecutar el archivo: ABRIR_PAGINA.bat
3. Durante la primera ejecución:
- Se solicitará crear una contraseña de al menos 10 caracteres.
- La contraseña deberá ingresarse dos veces para confirmación.
- Los caracteres no serán visibles mientras se escriben.
4. Una vez completada la configuración, el navegador se abrirá automáticamente.

### Consideraciones
Mantener abierta la ventana de inicio mientras la aplicación esté en uso.
Para futuras ejecuciones, volver a abrir ABRIR_PAGINA.bat.
Los datos quedan almacenados localmente en: instance/
Esta modalidad utiliza SQLite, no requiere Docker ni MySQL

# Opción B: Ejecutar con Docker y MySQL
## Requisitos
Docker Desktop instalado (incluyendo Docker Compose).
Conexión a internet para descargar imágenes y dependencias.
Navegador web actualizado.
No es necesario instalar Python ni MySQL de forma independiente.

## Instalación y ejecución
1. Descomprimir el proyecto
Descomprime completamente el archivo ZIP del proyecto en una carpeta local.

2. Abrir una terminal
Abre PowerShell dentro de la carpeta raíz del proyecto (la carpeta que contiene compose.yaml).

3. Crear el archivo de configuración
Copy-Item .env.example .env
notepad .env

4. Configurar credenciales
Edita el archivo .env y reemplaza todos los valores marcados como CAMBIAR.

5. Iniciar los contenedores
docker compose up --build -d
docker compose logs -f app
   
6. Abrir la aplicación
Cuando en los registros aparezca: FDPUS | Motor: mysql
Abrir en el navegador: http://localhost:5000
