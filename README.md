# Nexo Stock

Prototipo web para controlar repuestos, movimientos, talleres, coches e informes de El Norteño - Bus Del Norte.

## Abrir en Windows

Ejecuta con doble clic `release/NexoStock-1.0.0-Windows-x64.exe`. Abre Nexo Stock en su propia ventana y arranca el servidor SQLite local automáticamente; no requiere instalar Python ni iniciar un navegador manualmente. La base de esta versión se guarda en `%APPDATA%\Nexo Stock\data\control_stock.sqlite3`.

El ejecutable portable es para Windows de 64 bits. Como no tiene firma de editor, Windows puede mostrar un aviso de seguridad al abrirlo.

## Volver a generar el ejecutable

En Windows, instala Node.js y Python para desarrollo, luego ejecuta:

```powershell
npm install
python -m pip install -r requirements-build.txt
npm run dist:windows
```

## Ejecutar localmente

Desde esta carpeta, inicia el servidor local de la aplicación:

```powershell
python server.py
```

Luego abre <http://localhost:8765>.

## Continuar en otra computadora

Consulta la [guía paso a paso para Windows](docs/continuar-en-otro-pc.md) para clonar el repositorio, abrir la aplicación y guardar cambios en GitHub.

## Notas

- El tiempo actual de Bella Unión se consulta en Open-Meteo y requiere conexión a internet.
- Los datos operativos se guardan en SQLite en `data/control_stock.sqlite3`. Esta carpeta se excluye de Git para que los datos privados no se suban al repositorio.
- En la primera ejecución, el servidor importa los datos existentes desde el almacenamiento del navegador abierto en el mismo perfil. El archivo SQLite pasa a ser la fuente de datos para posteriores aperturas de la app.
- La base es local a esta computadora y el servidor solo escucha en `127.0.0.1`. No se comparte con otros dispositivos ni debe exponerse en una red.
- El acceso inicial es **usuario `admin` / contraseña `admin123`**. Luego, un administrador puede crear cuentas con nombre de usuario y contraseña desde **Configuración → Usuarios y roles**. Cierra la sesión desde **Configuración → Sesión actual**.
- El servidor local añade persistencia SQLite, pero el inicio de sesión y los permisos siguen aplicándose en la interfaz del navegador. Para usarla en una red o con información sensible todavía hace falta trasladar autenticación y permisos al backend.
- Para respaldar los datos, cierra el servidor y copia `data/control_stock.sqlite3` a un lugar seguro. No subas la base a GitHub.
- Las bibliotecas JavaScript de exportación están incluidas en `assets/vendor/`.
