# Diccionario de datos

Fuente: `datos/P09_C-01_AGUIRRE.xlsx` (datos simulados con fines didácticos).

## Viento_horario (1440 registros, 1 por hora, 60 días)

| Columna | Descripción | Unidad |
|---|---|---|
| fecha_hora | Fecha y hora del registro | fecha y hora |
| velocidad_m_s | Velocidad del viento a 55 m | m/s |
| direccion_grados | Dirección de procedencia (0 = norte) | grados |
| temperatura_C | Temperatura del aire | °C |
| produccion_planta_MWh | Energía entregada por la planta en esa hora | MWh |

## Curvas_potencia (cada 0,5 m/s, de 0 a 25 m/s)

| Columna | Descripción | Unidad |
|---|---|---|
| velocidad_m_s | Velocidad del viento | m/s |
| actual_V47_kW | Potencia de una turbina actual (Vestas V47), ρ = 1,225 kg/m³ | kW |
| opcion_A_kW | Potencia de una turbina de la opción A | kW |
| opcion_B_kW | Potencia de una turbina de la opción B | kW |

## Opciones

| Columna | Descripción | Unidad |
|---|---|---|
| opcion / descripcion | Nombre de la opción | — |
| turbinas | Número de turbinas | turbinas |
| potencia_nominal_kW | Potencia nominal de cada turbina | kW |
| diametro_rotor_m | Diámetro del rotor | m |
| altura_buje_m | Altura del buje | m |
| inversion_colones | Inversión inicial | colones |
| mantenimiento_anual_colones | Operación y mantenimiento | colones/año |

## Parametros

Altura del anemómetro (m), exponente de cizalladura (—), k y c de la distribución
anual (—, m/s), presión media (kPa), constante del aire seco (J/(kg·K)), densidad de
referencia (kg/m³), precio de la energía (colones/kWh), tasa de descuento (%) y vida
útil (años).
