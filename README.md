# Nexo Stock

Prototipo web para controlar repuestos, movimientos, talleres, coches e informes de El Norteño - Bus Del Norte.

## Ejecutar localmente

Desde esta carpeta, inicia un servidor estático:

```powershell
python -m http.server 8765
```

Luego abre <http://localhost:8765>.

## Continuar en otra computadora

Consulta la [guía paso a paso para Windows](docs/continuar-en-otro-pc.md) para clonar el repositorio, abrir la aplicación y guardar cambios en GitHub.

## Notas

- El tiempo actual de Bella Unión se consulta en Open-Meteo y requiere conexión a internet.
- Los datos de demostración y los cambios guardados en la aplicación se almacenan en el navegador (`localStorage`). GitHub conserva el código, pero esos datos no se sincronizan automáticamente entre dispositivos.
- Las bibliotecas JavaScript de exportación están incluidas en `assets/vendor/`.
