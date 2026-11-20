# Diccionario de datos

## Variables del archivo entregado (hoja *Diccionario* del Excel)

| Hoja | Variable | Significado | Unidad / tipo |
|---|---|---|---|
| Entregas | tarea | Código de la tarea (T1 a T8) | texto |
| Entregas | grupo | Grupo del curso (G01 a G04) | texto |
| Entregas | estudiante | Código anónimo del estudiante | texto |
| Entregas | intento | Número de intento de entrega (cuenta el último) | entero |
| Entregas | fecha_hora_entrega | Fecha y hora de la entrega en Mediación Virtual | fecha y hora |
| Entregas | nota | Nota obtenida en la tarea | puntos (0 a 100) |
| Tareas | apertura, cierre | Apertura y cierre de la tarea por grupo | fecha y hora |
| Grupos | estrategia | Estrategia contra la procrastinación aplicada | texto |
| Grupos | estudiantes | Número de estudiantes del grupo | personas |
| Grupos | horas_docente_extra_por_tarea | Horas docentes adicionales que exige la estrategia | h por tarea |
| Parametros | Duración normal del plazo | 168 | h |
| Parametros | Ventana de las últimas horas | 24 | h |
| Parametros | Diferencia mínima de nota relevante | 1 | puntos |
| Parametros | Nota máxima posible | 100 | puntos |

## Variables que calcula `depurar_entregas` (src/limpieza.py)

| Variable | Significado | Unidad |
|---|---|---|
| plazo_h (T) | Cierre menos apertura, por tarea y grupo (168 h; 216 h en G04) | h |
| horas (t) | Entrega menos apertura | h |
| tau | horas / plazo_h: fracción del plazo transcurrida | fracción (0 a 1; mayor que 1 si es tardía) |
| tardia | La entrega ocurrió después del cierre | lógico |
| nota_original, nota_atipica | Nota tal como venía y marca de las corregidas por ser mayores que 100 | puntos, lógico |

## Indicadores que calcula `resumen_grupo` (src/escenarios.py)

| Indicador | Significado | Unidad |
|---|---|---|
| ip_obs | Índice de procrastinación observado, integral de 1 − F (0: todo al abrir; 1: todo al cierre) | fracción |
| k | Intensidad de la procrastinación del modelo, estimada por bisección | 1/h |
| ultimas_obs / ultimas_modelo | Fracción de las entregas a tiempo hechas en las últimas 24 h | fracción |
| tardias_pct | Entregas después del cierre | % de las entregas |
| nota_media | Promedio de las notas de todas las entregas | puntos |
| no_entregas_pct | Entregas que no existen respecto de estudiantes × 8 tareas | % |
