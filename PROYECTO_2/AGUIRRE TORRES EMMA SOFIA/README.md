# Proyecto 9 — Repotenciación de la Planta Eólica Tejona en Tilarán

![Proyecto](https://img.shields.io/badge/Proyecto%202-9-0b4f8a?style=flat-square) ![Código](https://img.shields.io/badge/Código-C--01-2e7d32?style=flat-square) ![Modalidad](https://img.shields.io/badge/Modalidad-Individual-e08a2e?style=flat-square)

**Estudiante:** Emma Sofia Aguirre Torres  
**Código:** C-01  
**Modalidad:** individual

## Pregunta de decisión

¿Conviene repotenciar la planta y con cuál opción, o mantener las turbinas actuales?

## Objetivo y desarrollo

Analizar los datos de la planta mediante un modelo de integración, comparar las alternativas de repotenciación y sustentar una recomendación técnica.

## Modelo matemático

La potencia del viento, el límite de Betz y la energía generada se modelan como:

$$
P_{\mathrm{viento}}=\frac{1}{2}\rho Av^3,
\qquad
C_p=\frac{P(v)}{\frac{1}{2}\rho Av^3}\leq\frac{16}{27},
\qquad
E=\int_0^T P\big(v(t)\big)\,dt
$$

La distribución de Weibull, la potencia media y el escalamiento con la altura son:

$$
f(v)=\frac{k}{c}(v/c)^{k-1}e^{-(v/c)^k},
\qquad
\overline{P}=\int_0^{\infty}P(v)f(v)\,dv
$$

$$
v(H)=v(H_0)(H/H_0)^\alpha
$$

La energía anual y el valor presente neto de la repotenciación son:

$$
E_{\mathrm{anual}}=8760N(1-L)\overline{P}
$$

$$
VPN=-I+(\Delta E_{\mathrm{anual}}p-\Delta M)\frac{1-(1+r)^{-n}}{r}
$$

## Resultado de las pruebas

![pruebas](https://github.com/Emma-AT/PROYECTOS_CALCULO_DIFERENCIAL_E_INTEGRAL/actions/workflows/pruebas.yml/badge.svg)

## Aplicación web

Enlace público: **https://proyectoscalculodiferencialeintegral-lct252yf66nvyv9tudxzaq.streamlit.app/**

> La app se publica desde la rama `app-web`, que es igual a `main` pero con `requirements.txt` en la raíz del repositorio: Streamlit Community Cloud no maneja rutas con espacios.

## Estructura

| Carpeta / archivo | Contenido |
|---|---|
| `datos/` | Excel entregado, sin modificar |
| `src/limpieza.py` | Lectura, validación, faltantes, picos y densidad del aire |
| `src/modelo.py` | Trapecio, Simpson, clase `Turbina`, potencia, Weibull |
| `src/escenarios.py` | Energía anual, factor de planta, VPN y recomendación |
| `src/reporte.py` | Genera tablas y figuras en `resultados/` |
| `tests/` | Pruebas con pytest |
| `analisis.ipynb` | Análisis completo |
| `app.py` | Aplicación web (Streamlit) |
| `docs/` | Diccionario de datos y bitácora de supuestos |
| `informe/`, `presentacion/` | Ficha técnica, resumen ejecutivo y diapositivas (PDF) |

## Cómo ejecutar

Desde esta carpeta, con Python 3.10 o superior:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                      # pruebas
python -m src.reporte       # regenera resultados/
streamlit run app.py        # abre la aplicación en http://localhost:8501
```

## Archivos del enunciado

- [Enunciado (PDF)](P09_C-01_AGUIRRE.pdf)
- [Base de datos original](P09_C-01_AGUIRRE.xlsx)
