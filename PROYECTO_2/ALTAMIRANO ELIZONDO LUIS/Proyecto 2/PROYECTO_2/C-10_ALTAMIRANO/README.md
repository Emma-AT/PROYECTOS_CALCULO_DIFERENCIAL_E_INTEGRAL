# Proyecto Aplicado 2 · Procrastinación y entregas en Mediación Virtual

![pruebas](https://github.com/TU_USUARIO/TU_REPO/actions/workflows/pruebas.yml/badge.svg)

MA-0321 Cálculo Diferencial e Integral · II Ciclo 2026 · Sede del Sur (Golfito)
Estudiante: Altamirano Elizondo, Luis · Código C-10

## Aplicación web
Enlace: _pendiente: publicar en Streamlit Community Cloud y pegar aquí el enlace_

## Cómo ejecutar
```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                           # pruebas
streamlit run app.py             # aplicación
python -m src.reporte            # regenera tablas y figuras en resultados/
```

## Estructura
- `datos/` Excel entregado, sin modificar
- `src/` limpieza, modelo, escenarios y reporte
- `tests/` pruebas con pytest
- `analisis.ipynb` análisis completo
- `app.py` aplicación web
- `docs/` diccionario de datos y bitácora de supuestos
- `informe/` ficha técnica y resumen ejecutivo (PDF)
- `presentacion/` diapositivas en PDF y marco teórico
- `resultados/` tablas y figuras generadas (`oscuro/` y `formulas/` son para las diapositivas)

## Nota sobre la IA (opcional)
`src/explicador.py` redacta un resumen en lenguaje sencillo con una API de IA.
Las cifras las calcula siempre el código del proyecto, y sin clave la app usa un texto local.
Ver `docs/INTEGRAR_explicador.md`.

## Estado y resultados
- Estrategia recomendada: **G03 (entrega parcial obligatoria a mitad del plazo)**: nota media 78,3, 2,4 % de tardías, 6,2 h docentes por tarea.
- Tablas y figuras en `resultados/` (se regeneran con `python -m src.reporte`).
- Para estudiar y defender el trabajo: `docs/guia_defensa.md`. Propuesta: `docs/propuesta.md`.
