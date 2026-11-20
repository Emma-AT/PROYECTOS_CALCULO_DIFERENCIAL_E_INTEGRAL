# Supuestos y decisiones iniciales

| Decisión | Justificación e implicación |
|---|---|
| No sobrescribir el Excel | Se conserva evidencia de la base asignada, incluido su hash SHA-256 |
| Interpolar tres aceleraciones internas | Reconstrucción lineal local, sin extrapolar extremos |
| Conservar seis profundidades vacías | No intervienen en b, λ, PAE ni VPN; se excluyen solo de estadísticas de profundidad |
| Conservar magnitudes y profundidades señaladas por IQR | Una señal estadística no demuestra error; recortar magnitudes sesgaría la amenaza |
| No recortar picos del acelerograma | La señal intensa es parte del evento; se desconoce evidencia de error instrumental |
| Usar años calendario completos, 1996–2025 | El enunciado declara 30 años; la ventana se infiere de los extremos del Excel, no del tiempo entre primer y último evento |
| Catálogo completo y eventos independientes | Permite tasa constante y Poisson; no se ha probado completitud ni eliminado réplicas |
| Corrección de magnitud de medio intervalo | 0,1 Mw de resolución, por lo que m_c=2,95, según el estimador solicitado |
| Promedio de aceleración para t<t0 | t0 procede de Evento, 5 s; se interpola antes de calcularlo |
| Condiciones iniciales cero | Se integra movimiento relativo al inicio del registro |
| g estándar 9,80665 m/s² | Constante física, no parámetro económico del Excel |
| Daño lineal por tramos entre 5 y 8 Mw | Respeta las curvas tabuladas y permite integral exacta de verificación |
| Simpson con 16 subdivisiones por tramo | Paneles pares dentro de cada recta; se compara con fórmula exacta y tabla sin refinar |
| Descuento continuo | El porcentaje anual de Edificacion se interpreta según e^(-rt) del enunciado |
| Ahorro constante y beneficio principal desde t=0 | Aplica literalmente el modelo asignado; se añade comprobación con demora por obra |
| Sensibilidad de descuento ±2 puntos porcentuales | Rango de análisis supuesto, no dato medido ni intervalo de confianza |
| Decisión entre tres alternativas | Se incluye no invertir, con VPN cero, para no recomendar inversiones negativas |

## Límites que deben exponerse

1. Los datos son simulados, no un diagnóstico oficial del hospital.
2. Un solo acelerograma no representa todos los posibles movimientos futuros.
3. Magnitud y daño se relacionan directamente sin atenuación por distancia ni respuesta estructural.
4. La cola de magnitudes grandes se extrapola. El máximo registrado es M=6, y la probabilidad de M≥7 depende del modelo.
5. Se omiten vidas, lesiones, interrupción del servicio, inflación, mantenimiento y otras pérdidas indirectas.
6. Corregir un sesgo constante no prueba que todo el desplazamiento residual sea físicamente real.
7. La tasa regional estacionaria y la independencia de eventos son simplificaciones.

## Seguimiento de aprendizaje

Fecha | Cambio realizado | Motivo | Prueba ejecutada | Qué puedo explicar
---|---|---|---|---
2026-10-10 | Primera implementación asistida | Iniciar el proyecto según el enunciado | Ver resultados de pytest y verificaciones | Pendiente de repaso individual
