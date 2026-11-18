# Bitácora de supuestos

Anotar aquí cada decisión con su fecha y su justificación.

| Fecha | Supuesto o decisión | Justificación |
|---|---|---|
| | Un valor de viento es "pico" si supera 35 m/s o si se aleja más de 8 m/s de la mediana móvil de 5 horas. | Un anemómetro no registra saltos así de una hora a otra; en la base hay un valor de 39,84 m/s. |
| | Picos y faltantes de viento (14) se reemplazan por interpolación lineal en el tiempo. | El viento cambia de forma continua; son horas aisladas (< 1 % de los datos). |
| | Los 7 faltantes de producción se interpolan linealmente. | Son horas aisladas; rellenar con 0 subestimaría la energía medida. |
| | La fila i de `Opciones` corresponde a la columna i+1 de `Curvas_potencia`. | Mantener -> V47, Opción A -> opcion_A_kW, Opción B -> opcion_B_kW (según el Diccionario). |
| | Corrección por densidad: P(v, ρ) = P_curva(v)·ρ/ρ_ref, sin superar la potencia nominal. | La potencia del viento es proporcional a ρ (½ρAv³). |
| | Para la energía anual se usa la densidad media de los 60 días. | No hay temperatura anual en la base. |
| | La forma k de Weibull no cambia con la altura; solo la escala c se ajusta con la ley potencial. | Supuesto habitual cuando solo se conoce α. |
| | El VPN es incremental frente a mantener las turbinas actuales. | Así lo plantea el criterio de éxito del proyecto. |
