# Continuar Nexo Stock en otro PC

Esta guía explica cómo obtener el proyecto desde GitHub, ejecutarlo en Windows y guardar en GitHub los cambios que hagas.

## Opción recomendada: GitHub Desktop

1. Instala **GitHub Desktop** en el nuevo PC e inicia sesión en tu cuenta de GitHub.
2. En GitHub Desktop, abre **File → Clone repository**.
3. Elige la pestaña **URL** y pega esta dirección:

   `https://github.com/jorgemoraes28-ops/Control_de_stock.git`

4. Elige dónde guardar la carpeta `Control_de_stock` y pulsa **Clone**.
5. Para abrir la aplicación, en GitHub Desktop selecciona **Repository → Show in Explorer**. En la carpeta del repositorio, haz clic en la barra de dirección del Explorador, escribe `powershell` y pulsa Enter.
6. En PowerShell ejecuta:

   ```powershell
   python -m http.server 8765
   ```

7. Abre <http://localhost:8765> en el navegador. Deja abierta la ventana de PowerShell mientras uses la aplicación. Para detener el servidor, vuelve a esa ventana y pulsa **Ctrl+C**.

## Traer cambios hechos desde otro PC

Antes de empezar a trabajar, abre el repositorio en GitHub Desktop y pulsa **Fetch origin**. Si hay cambios nuevos, pulsa **Pull origin** para descargarlos.

## Guardar tus cambios en GitHub

1. Edita los archivos dentro de la carpeta `Control_de_stock`.
2. En GitHub Desktop revisa la pestaña **Changes** para confirmar qué archivos cambiaron.
3. Escribe un resumen en **Summary** y pulsa **Commit to main**.
4. Pulsa **Push origin** para subir el commit a GitHub.

Haz **Fetch origin** y **Pull origin** en el otro PC antes de continuar allí, así partes de la versión más reciente.

## Alternativa con PowerShell y Git

Si ya tienes Git instalado, puedes clonar y ejecutar el proyecto así:

```powershell
git clone https://github.com/jorgemoraes28-ops/Control_de_stock.git
cd Control_de_stock
python -m http.server 8765
```

Abre <http://localhost:8765>. Para actualizar el código antes de trabajar, usa `git pull`. Después de editarlo, guarda los cambios con:

```powershell
git add .
git commit -m "Describe brevemente el cambio"
git push
```

## Importante sobre los datos

GitHub guarda los archivos del programa. Los repuestos, movimientos y demás datos que la aplicación guarda en `localStorage` permanecen en el navegador y en ese PC; no se copian al clonar el repositorio. Si necesitas compartir los mismos datos operativos entre varios equipos, el sistema tendrá que conectarse a una base de datos compartida.
