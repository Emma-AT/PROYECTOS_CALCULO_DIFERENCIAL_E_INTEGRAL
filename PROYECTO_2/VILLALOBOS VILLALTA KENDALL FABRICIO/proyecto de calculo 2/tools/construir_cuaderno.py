"""Construye PROYECTO_2/C-09_VILLALOBOS/analisis.ipynb (se ejecuta luego con nbconvert)."""

from pathlib import Path

import nbformat as nbf

celdas: list[tuple[str, str]] = []


def md(texto: str) -> None:
    celdas.append(("md", texto.strip()))


def py(codigo: str) -> None:
    celdas.append(("py", codigo.strip()))


md(r"""
# Cafeína, atención y sueño en semana de exámenes
**Proyecto 2 · MA-0321 Cálculo Diferencial e Integral · UCR Sede del Sur (Golfito) · II-2026**
Kendall Fabricio Villalobos Villalta · Código C-09

**Cliente:** Coordinación de Vida Estudiantil, Sede del Sur, que prepara una campaña sobre el
consumo de café y bebidas energéticas en semana de exámenes.

**Pregunta de decisión.** ¿Cuántas tomas, de qué bebida y hasta qué hora conviene consumir cafeína
para tener más horas de atención entre las 8:00 y las 20:00 sin afectar el sueño?

**Criterio de éxito.** Para cada tipo de persona (eliminación rápida, normal y lenta) se recomienda el
plan con más horas de concentración eficaz, con concentración al acostarse menor que el umbral y
consumo diario dentro del máximo.

> Datos simulados con fines didácticos; los resultados no constituyen una recomendación médica.

Este cuaderno usa las funciones de `src/` (las mismas que la aplicación web) y se ejecuta de
principio a fin con `jupyter nbconvert --execute analisis.ipynb`.
""")

py("""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src import escenarios as esc
from src import graficos as gr
from src import limpieza, modelo
from src.config import RUTA_DATOS

%matplotlib inline
pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 160)
pd.set_option("display.precision", 3)
""")

md("""
## 1. Lectura y validación de la base
Se lee el Excel con `pd.read_excel(ruta, sheet_name=None)`; `leer_base` verifica hojas y columnas y
`leer_parametros` verifica que cada parámetro tenga la unidad esperada. Ningún valor del problema
se escribe en el código.
""")

py("""
hojas = limpieza.leer_base(RUTA_DATOS)
param = limpieza.leer_parametros(hojas["Parametros"])
print({h: d.shape for h, d in hojas.items()})
param
""")

py("""
hojas["Parametros"]
""")

md("""
## 2. Exploración
### 2.1 Calidad: registros, faltantes y rangos
""")

py("""
limpieza.resumen_calidad(hojas)
""")

md("""
### 2.2 Patrones en el tiempo
Concentración media y tiempo de reacción medio en cada momento de muestreo. La concentración sube
hasta un pico cerca de 1 h y luego decae; el tiempo de reacción hace lo contrario.
""")

py("""
conc = hojas["Concentraciones"]
pruebas = hojas["Pruebas_atencion"]
patron_c = conc.groupby("tiempo_h")["concentracion_mg_L"].agg(["mean", "std", "count"])
patron_rt = pruebas.groupby("tiempo_h")["tiempo_reaccion_ms"].agg(["mean", "std"])
patron_c.join(patron_rt, lsuffix="_C_mg_L", rsuffix="_RT_ms", how="outer")
""")

md("""
### 2.3 Características de los voluntarios
""")

py("""
vol = hojas["Voluntarios"]
display(vol.describe())
display(vol[["sexo", "fuma", "anticonceptivo_hormonal"]].apply(pd.Series.value_counts))
""")

md("""
## 3. Faltantes y atípicos
**Criterio (ver `docs/bitacora_supuestos.md`):**
* Atípico: punto interior que difiere más de ×1,8 del valor esperado por interpolación log-lineal
  entre sus vecinos válidos (se marcan uno a uno, el peor primero).
* Faltantes interiores y atípicos: interpolación lineal en el tiempo (equivale a lo que hace el
  trapecio, no inventa área).
* Faltantes en 24 h: extrapolación con la recta de ln C de la fase terminal.
* Los valores imputados no se usan para estimar k.
""")

py("""
conc_limpio, bitacora = limpieza.limpiar_concentraciones(conc)
print("Registros:", len(conc), "->", len(conc_limpio), "| faltantes tras limpiar:",
      conc_limpio["concentracion_mg_L"].isna().sum())
bitacora
""")

md("""
## 4. Modelo: AUC, vida media, depuración y volumen
Para cada voluntario:

* $k$ = −pendiente de $\\ln C$ contra $t$ para $t \\ge 6$ h (decrecimiento exponencial
  $C = C_0 e^{-kt}$ ⇒ $\\ln C = \\ln C_0 - kt$); $t_{1/2} = \\ln 2 / k$.
* $AUC = \\int_0^{24} C\\,dt$ (trapecio, con $C(0)=0$) $+ \\int_{24}^{\\infty} C(24)e^{-k(t-24)}dt$,
  y la integral impropia vale exactamente $C(24)/k$.
* $CL = D/AUC$ (L/h) y $V = CL/k$ (L).
""")

py("""
resultados = modelo.analizar_todos(conc_limpio, param.dosis_mg)
resultados.describe().T
""")

py("""
vidas = resultados["vida_media_h"]
tipico = (vidas - vidas.median()).abs().idxmin()
fig = gr.fig_voluntario_desde_tablas(conc_limpio, resultados, tipico, param.ka, param.dosis_mg)
fig = gr.fig_voluntario_desde_tablas(conc_limpio, resultados, vidas.idxmax(), param.ka, param.dosis_mg)
""")

md("""
**Interpretación.** El AUC (mg·h/L) es la exposición total a la cafeína. La cola impropia aporta en
mediana el 4 % del AUC, pero en personas de eliminación lenta llega al 40 %: truncar en 24 h
subestimaría mucho su exposición. V/peso ≈ 0,58 L/kg y CL/peso ≈ 0,085 L/(h·kg), órdenes de magnitud
coherentes con la literatura farmacocinética de la cafeína.
""")

py("""
print("Cola (% del AUC): mediana", round(resultados["pct_cola"].median(), 2),
      "| máx.", round(resultados["pct_cola"].max(), 2))
print("V/peso (L/kg):", round((resultados["v_l"] / vol.set_index("voluntario")["peso_kg"]).median(), 3))
""")

md("""
## 5. Verificación y validación
1. **Validación obligatoria:** integrando numéricamente (Simpson propio) el modelo $C(t)$ de cada
   voluntario hasta 200 h se recupera $D/(Vk)$ con error < 0,5 %.
2. $\\int_0^\\infty e^{-kt}dt = 1/k$ con la integral truncada.
3. **Contra los acumulados de la base:** el acumulado observado $\\int_0^{24}C\\,dt$ (trapecio) contra
   la integral exacta del modelo en [0, 24] (antiderivada analítica).
4. Trapecio contra Simpson (dos reglas para la misma integral).
""")

py("""
validacion = modelo.validar_auc_modelo(resultados, param.ka, param.dosis_mg)
print(f"Error relativo máximo D/(Vk): {100 * validacion['error_rel'].max():.4f} %")
for k in [resultados["k_1_h"].min(), resultados["k_1_h"].median(), resultados["k_1_h"].max()]:
    aprox = modelo.integral_exponencial_truncada(k, 200)
    print(f"k = {k:.3f}: truncada = {aprox:.4f} h, 1/k = {1 / k:.4f} h, error = {abs(aprox * k - 1):.2e}")
""")

py("""
verif = modelo.verificar_contra_datos(conc_limpio, resultados, param.ka, param.dosis_mg)
display(verif.describe().T)
fig = gr.fig_verificacion(validacion, verif)
""")

md("""
**Lectura.** El acumulado observado y la integral exacta del modelo difieren 0,2 % en promedio y el
modelo explica 96 % de la variación de cada perfil (R² medio). Simpson difiere 5,7 % de la integral
exacta: la parábola que pasa por 10, 12 y 24 h no sigue a la exponencial en el último tramo, por lo
que para estos datos el trapecio es la regla adecuada.
""")

md("""
## 6. Velocidad de eliminación: factores y grupos
""")

py("""
clasificados = esc.clasificar(resultados, vol)
factores = esc.comparar_factores(clasificados)
display(factores)
display(clasificados.groupby("grupo", observed=True)[["vida_media_h", "k_1_h", "v_l"]].agg(["median", "min", "max"]))
display(pd.crosstab(clasificados["grupo"], [clasificados["fuma"], clasificados["anticonceptivo_hormonal"]]))
fig = gr.fig_vida_media(clasificados, factores)
""")

md("""
Fumar acorta la vida media (mediana 3,1 h contra 5,5 h) y el anticonceptivo hormonal la alarga
(7,2 h contra 4,8 h); ambas diferencias son significativas en una prueba de permutaciones
(p < 0,001). Por eso los fumadores se concentran en el grupo rápido y las usuarias de anticonceptivo
en el lento.
""")

py("""
fig = gr.fig_perfiles(conc_limpio, clasificados)
""")

md("""
## 7. Atención y concentración
""")

py("""
atencion = limpieza.unir_atencion(limpieza.revisar_pruebas(pruebas), conc_limpio)
relacion = modelo.ajustar_atencion(atencion)
print(relacion)
fig = gr.fig_atencion(atencion, relacion, param.c_efecto)
""")

md("""
Cada mg/L de cafeína mejora el tiempo de reacción en ≈ 24 ms (R² = 0,77). En el umbral de efecto
(1,5 mg/L) la mejora esperada es ≈ 40 ms, ≈ 12 % del tiempo basal (336 ms).
""")

md("""
## 8. Planes de consumo: superposición y horas con efecto
$C_{plan}(t) = \\sum_j C(t-t_j; D_j)$ y $H_{ef} = \\int_8^{20} \\mathbf 1[C_{plan}(t)\\ge c_{ef}]\\,dt$.
La integral de la indicadora se calcula con la fracción exacta de cada subintervalo de una malla de
1 min y se compara con los cruces hallados por bisección.
""")

py("""
planes = esc.construir_planes(hojas["Planes"], hojas["Bebidas"])
modelos = esc.modelos_por_grupo(clasificados, param.ka)
individuos = esc.modelos_individuales(clasificados, param.ka)
for codigo, plan in planes.items():
    print(codigo, plan.descripcion(), f"({plan.total_mg:.0f} mg)")
modelos
""")

py("""
evaluacion = esc.evaluar_planes(planes, modelos, param, relacion, 0, individuos)
display(evaluacion)
fig = gr.fig_mapa_planes(evaluacion)
""")

py("""
metodos = esc.comparar_metodos_horas(planes, modelos, param)
print(f"Error relativo máximo entre métodos: {metodos['error_rel'].max():.2e}")
metodos.head(6)
""")

md("""
## 9. Recomendación, escenarios y sensibilidad
""")

py("""
recomendacion = esc.recomendar(evaluacion)
guia = esc.guia_consumo(recomendacion, planes, modelos, param)
display(guia)
fig = gr.fig_planes_recomendados(guia, planes, modelos, param)
""")

py("""
lista = esc.escenarios_definidos(param)
ev_esc = esc.evaluar_escenarios(lista, planes, modelos, relacion, individuos)
rec_esc = esc.recomendar(ev_esc)
display(rec_esc[["escenario", "grupo", "plan", "horas_efecto", "c_dormir", "pct_personas_duermen_bien"]])
fig = gr.fig_escenarios(ev_esc, rec_esc)
""")

py("""
sens = esc.sensibilidad(planes, modelos, param)
display(sens.groupby("parametro")["cambia_decision"].sum().rename("decisiones que cambian"))
fig = gr.fig_sensibilidad(sens, guia)
""")

py("""
limites = esc.tabla_horas_limite(modelos, hojas["Bebidas"], param)
display(limites)
fig = gr.fig_horas_limite(limites, param)
""")

md("""
### 9.1 Criterio prudente y plan ajustado
La persona típica del grupo puede cumplir el umbral de sueño mientras una parte importante del grupo
no lo cumple. El criterio prudente exige que al menos el 80 % del grupo quede bajo el umbral. El
plan ajustado busca entre todas las combinaciones de 1 a 3 bebidas de la base a horas enteras.
""")

py("""
prudente = esc.guia_consumo(esc.recomendar(evaluacion, 80.0), planes, modelos, param)
ajustados = esc.planes_optimizados(modelos, individuos, hojas["Bebidas"], param, 80.0)
display(prudente[["grupo", "plan", "descripcion", "horas_efecto", "c_dormir", "pct_personas_duermen_bien"]])
display(ajustados)
fig = gr.fig_comparacion_criterios(guia, prudente, ajustados)
""")

md("""
## 10. Conclusión
* **Criterio oficial (catálogo, persona típica):** eliminación rápida → plan E (café 8:00 +
  energética grande 14:00, 7,9 h); normal → plan B (cafés a las 8:00 y 13:00, 9,7 h); lenta →
  plan A (un café a las 8:00, 3,8 h).
* Con el criterio prudente (≥ 80 % del grupo duerme bien), el patrón ganador es **una dosis grande
  temprano y dosis pequeñas después**: el plan ajustado da 10,8 h (rápida), 10,9 h (normal) y
  6,7 h (lenta).
* El parámetro que más mueve la decisión es la velocidad de eliminación (k) junto con el umbral de
  sueño y la hora de acostarse; ka y el umbral de efecto no cambian ninguna decisión.
* Limitaciones: datos simulados, una sola dosis de prueba, cinética lineal supuesta, sin tolerancia.
""")

nb = nbf.v4.new_notebook()
nb["cells"] = [
    nbf.v4.new_markdown_cell(t) if tipo == "md" else nbf.v4.new_code_cell(t) for tipo, t in celdas
]
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
destino = Path(__file__).resolve().parents[1] / "PROYECTO_2" / "C-09_VILLALOBOS" / "analisis.ipynb"
nbf.write(nb, destino)
print("escrito", destino)
