# Guía de estudio para la defensa

Este documento es para que entiendas y puedas explicar cada pieza con tus palabras.
Léelo con el código abierto, no lo memorices.

## Resultados clave (con tus datos)

| Grupo | Estrategia | h docentes por tarea | Nota media | Tardías | IP | k (1/h) | Últimas 24 h obs. / modelo |
|---|---|---|---|---|---|---|---|
| G01 | Sin intervención | 0,0 | 70,8 | 10,0 % | 0,801 | 0,733 | 55,8 % / 60,6 % |
| G02 | Recordatorio 72 h | 0,5 | 72,2 | 8,0 % | 0,780 | 0,418 | 52,8 % / 56,3 % |
| G03 | Entrega parcial | 6,2 | **78,3** | 2,4 % | 0,700 | 0,080 | 39,8 % / 40,1 % |
| G04 | Plazo +48 h | 1,0 | 72,8 | 3,7 % | 0,808 | 0,706 | 56,2 % / 57,4 % |

Decisión: **G03**. La diferencia con G04 es de 5,5 puntos (intervalo del 95 %: 1,1 a 9,9), mucho mayor que 1 punto.

## Pregunta específica 1: ¿por qué IP = promedio de t/T?

Sea τ = t/T en [0, 1] con acumulada F y densidad f. El promedio es E[τ] = ∫₀¹ τ f(τ) dτ.
Integración por partes con u = τ y dv = f dτ, o sea v = F − 1:

E[τ] = [τ(F(τ) − 1)]₀¹ − ∫₀¹ (F(τ) − 1) dτ = 0 + ∫₀¹ (1 − F(τ)) dτ.

El término de frontera es 0 en τ = 1 (porque F(1) = 1) y en τ = 0 (por el factor τ).
Con el cambio t = Tτ: (1/T)∫₀ᵀ (1 − F(t)) dt = ∫₀¹ (1 − F(τ)) dτ = E[τ] = promedio de t/T.
En el código: `indice_procrastinacion(tau)` (trapecio) coincide con `tau.mean()` (prueba `test_ip_empirico_es_el_promedio_de_t_sobre_T`).

## Pregunta específica 2: la fracción de las últimas 24 h

Con u = 1 + k(T − t), du = −k dt. Cuando t = 0, u = 1 + kT; cuando t = T, u = 1.

∫₀ᵀ k/(1 + k(T − t)) dt = ∫₁^(1+kT) du/u = ln(1 + kT).

Dividiendo entre ln(1 + kT), f_k integra 1. Para las últimas 24 h, t va de T − 24 a T, y u va de 1 + 24k a 1:

∫_(T−24)ᵀ f_k dt = ln(1 + 24k) / ln(1 + kT).

También sale F_k(t) = 1 − ln(1 + k(T − t))/ln(1 + kT).
Verificado en el código con Simpson (error menor que 10⁻⁴; en la práctica menor que 10⁻⁸).

## Pregunta específica 3: ¿por qué la bisección encuentra un único k?

Con F_k de arriba, 1 − F_k(t) = ln(1 + k(T − t))/ln(1 + kT). Integrando:

IP_modelo(k) = g(κ) = 1 + 1/κ − 1/ln(1 + κ), con κ = kT.

- g es continua para κ > 0.
- Límites: g → 1/2 cuando κ → 0, y g → 1 cuando κ → ∞. Por eso solo se puede ajustar un IP entre 0,5 y 1 (el código lanza un error si no).
- g es estrictamente creciente: g′(κ) = 1/((1+κ) ln²(1+κ)) − 1/κ² es positiva si κ/√(1+κ) > ln(1+κ).
  Sea h(κ) = κ/√(1+κ) − ln(1+κ). Entonces h(0) = 0 y h′(κ) = (√(1+κ) − 1)² / (2(1+κ)^(3/2)) ≥ 0, así que h > 0 para κ > 0.

Por el **teorema del valor intermedio** existe un k con g = IP observado, y por ser creciente es único.
La bisección toma un intervalo [a, b] donde IP(a) < IP_obs < IP(b), evalúa el punto medio y se queda con la mitad donde sigue el cambio de signo; el intervalo se reduce a la mitad en cada paso.

**Qué limita la conclusión sobre la mejor estrategia:** los grupos no se asignaron al azar, es un solo semestre con 38 estudiantes por grupo, las entregas que no existen no están en la base, y el modelo de un solo parámetro sobrestima las últimas 24 h en G01 y G02.

## Las 10 preguntas generales (respuestas cortas con tus números)

1. **Patrones y tratamiento de faltantes y atípicos:** entregas concentradas al cierre; las de las últimas 24 h tienen notas entre 4,6 y 9,1 puntos más bajas. Último intento, 4 notas ÷10, 9 vacías excluidas (ver bitácora).
2. **Resultado teórico:** E[t] = ∫(1 − F) por partes; integral de 1/(a + bt) como logaritmo; teorema del valor intermedio para la bisección.
3. **Por qué el modelo es razonable:** el descuento hiperbólico da una densidad creciente hacia el cierre; con un solo k reproduce el IP y la fracción de las últimas 24 h con diferencias de 0,3 a 4,8 puntos porcentuales.
4. **Significado y unidades:** f_k en 1/h; F y IP sin unidad (fracciones); ∫f dt = 1 es la probabilidad total; IP es el promedio de t/T.
5. **Verificación:** ∫f_k = 1 con error menor que 10⁻⁴, IP → 0,5 cuando k → 0, Simpson contra la fórmula cerrada, IP empírico contra el promedio de t/T, bisección recuperando un k simulado con error menor que 10 %.
6. **Funciones principales:** `depurar_entregas` (limpia), `indice_procrastinacion` (trapecio), `densidad_modelo` e `ip_modelo` (Simpson), `estimar_k` (bisección), `resumen_grupo` y `elegir_estrategia`. Cada una tiene pruebas en `tests/`.
7. **Parámetro que más modifica la decisión:** la diferencia mínima de nota. Con 1 punto gana G03; si fuera mayor que 5,56 pasaría a G04, a partir de 6,14 a G02 y de 7,54 a G01. Los tratamientos de datos no cambian la decisión.
8. **Solución e impacto:** aplicar la entrega parcial obligatoria a mitad del plazo: nota media 78,3 (7,5 puntos más que sin intervención), tardías 2,4 % frente a 10,0 %, a un costo de 6,2 h docentes por tarea (unas 50 h por grupo en 8 tareas).
9. **Cuándo deja de ser válida:** si el costo docente no se puede sostener, si el cliente acepta perder más de 5,6 puntos a cambio de ahorrar horas, o si en un nuevo semestre G03 no reproduce la ventaja.
10. **Cómo medir:** IP, fracción de las últimas 24 h, % de tardías, nota media y horas docentes reales del semestre siguiente.
