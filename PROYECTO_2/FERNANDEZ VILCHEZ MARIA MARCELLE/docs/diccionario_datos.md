# Diccionario de datos

Archivo: `datos/P01_C-02_FERNANDEZ.xlsx` (entregado por el docente; **no se modifica**).
Los datos son **simulados con fines didácticos** (no son registros oficiales).

## Hoja `Espectro_EEG` (1440 registros = 2 viajes × 24 épocas × 30 frecuencias)

| Columna | Descripción | Unidad |
|---|---|---|
| `viaje` | Número del viaje registrado (1 o 2); cada viaje dura 2 h | — |
| `epoca` | Número de la época (intervalo de 5 min) dentro del viaje, 1 a 24 | — |
| `minuto_inicio` | Minuto del viaje en que inicia la época (0, 5, …, 115) | min |
| `frecuencia_Hz` | Frecuencia del espectro, 1 a 30 en pasos de 1 | Hz |
| `potencia_uV2_Hz` | Densidad espectral de potencia del EEG, S(f). Tiene 8 valores faltantes | µV²/Hz |

## Hoja `Etiquetas` (48 registros = una fila por época)

| Columna | Descripción | Unidad |
|---|---|---|
| `viaje`, `epoca` | Identifican la época (igual que en `Espectro_EEG`) | — |
| `somnolencia_video` | Somnolencia observada en video: 1 = somnoliento, 0 = alerta | — |
| `tiempo_reaccion_ms` | Tiempo de reacción del chofer en la época | ms |

## Hoja `Parametros` (8 filas)

| Parámetro | Valor | Unidad |
|---|---|---|
| Banda theta, límite inferior | 4 | Hz |
| Banda theta, límite superior (= alfa inferior) | 8 | Hz |
| Banda alfa, límite superior (= beta inferior) | 12 | Hz |
| Banda beta, límite superior | 30 | Hz |
| Duración de cada época | 5 | min |
| Sensibilidad mínima exigida | 0,9 | fracción |
| Costo relativo de una omisión | 8 | unidades |
| Costo relativo de una falsa alarma | 1 | unidades |

## Variables derivadas (calculadas en `src/`)

| Variable | Definición | Unidad |
|---|---|---|
| Pθ, Pα, Pβ | ∫ S(f) df en 4–8, 8–12 y 12–30 Hz (Simpson; trapecio para comparar) | µV² |
| Potencia total | ∫ S(f) df en 1–30 Hz | µV² |
| I | (Pθ + Pα) / Pβ | adimensional |
| TPR, FPR | Sensibilidad y 1 − especificidad para un umbral | fracción |
| c | Umbral de alarma: suena si I ≥ c | adimensional |
| Falsas alarmas por hora | Falsas alarmas ÷ horas de conducción alerta evaluadas | 1/h |
