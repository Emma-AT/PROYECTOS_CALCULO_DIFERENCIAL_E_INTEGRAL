# Bitácora de supuestos y decisiones

Cada decisión indica **qué** se hizo, **por qué** y **dónde** está en el código. Los números
salen de `python -m src.reporte` (`resultados/tablas/`).

## 1. Datos

| # | Decisión | Justificación | Código |
|---|---|---|---|
| D1 | El Excel se lee con `pd.read_excel(ruta, sheet_name=None)` y nunca se modifica. | Requisito del curso; trazabilidad. | `limpieza.leer_base` |
| D2 | Se agrega el punto C(0) = 0 a cada perfil. | Se supone que el voluntario llega sin cafeína en sangre (protocolo usual de estos estudios); en el instante de la toma aún no hay absorción. Sin este punto se pierde el área de 0 a 0,25 h. | `modelo.analizar_voluntario` |
| D3 | **Atípicos:** un punto interior es atípico si difiere más de 1,8 veces del valor esperado por interpolación log-lineal entre sus vecinos válidos; se marcan uno a uno (el peor primero). | En un perfil farmacocinético la curva es suave; un salto de ×2 entre muestras consecutivas no es fisiológico. La escala logarítmica respeta el decaimiento exponencial. El umbral 1,8 no marca ningún punto de perfiles suaves (prueba `test_detecta_un_pico_aislado_sin_falsos_positivos`). | `limpieza.detectar_atipicos` |
| D4 | Se detectaron 3 atípicos: V17 a 1 h (13,57 mg/L; esperado 4,04; ×3,4), V04 a 4 h (3,60 mg/L; esperado 1,30; ×2,8) y V21 a 10 h (2,39 mg/L; esperado 0,76; ×3,2). El siguiente punto más alejado de sus vecinos no llega a ×1,8. | V21 está en la fase terminal: dejarlo habría sesgado su k. | `bitacora_limpieza.csv` |
| D5 | **Faltantes interiores** (V31 0,5 h; V32 3 h; V44 0,25 h; V45 4 h) y atípicos: interpolación lineal en el tiempo. | Para la regla del trapecio, interpolar linealmente equivale a unir los vecinos con una recta: no se inventa área. | `limpieza.imputar_voluntario` |
| D6 | **Faltantes en 24 h** (V31, V48): extrapolación C(24) = exp(b + m·24) con la recta de ln C de la fase terminal. | La cola impropia C(24)/k necesita C(24); la recta terminal es el propio modelo de eliminación. | `limpieza.imputar_voluntario` |
| D7 | Los valores imputados **no** se usan para estimar k. | Evita circularidad (k no se estima con datos que dependen de k). | `analizar_todos(usar_en_k=...)` |
| D8 | Pesos iguales a 45,0 kg (V44, V48, V57) se conservan. | Pueden ser un piso del instrumento, pero el peso no entra al modelo; V/peso de esos voluntarios es plausible. | — |
| D9 | Tiempos de reacción: se aceptan valores entre 100 y 1000 ms. | Rango fisiológico del tiempo de reacción simple. Ningún registro quedó fuera (128–400 ms). | `limpieza.revisar_pruebas` |
| D10 | La prueba de atención en t = 0 corresponde a C = 0 mg/L; en los demás tiempos se usa la concentración medida en el mismo instante. | Las mallas de tiempo coinciden (0,5; 1; 2; 4; 6; 8; 12 h). | `limpieza.unir_atencion` |

## 2. Modelo

| # | Supuesto | Justificación / límite |
|---|---|---|
| M1 | Modelo de un compartimento con absorción y eliminación de primer orden. | Estándar para cafeína oral (absorción casi completa, cinética lineal en dosis habituales < 10 mg/kg). R² medio del ajuste: 0,96. |
| M2 | ka = 3 h⁻¹ igual para todos (hoja `Parametros`). | Dato del problema. La sensibilidad muestra que ±20 % en ka no cambia ninguna decisión. |
| M3 | k desde la fase terminal (t ≥ 6 h). | A partir de ~6 h la absorción terminó (e^{−3·6} ≈ 10⁻⁸) y ln C es lineal (R² terminal medio 0,995). |
| M4 | AUC = trapecio en [0, 24] + cola C(24)/k. | La cola es la integral impropia exacta de C(24)e^{−k(t−24)}. Aporta 4 % del AUC (mediana) y hasta 40 % (V15, t½ = 17,4 h). |
| M5 | La regla del trapecio sobrestima el AUC en ≈ 3 % con este muestreo (salto 12 → 24 h). | Verificado con datos sintéticos (prueba `test_analizar_voluntario_recupera_parametros...`); por eso V queda subestimado en ≈ 3 %. Simpson es peor aquí (5,7 % de error contra la integral exacta del modelo) porque la parábola por 10, 12 y 24 h no sigue a la exponencial. |
| M6 | Linealidad: C es proporcional a la dosis y las tomas se suman (superposición). | Válido para cinética lineal. Permite escalar dosis (máximo diario) y sumar días previos. |
| M7 | Persona representativa de cada grupo: mediana de k y de V del grupo. | La mediana es robusta a extremos (V15). Se complementa con el % de personas del grupo que cumplen el umbral de sueño. |
| M8 | Relación atención–concentración lineal: mejora = 3,9 + 23,9·C (ms), R² = 0,77. | Ajuste por mínimos cuadrados sobre 480 pruebas; se usa solo como indicador (no en la decisión). |
| M9 | Las bebidas aportan solo su cafeína (otros componentes de las energéticas se ignoran). | Límite: azúcar, taurina u otros efectos no se modelan. |

## 3. Decisión

| # | Regla | Justificación |
|---|---|---|
| R1 | Criterio oficial: plan del catálogo con más H_ef, con C(23) < 1 mg/L y cafeína ≤ 400 mg; empate (< 0,01 h) → menos cafeína. | Criterio de éxito del enunciado. |
| R2 | Criterio prudente: además, ≥ 80 % de las personas del grupo con C(23) < 1 mg/L. | La persona típica puede cumplir mientras casi la mitad del grupo no (p. ej. plan B en eliminación normal: 55 %). El 80 % es un supuesto de diseño de la campaña, ajustable en la aplicación. |
| R3 | Plan ajustado (exploratorio): búsqueda exhaustiva de 1 a 3 tomas de las bebidas de la base, a horas enteras de 8:00 a 18:00 (≈ 37 700 combinaciones por grupo). | Responde directamente «cuántas tomas, de qué bebida y hasta qué hora» sin limitarse a los seis planes. |
| R4 | Escenarios: base (día 1), semana de exámenes (5 días seguidos) y acostarse 1 h antes. | Son situaciones factibles para el público de la campaña. |
| R5 | Sensibilidad: ±20 % en k, V, ka, umbral de efecto y umbral de sueño; ±1 h en la hora de dormir. | k, V, umbral de sueño y hora de dormir cambian la decisión en 3 casos cada uno; ka y umbral de efecto en ninguno. |
| R6 | Hora límite: bisección de C(23; t_toma) = c_sueño en [8, 23 − t_max]. | En ese tramo C al acostarse crece con la hora de la toma (es monótona), condición para que la bisección converja. |

## 4. Limitaciones conocidas

* Datos simulados; los resultados no son una recomendación médica.
* Una sola dosis de prueba (200 mg); se supone cinética lineal para 35–160 mg.
* Se ignora la tolerancia por consumo habitual (la correlación entre tazas habituales y t½ es 0,07).
* El umbral de sueño se evalúa en un instante (23:00); en planes del catálogo la concentración ya
  decrece a esa hora, por lo que es el máximo de la noche.
