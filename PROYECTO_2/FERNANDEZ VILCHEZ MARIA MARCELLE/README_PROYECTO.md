# Entrega: somnolencia al volante en la ruta Golfito–San José

![Pruebas](https://github.com/MarcelleFernandez/PROYECTOS_CALCULO_DIFERENCIAL_E_INTEGRAL/actions/workflows/pruebas.yml/badge.svg)

**Universidad de Costa Rica, Sede del Sur (Golfito) · MA-0321 Cálculo Diferencial e Integral · II Ciclo 2026**
**Proyecto Aplicado 2 · Estudiante: María Marcelle Fernández Vílchez (C-02) · Docente: Francisco Campos Sandi**

**Aplicación web:** URL_DE_LA_APLICACION

## Problema

Una empresa de autobuses que viaja de noche por la Interamericana Sur prueba una diadema con
sensores de electroencefalografía (EEG) que alerta al chofer cuando empieza a dormirse.
**Pregunta de decisión:** ¿qué umbral del índice de bandas debe activar la alarma?

**Criterio de éxito:** sensibilidad ≥ 90 % con el menor costo por errores; se informan el AUC y las
falsas alarmas por hora.

## Modelo (integración)

- Potencia de banda: `P = ∫ S(f) df` entre `f1` y `f2` (regla de Simpson; trapecio para comparar).
- Índice de somnolencia: `I = (Pθ + Pα) / Pβ`.
- Curva ROC variando el umbral `c` (alarma si `I ≥ c`) y `AUC = ∫ TPR d(FPR)` por la regla del trapecio.

## Resultado

| Indicador | Valor |
|---|---|
| Umbral recomendado | c ≈ 1,72 (con filtro de artefactos) |
| Sensibilidad | 100 % (16 de 16 épocas somnolientas) |
| Especificidad | 83,3 % |
| AUC | 0,948 (0,889 sin quitar artefactos) |
| Falsas alarmas por hora | 2,0 |

Los datos son **simulados con fines didácticos**; no son registros oficiales de ninguna institución.

## Estructura del repositorio

```
datos/            Excel entregado (sin modificar)
src/limpieza.py   Lectura, validación, interpolación y artefactos
src/modelo.py     Simpson, trapecio, índice, ROC, AUC, umbral óptimo, ajuste analítico
src/escenarios.py Escenarios, sensibilidad y recomendación
src/reporte.py    Genera tablas y figuras en resultados/
tests/            Pruebas con pytest
analisis.ipynb    Análisis completo con gráficos
app.py            Aplicación web (Streamlit)
docs/             Diccionario de datos y bitácora de supuestos
informe/          Ficha técnica y resumen ejecutivo (PDF)
presentacion/     Diapositivas (PDF)
resultados/       Tablas (CSV) y figuras (PNG) generadas
```

## Cómo reproducirlo

Requiere Python 3.10 o superior.

```bash
python -m pip install -r requirements.txt
python -m pytest                # 18 pruebas
python -m src.reporte           # regenera tablas y figuras en resultados/
python -m streamlit run app.py  # abre la aplicación web
```

Para el cuaderno, abrir `analisis.ipynb` en VS Code o Jupyter y ejecutar todas las celdas.

## Integración continua

El flujo `.github/workflows/pruebas.yml` ejecuta `ruff`, `black --check` y `pytest` en cada push.
