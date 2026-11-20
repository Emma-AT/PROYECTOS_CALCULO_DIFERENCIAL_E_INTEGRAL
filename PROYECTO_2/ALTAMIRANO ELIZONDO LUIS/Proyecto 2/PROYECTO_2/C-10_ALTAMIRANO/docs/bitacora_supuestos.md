# Bitácora de supuestos y tratamiento de datos

Conteos obtenidos con `informe_depuracion` sobre el archivo P05_C-10_ALTAMIRANO.xlsx.

| # | Hallazgo | Decisión | Justificación | Cómo se probó que no cambia la conclusión |
|---|---|---|---|---|
| 1 | G04 tiene un plazo de 216 h (168 h + 48 h); los otros, 168 h | T se calcula por tarea y grupo con la hoja Tareas | La ampliación es parte de la estrategia de G04; usar 168 h distorsiona su F | Prueba `test_conteos_con_los_datos_reales` |
| 2 | 1182 registros; 15 son intentos repetidos (1167 entregas finales) | Se conserva el último intento | El diccionario dice que cuenta el último; el primero suele traer la nota vacía | Prueba `test_conserva_solo_el_ultimo_intento` |
| 3 | 4 notas mayores que 100: 513, 894, 715 y 776 | Se dividen entre 10 (51,3; 89,4; 71,5; 77,6) | Parecen un decimal corrido (error de digitación) y quedan en rango | Descartarlas o poner tope 100: G03 sigue siendo la elegida |
| 4 | 9 notas vacías después de depurar | Se excluyen del promedio | No se inventan datos | Imputar la media de grupo y tarea: sin cambio en la decisión |
| 5 | Cada grupo debería tener 304 entregas (38 estudiantes × 8 tareas); hay entre 288 y 296 | Se declara como limitación; las no entregas no entran en F ni en la nota media | La base no registra a quienes no entregaron | Contándolas como 0: G03 sigue siendo la elegida |
| 6 | 70 entregas tardías (después del cierre de su grupo) | No entran en F (la F usa solo entregas a tiempo), sí en la nota media y en el % de tardías | Así lo pide el proyecto | |
| 7 | Ninguna entrega ocurre antes de la apertura | Se deja la marca `antes_apertura` por si llegara otra base | Control de calidad | |
| 8 | Los grupos no se asignaron al azar | Se declara como limitación en la recomendación | Las diferencias pueden deberse en parte a los estudiantes | Intervalo del 95 % por remuestreo de estudiantes |
