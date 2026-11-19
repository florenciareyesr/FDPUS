# FDPUS · Gestión institucional

Aplicación reconstruida para Fundación Deportistas por un Sueño. Equipo académico indicado en la matriz: Florencia Reyes y Matías Ramírez. Interfaz basada en las capturas proporcionadas: cabecera amarilla, texto azul oscuro, tarjetas blancas, botones azules/verdes y pie rojo.

**Empieza por esta guía.** La aplicación ejecuta CU-01, CU-02, CU-03, CU-05 y CU-06. CU-04 y RF-09/10/11/15 se excluyen según la matriz vigente del 18/11/2026. Los datos iniciales son ficticios. Las cifras del dashboard se calculan desde la base de datos.

## Abrir con doble clic en Windows (opción sencilla)

Descomprime todo el ZIP y abre `ABRIR_PAGINA.bat`. Requiere Python 3.11 o superior instalado y conexión a internet en la primera instalación. El archivo prepara los componentes automáticamente. La primera vez te pide elegir y repetir una contraseña de al menos 10 caracteres (no se ve mientras escribes). Luego abre el navegador: entra con usuario `admin` y esa contraseña.

Mantén la ventana de inicio abierta mientras utilizas la página. Para volver a abrir otro día, usa el mismo archivo. Los datos quedan guardados localmente en `instance/`. Esta modalidad usa SQLite, sin Docker ni MySQL; no acredita una integración MySQL ante el docente. Si el navegador no abre automáticamente, entra a http://127.0.0.1:5000 después de iniciar.

## Estado de esta entrega

- Implementados: postulaciones públicas con adjunto, evaluación y creación de ficha, catálogos, correcciones auditadas, documentos, bajas con respaldo, agenda, registro clínico, avisos internos, inventario, entregas, PDF y CSV filtrado.
- Validación ejecutada: consultar `docs/evidencias/results.json` y `docs/ESTADO_VALIDACION.md`.
- MySQL: adaptador y configuración Docker incluidos. Su ejecución está **pendiente en un equipo con Docker/MySQL**, no se presenta como probada aquí.
- Revisión visual e interacción en navegador: pendiente; el entorno que construyó el proyecto bloqueó sockets locales.
- La rúbrica Excel no pudo leerse. Se utilizó el instructivo y las matrices legibles. No se certifica una nota ni cumplimiento completo de criterios no accesibles.
- El reporte ministerial es un formato de gestión propuesto. Hace falta la plantilla oficial y validación de la contraparte para afirmar conformidad ministerial.

## Opción A · Ejecutar con MySQL (configuración para la entrega)

Requisitos: Docker Desktop con Compose, conectado a internet para descargar imágenes y dependencias; navegador actualizado. No hace falta instalar Python ni MySQL aparte.

1. Descomprime este proyecto. Abre PowerShell **dentro de la carpeta que contiene `compose.yaml`**.
2. Copia el archivo de ejemplo:

```powershell
Copy-Item .env.example .env
notepad .env
```

3. Cambia las cinco claves/valores de ejemplo que indican CAMBIAR. `DEMO_PASSWORD` debe tener al menos 10 caracteres. No dejes contraseñas de ejemplo. Mantén `MYSQL_DATABASE=fdpus` y `MYSQL_USER=fdpus_app`.
4. Ejecuta:

```powershell
docker compose up --build -d
docker compose logs -f app
```

5. Cuando aparezca `FDPUS | Motor: mysql`, abre **http://localhost:5000**. Ctrl+C sale de la vista de logs sin detener los contenedores.
6. Entra como `admin` con la contraseña que configuraste en `DEMO_PASSWORD`. La primera ejecución crea seis usuarios y datos ficticios; siguientes arranques no los duplican.

Para detener: `docker compose down`. Los volúmenes conservan la base y los documentos. **No uses `down -v` salvo que quieras eliminar todos los datos de ese entorno.**

Si la base aún inicia, espera a que el servicio `db` esté sano: `docker compose ps`. Si cambias claves en `.env` después de inicializar el volumen, eso no cambia las contraseñas existentes dentro de MySQL: coordina la rotación en el motor.

### Probar la integración MySQL antes de grabar

```powershell
docker compose --profile test run --build --rm tests
```

La prueba usa `db_test`, una base temporal separada llamada `fdpus_test`; no toca la base `fdpus`. La salida contiene JSON de resultados reales. Guárdala como evidencia y revisa `passed: true`. No marques pruebas MySQL como aprobadas hasta ejecutar este comando. La batería borra y recrea datos **solo en la base de pruebas** en cada caso.

## Opción B · Revisión local rápida con SQLite

Requisitos: Python 3.11 o superior, internet para instalar dependencias y navegador. SQLite se incluye con Python. Esta opción prueba la misma lógica, pero **no acredita el requisito técnico MySQL**.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py --seed
```

Ingresa una contraseña de al menos 10 caracteres cuando se solicite. Abre **http://127.0.0.1:5000**. Usa `admin` y esa contraseña. En siguientes ejecuciones: `.\.venv\Scripts\python.exe run.py`.

La base SQLite, documentos y clave de sesión están en `instance/`, excluida de Git. Para reiniciar la demostración sin perderla, detén el servidor, mueve `instance/` a una carpeta de respaldo y vuelve a iniciar con `--seed`.

## Usuarios de demostración

Todos usan la contraseña elegida al inicializar. Se comparte solo para la demostración académica, no para operación institucional.

| Usuario | Rol | Funciones principales |
|---|---|---|
| admin | Administración | Todos los módulos y auditoría |
| social | Trabajo Social | Evaluar, mantener fichas, asignar ayudas, revisar avisos y reportes |
| tens | TENS | Consultar fichas y agendar atenciones |
| clinico | Profesional clínico | Consultar fichas y registrar sus propias atenciones asignadas |
| bodega | Bodega | Inventario, preparación, despacho y entrega; sin acceso clínico |
| direccion | Dirección | Consulta de fichas, reportes y auditoría |

La matriz de permisos es una propuesta de implementación coherente con las pruebas disponibles; requiere validación del mandante. No existe interfaz de administración de usuarios en este alcance.

## Recorrido funcional sugerido

1. Desde el inicio, abre **Postular**. Completa datos sintéticos y adjunta un PDF. El sistema devuelve un comprobante; no afirma haber enviado un correo.
2. Ingresa como `social`, abre Postulaciones, revisa el documento y aprueba. Se crea una ficha activa y se conservan sus datos de origen. Un segundo caso activo con la misma identificación se bloquea.
3. En Beneficiarios, busca y filtra, abre la ficha, corrige datos y selecciona diagnóstico/previsión. Puedes agregar opciones al catálogo desde ese formulario. El historial muestra valores anterior/nuevo, autor y fecha.
4. Como `tens`, agenda una atención. Como `clinico`, registra evolución, procedimiento y recomendaciones o una causal estructurada de no realización. Trabajo Social recibe un aviso interno persistente.
5. Como `social`, asigna ayuda. Como `bodega`, prepara, despacha y confirma la entrega efectiva. El stock se descuenta una sola vez al entregar; si no alcanza, queda `sin_stock` y se avisa al equipo social.
6. Como `social` o `direccion`, genera un reporte con período y filtros, revisa la vista previa y descarga PDF o CSV. La ficha también tiene PDF consolidado.
7. Para una baja, resuelve primero citas/ayudas pendientes, selecciona causal y adjunta respaldo. La ficha queda cerrada, no se borra.

## Pruebas locales

```powershell
.\.venv\Scripts\python.exe run_tests.py
```

Resultados en `test-results-local/results.json` y `execution.txt`. Hay pruebas HTTP, persistencia, PDF, roles, concurrencia, archivos de 45/50/51 MB y errores controlados. No son pruebas de navegador. Las pruebas se ejecutan sobre datos ficticios y una base temporal.

## Estructura

| Ruta | Propósito |
|---|---|
| `app.py` | Rutas HTTP, autorización, validaciones y servicios de negocio |
| `db.py` | Repository y adaptador transaccional SQLite/MySQL |
| `schema.sql` | Modelo físico: PK, FK, unicidad y restricciones |
| `seed.py` | Inicialización explícita de usuarios y datos sintéticos |
| `pdf_report.py` | Generación de PDF paginado sin servicios externos |
| `static/` | Interfaz HTML, CSS y JavaScript sin dependencias CDN |
| `tests/`, `run_tests.py` | Batería y generación de evidencias reales |
| `compose.yaml`, `Dockerfile` | Entorno reproducible MySQL + aplicación |
| `docs/` | Trazabilidad, arquitectura, evaluación, manual GitHub y guion |

## Decisiones y límites

- Monolito modular cliente-servidor. Flask/Waitress, SQL parametrizado y transacciones. La interfaz no guarda datos de negocio en localStorage.
- Claves con hash scrypt, cookies HttpOnly/SameSite, CSRF y permisos en servidor. La sesión dura una hora. El bloqueo de intentos es local al proceso.
- Se conserva el formulario abierto ante fallo de red. No se promete recuperar borradores tras cerrar o recargar la pestaña.
- Archivos hasta 50 MiB (52.428.800 bytes), con extensión y cabecera/final PDF. No hay antivirus ni validación semántica de documentos médicos. Los archivos no se publican como recursos estáticos.
- Avisos internos; no hay SMTP ni envío de correos implementado. Las marcas de tiempo de auditoría se guardan en UTC; agenda usa fecha/hora local ingresada por el equipo.
- Stock se descuenta al confirmar entrega, no al asignar. No se implementan reservas. Esto coincide con CP-14/23, pero debe validarse operativamente.
- Antes de datos reales: cuentas individuales, política de accesos validada, HTTPS (`COOKIE_SECURE=1`), copias y restauración probadas, antivirus, monitoreo y revisión de seguridad. La entrega académica usa únicamente datos ficticios.
- La aplicación no completa por sí sola el informe académico, sus diagramas previos, la aprobación del mandante ni los videos. Consulta `docs/CIERRE_ENTREGA.md`.

## GitHub y entrega

Sigue `docs/GUIA_GITHUB.md`. Repositorio de referencia proporcionado: https://github.com/padreada/deportistas. Página original: https://padreada.github.io/deportistas/. No se modificó ni publicó en ese repositorio desde esta sesión.
