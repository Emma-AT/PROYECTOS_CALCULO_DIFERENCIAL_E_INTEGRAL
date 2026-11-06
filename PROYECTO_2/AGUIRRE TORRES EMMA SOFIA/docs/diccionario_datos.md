# Diccionario de Datos del Proyecto C-01_AGUIRRE
**Proyecto:** Repotenciación de la Planta Eólica Tejona  
**Archivo fuente esperado:** `datos/P09_C-01_AGUIRRE.xlsx`  

Este documento describe la estructura, tipos de variables, unidades físicas en el Sistema Internacional (SI) y validaciones esperadas en el libro de trabajo de datos meteorológicos y operativos.

---

## 1. Hoja: `Metereologia` (o `Datos_Viento`)

Contiene el registro temporal de variables climáticas medidas en la estación anemométrica de la Planta Eólica Tejona.

| Nombre de Columna | Tipo de Dato | Unidades | Rango Válido Esperado | Descripción Física / Significado |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` / `fecha_hora` | `datetime64[ns]` | N/A | Intervalos horarios continuos | Fecha y hora de la medición (estampa temporal). |
| `velocidad_viento` / `v_ms` | `float64` | $\text{m/s}$ | $[0.0, 45.0]$ | Velocidad horizontal del viento medida a la altura del anemómetro de referencia ($h_{ref} = 40\text{ m}$). |
| `direccion_viento` / `dir_deg` | `float64` | Grados ($^\circ$) | $[0.0, 360.0]$ | Dirección de procedencia del viento respecto al norte geográfico ($0^\circ = \text{Norte}$). |
| `temperatura_c` / `temp_c` | `float64` | $^\circ\text{C}$ | $[10.0, 40.0]$ | Temperatura ambiente superficial a nivel de estación. |
| `presion_pa` / `presion_hpa` | `float64` | $\text{Pa}$ o $\text{hPa}$ | $[85\,000, 105\,000]\text{ Pa}$ | Presión atmosférica local (considerar altitud de Tejona ~ $500$ m.s.n.m.). |

### Criterios de Calidad de Datos:
1. **Valores nulos o faltantes (`NaN`):** Deben identificarse e imputarse mediante interpolación lineal o sustitución temporal coherente (evitar caídas bruscas a cero).
2. **Picos anómalos (Spikes de anemómetro):** 
   - Velocidades negativas ($v < 0$): Error de sensor $\to$ reasignar o filtrar.
   - Velocidades desmedidas ($v > 35\text{ m/s}$): Picos no físicos en Tejona $\to$ verificar o acotar.
   - Variaciones abruptas: $|\Delta v / \Delta t| > 15\text{ m/s por hora}$ atribuibles a fallas de comunicación.

---

## 2. Hoja: `Turbina_Existente`

Parámetros técnicos y operativos de la flota de aerogeneradores actualmente en operación en Tejona (e.g., Vestas V47-660 kW o similar según especificación del caso).

| Parámetro | Tipo | Unidades | Descripción |
| :--- | :--- | :--- | :--- |
| `modelo` | `string` | N/A | Identificador del aerogenerador existente. |
| `potencia_nominal_kw` | `float64` | $\text{kW}$ | Capacidad nominal de generación eléctrica activa ($P_{nom}$). |
| `diametro_rotor_m` | `float64` | $\text{m}$ | Diámetro del círculo de barrido del rotor ($D$). |
| `altura_buje_m` | `float64` | $\text{m}$ | Altura del buje (*hub height*) sobre el nivel del suelo ($h$). |
| `v_in` | `float64` | $\text{m/s}$ | Velocidad de conexión (*cut-in wind speed*). |
| `v_rated` | `float64` | $\text{m/s}$ | Velocidad nominal (*rated wind speed*). |
| `v_out` | `float64` | $\text{m/s}$ | Velocidad de desconexión por seguridad (*cut-out wind speed*). |
| `n_unidades` | `int64` | Adimensional | Número total de turbinas instaladas en el parque. |

---

## 3. Hoja: `Turbina_Repotenciacion`

Especificaciones técnicas del nuevo modelo de turbina evaluado para la repotenciación (*repowering*).

| Parámetro | Tipo | Unidades | Descripción |
| :--- | :--- | :--- | :--- |
| `modelo` | `string` | N/A | Denominación del modelo moderno de alta eficiencia. |
| `potencia_nominal_kw` | `float64` | $\text{kW}$ | Nueva capacidad unitaria de generación ($P_{nom}$). |
| `diametro_rotor_m` | `float64` | $\text{m}$ | Diámetro mayor para maximizar captura de energía ($D$). |
| `altura_buje_m` | `float64` | $\text{m}$ | Nueva altura de torre para aprovechar el perfil vertical de viento ($h$). |
| `v_in` | `float64` | $\text{m/s}$ | Velocidad de conexión. |
| `v_rated` | `float64` | $\text{m/s}$ | Velocidad nominal. |
| `v_out` | `float64` | $\text{m/s}$ | Velocidad de desconexión. |
| `n_unidades_propuestas` | `int64` | Adimensional | Número propuesto de nuevas turbinas en el rediseño. |

---

## 4. Hoja: `Curvas_Potencia`

Curvas tabuladas de potencia en función de la velocidad del viento para condiciones de densidad estándar de referencia ($\rho_{ref} = 1.225\text{ kg/m}^3$).

| Nombre de Columna | Tipo de Dato | Unidades | Descripción |
| :--- | :--- | :--- | :--- |
| `v_ms` | `float64` | $\text{m/s}$ | Velocidad del viento en paso regular (usualmente $0.5$ o $1.0\text{ m/s}$). |
| `potencia_existente_kw` | `float64` | $\text{kW}$ | Potencia entregada por la turbina existente a esa velocidad. |
| `potencia_nueva_kw` | `float64` | $\text{kW}$ | Potencia entregada por la turbina de repotenciación a esa velocidad. |
| `cp_existente` | `float64` | Adimensional | Coeficiente de potencia aerodinámico ($C_p$). |
| `cp_nueva` | `float64` | Adimensional | Coeficiente de potencia aerodinámico ($C_p$). |

---

## 5. Hoja: `Parametros_Economicos`

Datos para la evaluación de rentabilidad del proyecto a lo largo de su vida útil.

| Variable | Tipo | Unidades | Descripción |
| :--- | :--- | :--- | :--- |
| `inversion_capex_usd` | `float64` | $\text{USD}$ | Costo total de inversión inicial (desmantelamiento + turbinas + obra civil + interconexión). |
| `precio_energia_usd_kwh`| `float64` | $\text{USD/kWh}$ | Tarifa o precio de venta de la energía generada contractualmente. |
| `delta_opex_anual_usd` | `float64` | $\text{USD/año}$ | Variación neta en costos anuales de operación y mantenimiento ($\Delta\text{OPEX}$). |
| `tasa_descuento` | `float64` | Fraccional | Tasa de corte o costo de capital del proyecto ($r$, e.g., $0.08$ para $8\%$). |
| `vida_util_anios` | `int64` | Años | Horizonte temporal de evaluación económica ($N = 20\text{ o }25\text{ años}$). |
