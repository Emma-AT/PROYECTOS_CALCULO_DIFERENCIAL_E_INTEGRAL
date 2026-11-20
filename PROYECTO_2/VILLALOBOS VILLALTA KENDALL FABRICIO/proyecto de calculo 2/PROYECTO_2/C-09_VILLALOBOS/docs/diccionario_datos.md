# Diccionario de datos

Base: `datos/P02_C-09_VILLALOBOS.xlsx` (sin modificar). Datos **simulados con fines didácticos**;
los lugares e instituciones son reales, los valores no son registros oficiales.

## Hojas originales

| Hoja | Columna | Descripción | Unidad | Registros |
|---|---|---|---|---|
| Concentraciones | `voluntario` | Código del voluntario (V01–V60) | — | 780 (60 × 13) |
| Concentraciones | `tiempo_h` | Tiempo desde la toma de la dosis de 200 mg | h | malla 0,25 … 24 |
| Concentraciones | `concentracion_mg_L` | Concentración de cafeína en sangre | mg/L | 6 faltantes |
| Voluntarios | `voluntario` | Código del voluntario | — | 60 |
| Voluntarios | `sexo` | Hombre / Mujer | — | 28 H, 32 M |
| Voluntarios | `edad` | Edad | años | 18–26 |
| Voluntarios | `peso_kg` | Peso | kg | 45–96,7 |
| Voluntarios | `fuma` | Fuma | Sí/No | 11 Sí |
| Voluntarios | `anticonceptivo_hormonal` | Usa anticonceptivo hormonal | Sí/No | 9 Sí |
| Voluntarios | `tazas_cafe_habituales_dia` | Consumo habitual de café | tazas/día | 0–4 |
| Pruebas_atencion | `voluntario` | Código del voluntario | — | 480 (60 × 8) |
| Pruebas_atencion | `tiempo_h` | Tiempo desde la toma | h | 0; 0,5; 1; 2; 4; 6; 8; 12 |
| Pruebas_atencion | `tiempo_reaccion_ms` | Tiempo de reacción en la prueba de atención | ms | 128–400 |
| Bebidas | `bebida` | Nombre de la bebida | — | 6 |
| Bebidas | `cafeina_mg` | Cafeína por porción | mg | 35–160 |
| Bebidas | `volumen_ml` | Volumen de la porción | mL | 30–500 |
| Planes | `plan` | Código del plan (A–F) | — | 13 tomas |
| Planes | `hora_toma` | Hora de la toma | hora (hh:mm) | 08:00–18:00 |
| Planes | `bebida` | Bebida de la toma | — | — |
| Parametros | `parametro`, `valor`, `unidad` | Parámetros del problema | ver tabla | 8 |

### Parámetros (hoja `Parametros`)

| Parámetro | Valor | Unidad | Símbolo en el código |
|---|---|---|---|
| Dosis de la prueba | 200 | mg | `dosis_mg` |
| Constante de absorción típica | 3 | 1/h | `ka` |
| Umbral de efecto en la atención | 1,5 | mg/L | `c_efecto` |
| Umbral para no afectar el sueño | 1,0 | mg/L | `c_sueno` |
| Hora de acostarse | 23 | hora | `hora_dormir` |
| Máximo diario recomendado | 400 | mg | `max_diario_mg` |
| Inicio de la jornada de estudio | 8 | hora | `inicio` |
| Fin de la jornada de estudio | 20 | hora | `fin` |

`src/limpieza.py` verifica que existan todas las hojas, columnas y estos parámetros **con su
unidad**; si algo falta o cambia, se detiene con un mensaje claro.

## Variables derivadas (`resultados/tablas/resultados_voluntarios.csv`)

| Variable | Definición | Unidad |
|---|---|---|
| `k_1_h` | −pendiente de ln C contra t para t ≥ 6 h (mínimos cuadrados) | 1/h |
| `vida_media_h` | t½ = ln 2 / k | h |
| `r2_terminal` | R² de la recta de ln C en la fase terminal | — |
| `auc_0_24_trapecio` | ∫₀²⁴ C dt con trapecios (incluye C(0) = 0) | mg·h/L |
| `auc_0_24_simpson` | ∫₀²⁴ C dt con Simpson para espaciado irregular | mg·h/L |
| `cola_mg_h_l` | ∫₂₄^∞ C dt ≈ C(24)/k | mg·h/L |
| `auc_total` | AUC = trapecio + cola | mg·h/L |
| `pct_cola` | 100 · cola / AUC | % |
| `cl_l_h` | Depuración CL = D / AUC | L/h |
| `v_l` | Volumen de distribución V = CL / k | L |
| `grupo` | Tercil de t½: rápida, normal, lenta | — |

## Variables de decisión (`evaluacion_planes.csv`)

| Variable | Definición | Unidad |
|---|---|---|
| `horas_efecto` | H_ef = ∫₈²⁰ 1[C_plan(t) ≥ c_ef] dt | h |
| `c_dormir` | C_plan(23:00) | mg/L |
| `c_media_jornada` | (1/12) ∫₈²⁰ C_plan dt (valor promedio) | mg/L |
| `mejora_rt_ms` | pendiente atención × c_media_jornada | ms |
| `cafeina_mg` | Σ D_j | mg/día |
| `pct_personas_duermen_bien` | % de voluntarios del grupo con C(23) < c_sueño | % |
| `cumple` | C(23) < c_sueño y cafeína ≤ máximo | — |
