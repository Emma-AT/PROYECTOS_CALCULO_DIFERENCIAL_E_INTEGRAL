# Bitácora de supuestos y decisiones

| N.º | Decisión o supuesto | Justificación |
|---|---|---|
| 1 | El Excel original no se modifica; todo el procesamiento se hace en memoria | Requisito del proyecto (lectura directa con `pandas`) |
| 2 | Los **8 valores faltantes** de `potencia_uV2_Hz` se completan por **interpolación lineal en la frecuencia, dentro de cada época** | Lo pide el enunciado; el espectro es continuo en f y solo faltan valores aislados. No se mezclan épocas distintas |
| 3 | Las bandas se integran con límites cerrados: theta 4–8, alfa 8–12, beta 12–30 Hz; la frecuencia de borde (8 y 12 Hz) entra en ambas bandas vecinas | Es la definición de la hoja `Parametros`; es la forma usual de dividir un intervalo en integrales consecutivas |
| 4 | **Simpson** es la regla principal y el **trapecio** se usa para comparar | Simpson es de orden superior (error ∝ h⁴ contra h² del trapecio) y exacta hasta cúbicas |
| 5 | Si una banda tiene un número impar de subintervalos, se usa Simpson 3/8 en los últimos tres | Mantiene el orden de precisión sin descartar datos |
| 6 | **Artefactos de movimiento:** una época es atípica si su potencia total tiene puntaje z modificado (mediana y MAD, por viaje) mayor que **10** | La mediana y el MAD no se distorsionan con el propio artefacto. El criterio clásico z > 3,5 (Iglewicz y Hoaglin, 1993) marcaba también la época 17 del viaje 1, que el video clasifica como somnolienta (z = 4,3): se habría descartado una época legítima. Los artefactos reales tienen z = 96 y z = 45 |
| 7 | Las épocas con artefactos **no se borran**: se analizan **con y sin ellas** (AUC y escenarios) | Evita eliminar datos sin justificar y mide el efecto del artefacto |
| 8 | Se evalúa la alarma **por época** de 5 min (una decisión por época) | Es la resolución de las etiquetas de video |
| 9 | Alarma: suena si I ≥ c (el índice crece con la somnolencia) | Pθ + Pα aumentan y Pβ disminuye al dormirse |
| 10 | Entre los umbrales con sensibilidad ≥ 0,9 se elige el de **menor costo** (8·omisiones + 1·falsas alarmas); si hay empate, el mayor umbral | Criterio de éxito del enunciado; el mayor umbral es el menos molesto |
| 11 | Falsas alarmas por hora = falsas alarmas ÷ horas de conducción **alerta** evaluadas (épocas alertas × 5 min ÷ 60) | Mide cuánto molesta la alarma a un chofer que sí está alerta |
| 12 | El AUC se calcula con la regla del trapecio sobre los puntos (FPR, TPR) | Lo pide el enunciado; coincide con el estadístico de Mann–Whitney (0,9479) |
| 13 | Escenarios: base (parámetros de la hoja), «chofer prioritario» (costo de falsa alarma ×10) y «equipo sin filtro de artefactos» | Tres alternativas factibles que cambian el costo o el equipo |
| 14 | La verificación analítica usa S(f) ≈ A·f^b ajustada en escala log-log al espectro medio | Permite integrar con la antiderivada exacta y comparar con la regla numérica |
| 15 | Los datos son simulados: los resultados no son registros oficiales ni validan el dispositivo en la vida real | Aclaración del enunciado |

## Limitaciones conocidas
- Solo hay 46 épocas utilizables (16 somnolientas y 30 alertas) de 2 viajes: las estimaciones tienen incertidumbre grande (sensibilidad 16/16, IC 95 % de Clopper–Pearson: 79,4 %–100 %).
- El umbral óptimo (1,724) coincide con el índice observado de una época somnolienta; cualquier valor entre 1,704 y 1,724 da el mismo resultado en estos datos.
- La ley de potencias no reproduce el pico alfa (~10 Hz).
