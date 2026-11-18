# Proyecto 6 — Migración de aves rapaces sobre Kèköldi, Talamanca

![Proyecto](https://img.shields.io/badge/Proyecto%202-6-0b4f8a?style=flat-square) ![Código](https://img.shields.io/badge/Código-C--06-2e7d32?style=flat-square) ![Modalidad](https://img.shields.io/badge/Modalidad-Individual-e08a2e?style=flat-square)
![pruebas](https://github.com/Allison28monge/PROYECTOS_CALCULO_DIFERENCIAL_E_INTEGRAL/actions/workflows/pruebas.yml/badge.svg)

**Estudiante:** Allison Georgina Monge Navarro  
**Código:** C-06  
**Modalidad:** individual  
**Curso:** MA-0321 Cálculo Diferencial e Integral · UCR Sede del Sur · II Ciclo 2026

**Aplicación web:** https://rapaces-kekoldi-monge.streamlit.app/

## Pregunta de decisión

¿Qué fechas y qué horario debe tener la campaña de voluntariado para registrar la mayor cantidad de aves migratorias?

## Objetivo y desarrollo

Modelar la migración mediante integración, analizar los periodos de mayor actividad y recomendar fechas y horarios de monitoreo.

## Resultado principal

Hacer la campaña de 21 días **del 8 al 28 de octubre**, con turno de **9:00 a 15:00**.
Registraría cerca del **62 %** de las aves de la temporada, frente al **45 %** de la campaña
tradicional (1 al 21 de octubre): unas 394 000 aves más.

## Modelo matemático

El total diario, el total de la temporada, la fracción acumulada y la fecha media se calculan como:

$$
N_d=\int_{h_i}^{h_f}r_d(x)\,dx,
\qquad
N=\int_{t_0}^{t_1}n(t)\,dt
$$

$$
F(t)=\frac{1}{N}\int_{t_0}^{t}n(u)\,du,
\qquad
\bar{t}=\frac{1}{N}\int_{t_0}^{t_1}t\,n(t)\,dt
$$

La campaña de $L$ días que inicia en $a$ captura:

$$
G(a)=\int_a^{a+L}n(t)\,dt,
\qquad
G'(a)=n(a+L)-n(a)=0
$$

## Archivos

- [Enunciado del proyecto (PDF)](P06_C-06_MONGE.pdf)
- [Datos entregados](P06_C-06_MONGE.xlsx) (copia sin modificar en `datos/`)
- [Cuaderno de análisis](analisis.ipynb)
- [Diccionario de datos](docs/diccionario_datos.md) y [bitácora de supuestos](docs/bitacora_supuestos.md)
- Ficha técnica y resumen ejecutivo: carpeta `informe/`
- Diapositivas: carpeta `presentacion/`

## Cómo ejecutarlo

Desde esta carpeta, con Python 3.10 o superior:

```bash
pip install -r requirements.txt
pytest -v                 # pruebas
python -m src.reporte     # tablas y figuras en resultados/
streamlit run app.py      # aplicación web
```

Instrucciones detalladas para VS Code en [`docs/GUIA_VS_CODE.md`](docs/GUIA_VS_CODE.md).

## Estructura

| Carpeta / archivo | Contenido |
|---|---|
| `datos/` | Excel entregado, sin modificar |
| `src/datos.py` | Lectura del Excel y validación de hojas, columnas y unidades |
| `src/limpieza.py` | Detección de ceros de más y horas sin conteo; interpolación dentro del día |
| `src/modelo.py` | Trapecio, Simpson, total diario con colas, F(t), percentiles, fecha media, ventana y turno óptimos |
| `src/escenarios.py` | Campaña tradicional vs. alternativas, sensibilidad y recomendación |
| `src/graficos.py` | Figuras (las usan el reporte, el cuaderno y la app) |
| `src/reporte.py` | Genera tablas y figuras en `resultados/` |
| `tests/` | Pruebas con pytest |
| `analisis.ipynb` | Análisis completo con gráficos y explicación |
| `app.py` | Aplicación web (Streamlit) |
| `docs/` | Diccionario de datos, bitácora de supuestos y guía de VS Code |

## Cómo revisar

1. Leer este README y el informe en `informe/`.
2. Abrir `analisis.ipynb` (ya ejecutado) o la aplicación web.
3. Correr `pytest -v` para comprobar las pruebas.

Los datos son simulados con fines didácticos; no son registros oficiales.
