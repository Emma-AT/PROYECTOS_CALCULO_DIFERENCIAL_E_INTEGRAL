# Bitácora de supuestos y decisiones

Cada decisión sobre los datos o el modelo, con su justificación y su efecto.

## Datos

1. **El Excel original no se modifica.** Se lee con `pandas.read_excel(ruta, sheet_name=None)`
   y las correcciones van en una columna nueva (`aves_limpias`).
2. **Horas sin conteo (58 vacíos).** Casi todas están en horas con lluvia (54 de 58). Se rellenan
   con interpolación lineal **dentro del mismo día y especie**, porque el paso cambia poco de una
   hora a la siguiente. Si el vacío está en la primera o la última hora del día, se copia la hora
   más cercana.
3. **Conteos con un cero de más.** Se marca un conteo si es más de **5 veces** el promedio de sus
   horas vecinas (criterio del enunciado) **y además es de al menos 20 aves**.
   - El mínimo de 20 aves evita marcar variaciones normales en conteos muy pequeños: pasar de 1 a 5
     aves es azar, no un error de digitación. Sin ese mínimo se marcaban 2 conteos de 4 y 5 aves
     en días casi sin paso.
   - Se detectaron 4 casos: 32 470 (gavilán aludo, 02/10, 12:00), 430 (zopilote, 08/10, 8:00),
     113 450 (zopilote, 18/10, 11:00) y 17 440 (zopilote, 07/11, 11:00). Se reemplazan por
     interpolación entre sus horas vecinas.
   - **Sensibilidad:** con factor 3 se marcan 15 conteos, con factor 10 se marcan 3. En los tres
     casos la fecha óptima es la misma (día 18). La decisión no depende de este criterio.

## Modelo

4. **Tasa por hora.** Dentro de cada bloque de una hora la tasa se toma constante: el área del
   bloque es el conteo (aves/h × 1 h = aves).
5. **Horas no observadas (colas triangulares).** Antes de las 7:00 la tasa sube en línea recta
   desde 0 (en h_i = 6:12) hasta la tasa de la hora 7:00. Después de las 16:00 baja en línea recta
   hasta 0 (en h_f = 17:06). Las colas agregan un 4,4 % a lo contado.
   **Sensibilidad:** mover h_i y h_f ±0,5 h cambia el total en ±2,2 %, pero no la fecha óptima.
6. **Serie diaria.** n(t) son los totales diarios ubicados en t = 0, 1, …, 49 (días desde el 20/9).
   Las integrales de la temporada usan la **regla del trapecio** (coincide con la suma de los
   totales diarios con un error menor que 0,1 %). Simpson se usa para comparar: se aleja hasta
   un 3 % porque supone una curva suave y los datos diarios tienen saltos por la lluvia.
7. **Campaña.** Una campaña de L días que empieza el día a cubre el intervalo [a, a + L]. En el
   calendario son los días a, a + 1, …, a + L − 1 (por ejemplo, del 8 al 28 de octubre).
8. **Condición del óptimo.** G'(a) = n(a + L) − n(a) = 0 se comprueba con la serie suavizada
   (media móvil de 5 días), porque los totales diarios cambian mucho de un día a otro por la
   lluvia. El cambio de signo de G' ocurre en a ≈ 19,0, junto al óptimo discreto a = 18.
9. **Turno.** Se usa el perfil horario promedio de los días de la campaña, para las tres especies
   juntas. Solo se consideran horas dentro del horario de conteo (7:00 a 16:00). Se supone que la
   forma del perfil horario no cambia mucho entre días.
10. **Fracción registrada** = (fracción del paso en las fechas) × (fracción del día en el turno).
    Supone que el horario de paso es parecido todos los días de la campaña.
11. **Campaña tradicional.** El Excel solo da su fecha de inicio (día 11 = 1 de octubre). Para
    compararla en igualdad de condiciones se le asigna su mejor turno de 6 horas, como a las demás.

## Limitaciones

- Los datos son de una sola temporada (simulada). El calendario real cambia de un año a otro.
- La lluvia no se modela: solo se rellenan sus huecos.
- La recomendación maximiza el **total de aves**. Como el zopilote domina el total, la campaña
  óptima registra menos gavilán aludo (67 %) que la tradicional (97 %). Si el programa quiere
  priorizar especies, conviene la opción equilibrada.
