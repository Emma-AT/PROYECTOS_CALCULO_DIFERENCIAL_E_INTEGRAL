# Bitácora de Supuestos Técnicos y Económicos
**Proyecto:** Repotenciación de la Planta Eólica Tejona (`C-01_AGUIRRE`)  
**Autor:** Emma Aguirre Torres  
**Ubicación:** Cordillera de Tilarán, Guanacaste, Costa Rica  

---

## 1. Contexto Geográfico y Físico de Tejona

1. **Topografía y Rugosidad del Terreno:**
   - La Planta Eólica Tejona se localiza en una zona de colinas complejas con régimen de vientos alisios acelerados por efecto Venturi entre cuencas lacustres y montañosas.
   - Longitud de rugosidad superficial $z_0$: Se adopta un terreno clase pastizal/colina baja con rugosidad típica entre $0.03\text{ m}$ y $0.10\text{ m}$.
   - Exponente de cizalladura vertical del viento ($\alpha$ de Hellmann): Por defecto se utiliza $\alpha \approx 0.14$ a $0.20$ según los registros experimentales de la zona cuando no se cuenta con múltiples anemómetros a diferente cota.

2. **Condiciones Atmosféricas y Densidad del Aire:**
   - Altitud promedio del parque: $\approx 500\text{ a }600\text{ m.s.n.m.}$, lo cual ocasiona presiones barométricas medias del orden de $94\,000\text{ a }96\,000\text{ Pa}$.
   - Densidad de referencia según norma internacional IEC 61400-12-1: $\rho_{ref} = 1.225\text{ kg/m}^3$ ($T = 15^\circ\text{C}$, $P = 101\,325\text{ Pa}$).
   - Modelo termodinámico: Gas ideal de aire seco con constante específica $R_{aire} = 287.058\text{ J/(kg}\cdot\text{K)}$.
     $$\rho = \frac{P_{atm}}{R_{aire} \cdot (T_C + 273.15)}$$

---

## 2. Supuestos de Modelado Aerodinámico y Numérico

1. **Perfil Vertical de Viento (Ley de Hellmann):**
   - Para proyectar la velocidad del viento desde la altura del mástil anemométrico ($h_{ref} = 40\text{ m}$) a la altura del buje de la turbina ($h_{buje}$):
     $$v(h_{buje}) = v_{ref} \cdot \left(\frac{h_{buje}}{h_{ref}}\right)^\alpha$$

2. **Límite Teórico de Betz:**
   - Ningún rotor eólico de eje horizontal puede extraer más del $16/27 \approx 59.26\%$ de la energía cinética del flujo de viento incidente:
     $$P_{viento} = \frac{1}{2} \rho A v^3 \implies C_p(v) = \frac{P_{turbina}(v)}{P_{viento}(v)} \le \frac{16}{27}$$
   - Se debe garantizar numéricamente que las curvas de potencia importadas cumplan esta cota física en todo el rango operativo.

3. **Corrección de Curvas de Potencia por Densidad:**
   - Conforme a IEC 61400-12-1, para turbinas con control activo de paso de pala (*pitch controlled*), en la región 2 (por debajo de la velocidad nominal), la velocidad efectiva se escala mediante:
     $$v_{corr} = v \cdot \left(\frac{\rho}{\rho_{ref}}\right)^{1/3}$$
   - La potencia nominal (región 3) se mantiene fija al límite del generador eléctrico.

4. **Distribución Estadística de Viento (Weibull):**
   - La distribución bivariada de Weibull se parametriza mediante el método de los momentos:
     - $k$: factor de forma (adimensional, típicamente $k \in [1.8, 2.5]$ para vientos con moderada variabilidad estacional).
     - $c$: factor de escala en $\text{m/s}$ relacionado con la velocidad media $\bar{v} = c \cdot \Gamma(1 + 1/k)$.
   - La integración de la potencia esperada $\bar{P} = \int_0^\infty P(v) f(v) dv$ se resuelve numéricamente mediante la regla de Simpson 1/3 compuesta.

---

## 3. Factores de Pérdida en Parque Eólico ($L_{total}$)

Para convertir la producción de energía bruta en neta anual ($AEP_{net}$), se asume una tasa global combinada de pérdidas $L \approx 12\% - 16\%$ compuesta por:
- Pérdidas por efecto estela entre turbinas (*wake effect*): $6.0\%$ a $8.0\%$.
- Disponibilidad técnica de aerogeneradores y parque: $3.0\%$.
- Pérdidas eléctricas internas (cables, transformadores, subestación): $2.5\%$.
- Pérdidas ambientales (ensuciamiento de palas, degradación de borde de ataque): $1.5\%$.
- Paradas por restricciones de red y mantenimiento programado: $1.0\%$.

Factor multiplicador de rendimiento neto: $\eta_{parque} = 1 - L$.

---

## 4. Supuestos Financieros de Repotenciación

1. **Horizonte de Evaluación:**
   - Vida útil de proyecto: $20$ o $25$ años.
2. **Estructura del Flujo de Caja Incremental:**
   - Inversión inicial ($I_0 = \text{CAPEX}$): Ocurre en el año 0.
   - Flujo de caja neto anual ($CF_t$):
     $$CF_t = (\Delta E_{anual} \cdot \text{Precio}_{kWh}) - \Delta\text{OPEX}_{anual}$$
     donde $\Delta E_{anual} = E_{anual, nueva} - E_{anual, existente}$.
3. **Costo de Capital / Tasa de Descuento ($r$):**
   - Tasa de descuento real de referencia: $r = 8.0\%$ anual (configurable según escenario de riesgo país y costo ponderado de capital WACC).
4. **Criterio de Aceptación:**
   - La repotenciación es económicamente viable si el Valor Presente Neto es positivo ($\text{VPN} > 0$).
