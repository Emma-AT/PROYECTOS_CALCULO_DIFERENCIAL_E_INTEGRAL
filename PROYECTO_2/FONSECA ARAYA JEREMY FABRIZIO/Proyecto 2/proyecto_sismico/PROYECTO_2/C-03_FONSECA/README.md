# Amenaza sísmica y refuerzo del Hospital de Golfito

Proyecto Aplicado 2, tema 3. Universidad de Costa Rica, Sede del Sur.
MA-0321, II ciclo 2026. Docente: Francisco Campos Sandi.
Estudiante: Jeremy Fabrizio Fonseca Araya. Carné: C23005. Código: C-03.

Compara el estado actual y dos refuerzos según el valor presente neto de pérdidas evitadas.
Lee el Excel individual original. Los datos son simulados por el docente, no oficiales del hospital.

**Estado:** implementación inicial con asistencia de ChatGPT/Codex, para revisión y defensa individual.
Los PDF son borradores reproducibles. Ver `docs/AUTORIA.md` y `docs/CUMPLIMIENTO.md`.
**Aplicación publicada:** pendiente de desplegar desde el fork personal.
**CI:** flujo preparado, pendiente de ejecutarse en GitHub. No se presenta una insignia verde ficticia.

## Abrir en VS Code y WSL

Usá Python 3.12 o posterior (dependencias preparadas para 3.12–3.14).
Abrí esta carpeta, la que contiene `app.py` e `iniciar.sh`. En WSL:

```bash
pwd
ls
bash iniciar.sh
```

Abrí el `Local URL` que indique Streamlit, normalmente `http://localhost:8501`.
Dejá esa terminal abierta. Para detener: Ctrl+C. Para volver a iniciar: `bash iniciar.sh`.
No necesitás activar manualmente el entorno ni usar `chmod` para ejecutar con bash.
Si falta venv, instalá `python3-venv` con apt en WSL. La contraseña de sudo es la de tu usuario Linux.

## Pruebas y reproducción

Después de iniciar por primera vez, otra terminal en esta misma carpeta permite ejecutar:

```bash
source .venv/bin/activate
pytest -q
ruff check .
ruff format --check .
python -m src.reporte
python -m src.cuaderno --ejecutar
```

`src.reporte` regenera los CSV y gráficos de `resultados/`, la propuesta de una página,
la ficha técnica de 5 páginas más declaración sin firmar, el resumen ejecutivo y 13 diapositivas PDF.
`src.cuaderno` construye y ejecuta `analisis.ipynb` con el Python activo, sin depender de un kernel ajeno.
El cuaderno entregado ya contiene resultados. En VS Code elegí `.venv` como kernel si querés reejecutarlo.
En entornos que no permiten iniciar kernels, `python -m src.cuaderno --en-proceso` ejecuta las mismas
celdas realmente con IPython y conserva sus resultados, sin abrir conexiones de kernel.

## Recorrido de la aplicación

1. **Decisión:** recomendación, inversión, ahorro anual, VPN, tabla de tres alternativas y descarga.
2. **Movimiento del suelo:** aceleración, velocidad y desplazamiento con y sin corrección, Arias y duración.
3. **Cálculos y verificación:** fórmulas, recurrencia, integrandos de PAE, descuento y errores entre métodos.
4. **Datos y supuestos:** faltantes, atípicos, exploración y hojas originales.

Los controles modifican b, descuento y alternativa inspeccionada. El Excel también puede sustituirse
por otro con las mismas hojas, columnas, unidades y estructura numérica. Las restricciones se validan
con mensajes de error. La recomendación siempre compara las tres opciones, aunque se inspeccione una.

## Archivos y responsabilidades

| Archivo | Responsabilidad |
|---|---|
| `src/limpieza.py` | Leer Excel, validar, registrar faltantes e interpolar la aceleración |
| `src/numericos.py` | Trapecio, Simpson e integral acumulada propios |
| `src/modelo.py` | b, recurrencia, probabilidades, movimiento, Arias, PAE y VPN |
| `src/escenarios.py` | Comparación y sensibilidad |
| `src/analisis.py` | Reunir resultados sin duplicar fórmulas |
| `src/graficas.py` | Figuras con unidades y áreas sombreadas |
| `src/reporte.py` | Regenerar tablas, gráficos y documentos |
| `src/cuaderno.py` | Crear y ejecutar el análisis reproducible |
| `app.py` | Presentar y controlar los resultados con Streamlit |

La API de OpenAI no se utiliza en esta versión. Los resultados son independientes de servicios de IA.

## Criterios matemáticos

Catálogo completo supuesto durante los 30 años calendario 1996–2025.
Magnitudes redondeadas a 0,1; estimador con corrección de medio intervalo.
Datos de aceleración en cm/s²; únicamente Arias convierte primero a m/s².
Se integra daño lineal por tramos con Simpson refinado (16 subdivisiones por tramo),
y se compara con trapecio, Simpson en la tabla original e integral exacta del mismo modelo.
La tasa de descuento del Excel se interpreta como tasa continua anual, conforme al enunciado.
El plazo se informa; el VPN principal usa beneficios desde t=0 como pide su fórmula.
La variante con beneficios al terminar la obra se muestra en los resultados como verificación adicional.

## Fork, commits y publicación

Repositorio del curso:
https://github.com/Franciscocamposk/PROYECTOS_CALCULO_DIFERENCIAL_E_INTEGRAL

Creá tu fork y clonalo. Copiá aquí dentro `PROYECTO_2/C-03_FONSECA/`.
Copiá el workflow a `.github/workflows/` en la RAÍZ del fork. GitHub no descubre workflows anidados.
Se incluye una copia dentro del proyecto únicamente para conservar la estructura solicitada.
Usá al menos 10 commits reales, repartidos durante las semanas de trabajo, con cambios que comprendás.
No inventés fechas ni dividas artificialmente una entrega para simular ese historial.

Cuando exista el fork, ejecutá `python -m src.configurar_github TU_USUARIO NOMBRE_REPOSITORIO`
para insertar la insignia que consulta el estado real del flujo. Después verificá la ejecución en Actions.

En Streamlit Community Cloud, seleccioná el fork, su rama y
`PROYECTO_2/C-03_FONSECA/app.py`. Usá Python 3.12 si está disponible.
Anotá el enlace público real en este README y probá que abre sin tu sesión.
El pull request de entrega se realiza después de revisar los resultados, archivos, enlaces y autoría.
