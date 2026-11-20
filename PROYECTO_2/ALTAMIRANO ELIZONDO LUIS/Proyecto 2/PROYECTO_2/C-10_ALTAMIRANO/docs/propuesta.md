# Propuesta de proyecto (una página)

**Estudiante:** Altamirano Elizondo, Luis · C-10 · MA-0321, II Ciclo 2026
**Proyecto 5:** Procrastinación y entregas de tareas en Mediación Virtual

## Cliente y problema
La Coordinación de Docencia de la Sede del Sur (UCR) observa que una gran parte de las tareas se entrega en las últimas horas antes del cierre, lo que se asocia con trabajos apresurados, notas más bajas y entregas tardías. En el semestre anterior cada uno de cuatro grupos aplicó una estrategia distinta: ninguna (G01), recordatorio 72 h antes del cierre (G02), entrega parcial obligatoria a mitad del plazo (G03) y plazo ampliado en 48 h (G04).

## Pregunta de decisión
¿Qué estrategia contra la procrastinación debe aplicarse en todos los grupos el próximo semestre?

## Criterio de éxito
Se elige la estrategia con mayor nota media. Si otra queda a menos de 1 punto, se prefiere la que requiere menos horas docentes. El modelo debe reproducir la fracción de entregas de las últimas 24 horas de cada grupo.

## Datos y exploración inicial
El Excel tiene 1182 registros de entrega de 8 tareas en 4 grupos de 38 estudiantes, las fechas de apertura y cierre, la estrategia de cada grupo con sus horas docentes y los parámetros del problema. En la exploración inicial encontré: plazo de 216 h en G04 (no 168 h), 15 intentos repetidos, 4 notas mayores que 100 (decimal corrido), notas vacías y menos entregas que las esperadas (304 por grupo).

## Modelación
1. Depurar: último intento, notas corregidas, horas desde la apertura y entregas tardías.
2. Índice de procrastinación IP = (1/T)∫(1 − F) dt con trapecio, verificado contra el promedio de t/T.
3. Densidad por descuento hiperbólico f_k(t) = k / (ln(1+kT)(1 + k(T−t))): demostrar que integra 1 y que las últimas 24 h valen ln(1+24k)/ln(1+kT).
4. Estimar k de cada grupo por bisección, igualando el IP calculado con Simpson al observado.
5. Comparar por grupo las entregas de las últimas 24 h (observada y del modelo), tardías y nota media; elegir con el criterio del cliente y discutir limitaciones (grupos no asignados al azar).

## Productos
Código en Python con pruebas y GitHub Actions, aplicación web en Streamlit, ficha técnica y resumen ejecutivo en PDF, diapositivas y defensa oral.
