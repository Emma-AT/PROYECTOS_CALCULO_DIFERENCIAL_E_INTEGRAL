# Diccionario de datos

Archivo: `datos/P06_C-06_MONGE.xlsx` (no se modifica). Datos simulados con fines didácticos.

## Hoja `Conteo_horario` (1350 registros = 50 días × 9 horas × 3 especies)

| Columna | Descripción | Unidad | Tipo |
|---|---|---|---|
| `fecha` | Fecha del registro, del 20/09/2026 al 08/11/2026 | fecha | texto (año-mes-día) |
| `hora_inicio` | Inicio del bloque de una hora del conteo (07:00 a 15:00) | hora | texto (hh:mm) |
| `especie` | Zopilote cabecirrojo, Gavilán aludo o Gavilán de Swainson | — | texto |
| `aves_contadas` | Aves contadas en el bloque de una hora. Tiene 58 vacíos | aves (por hora) | número |
| `condicion` | Tiempo durante el día: Despejado, Nublado o Lluvia | — | texto |

## Hoja `Parametros`

| Parámetro | Símbolo en el código | Valor | Unidad |
|---|---|---|---|
| Hora de inicio del vuelo migratorio | `hi` | 6,2 (6:12) | hora |
| Hora de fin del vuelo migratorio | `hf` | 17,1 (17:06) | hora |
| Días de la campaña de voluntariado | `dias_campana` (L) | 21 | días |
| Horas por turno de observación | `horas_turno` | 6 | horas |
| Inicio de la campaña tradicional | `inicio_tradicional` | 11 (1 de octubre) | días desde el 20/9 |

## Hoja `Diccionario`

Descripción de las columnas y sus unidades, entregada por el docente.

## Columnas que agrega el código (no se guardan en el Excel)

| Columna | Dónde se crea | Descripción | Unidad |
|---|---|---|---|
| `hora` | `datos.preparar_conteos` | `hora_inicio` como número (07:00 → 7.0) | h |
| `dia` | `datos.preparar_conteos` | Días desde el 20 de septiembre (0 a 49) | días |
| `aves_limpias` | `limpieza.limpiar_conteos` | Conteo corregido (sin vacíos ni ceros de más) | aves |
| `correccion` | `limpieza.limpiar_conteos` | "atípico", "faltante" o vacío | — |
| `n` / columnas por especie | `modelo.totales_diarios` | Total del día N_d, con las colas triangulares | aves/día |
