# Cómo se construyen y verifican los cálculos

## 1. Frecuencia de magnitudes

El catálogo contiene N eventos durante Y años completos, por hipótesis.
La tasa anual se calcula como λ₃=N/Y. La frecuencia para magnitudes grandes se modela por
λ(m)=λ₃·10^[-b(m−3)]. b indica qué tan rápido disminuye la frecuencia al aumentar m.

Para justificar su estimador, tomamos una densidad exponencial desplazada:

f(m)=β exp[−β(m−m_c)], m≥m_c, β=b ln(10).

Su integral en ese dominio es 1. Con u=m−m_c:

E[M]=∫ m f(m)dm = m_c∫₀∞βe^(−βu)du + ∫₀∞uβe^(−βu)du.

La primera integral vale m_c. La segunda se resuelve por partes:
∫₀∞uβe^(−βu)du = [−u e^(−βu)]₀∞ + ∫₀∞e^(−βu)du = 1/β.

Entonces E[M]=m_c+1/β. Al igualar media teórica y media de la muestra:
b=1/[ln(10)(media−m_c)]=log₁₀(e)/(media−m_c).
Las magnitudes vienen redondeadas a 0,1. El enunciado pide m_c=3−0,05=2,95.
Es una corrección por redondeo, no un dato que se cambie para conseguir otro resultado.
La ley de recurrencia se ancla en λ₃ para el umbral reportado M≥3.

La hipótesis Poisson implica P(N=0)=exp(−λT), de modo que P(N≥1)=1−exp(−λT).
Es una probabilidad regional en un intervalo, no fecha pronosticada de un terremoto.

## 2. Movimiento: integrar dos veces

Los tres huecos internos se interpolan como
a(t)=a_i+(a_(i+1)−a_i)(t−t_i)/(t_(i+1)−t_i).
Luego se calcula c=promedio de a(t) con t<t₀. Se usa a_corregida=a−c.
La hoja Evento aporta t₀. No se incluyen muestras del evento en la media previa.

El teorema fundamental del cálculo conecta a=v' y v=x'. Con v(0)=x(0)=0:
v(t)=∫₀ᵗa(u)du y x(t)=∫₀ᵗv(u)du.

Cada trapecio tiene área (t_i−t_(i−1))(y_i+y_(i−1))/2. La función
integral_acumulada suma esas áreas y conserva un resultado por muestra.
El área puede ser negativa. No equivale a sumar valores absolutos.

Si no restamos un sesgo constante c, añadimos ct a la velocidad y ct²/2 al
desplazamiento. Por eso un sesgo pequeño puede producir cientos de centímetros.
Restar una media no elimina todas las posibles derivas instrumentales.
PGA=max|a|, PGV=max|v|, PGD=max|x|. PGD del suelo no es deriva entre pisos del edificio.

IA=π/(2g)∫a_m²dt, con a_m=a/100, g=9,80665 m/s².
Unidades: (s²/m)(m²/s⁴)(s)=m/s. No es energía medida en joules.
Se buscan t5 y t95 en la integral acumulada y duración=t95−t5.

## 3. Pérdida anual esperada

La densidad de frecuencia ν(m)=−λ'(m)=b ln(10) λ(m) tiene unidades eventos/(año·Mw).
No está normalizada a 1. D(m) es fracción de daño, por lo que el porcentaje se divide entre 100.
PAE=V∫₅⁸D(m)ν(m)dm. Unidades: colones × fracción × eventos/año = colones/año.
Un evento pequeño causa menos daño, pero puede aportar bastante por ser más frecuente.

Construcción del modelo continuo: unimos cada par de datos de daño con una recta,
sin ajustar una curva arbitraria ni añadir observaciones reales. Para Simpson,
subdividimos cada intervalo original en 16 partes iguales (número par).
Los quiebres entre rectas coinciden con límites de los paneles de Simpson.

Simpson compuesto: h/3 [y₀+y_n+4Σy_impares+2Σy_pares_interiores].
Se requieren intervalos pares y uniformes, condiciones verificadas por código.

Comprobación exacta por tramo: sea u=m−m_i, h=m_(i+1)−m_i, D=d_i+s_i u,
β=b ln(10), λ_i=λ(m_i). El integrando es (d_i+s_i u)βλ_i e^(−βu).
Integrando la constante por sustitución y u por partes:

PAE_i/V = λ_i{d_i(1−e^(−βh)) + s_i[(1−e^(−βh))/β−h e^(−βh)]}.

Se suman los tramos y se comparan con Simpson y trapecio. El Simpson de los 13 puntos
originales también se reporta: difiere aproximadamente un 3 % de la integral del modelo
lineal por tramos. El refinamiento aproxima ese modelo, no elimina la incertidumbre del daño.

## 4. Valor presente neto

Sea ΔPAE=PAE_actual−PAE_refuerzo. Se supone ahorro constante por año.
VPN=−C+∫₀ᴴΔPAE·e^(−rt)dt.
Por sustitución u=−rt, la antiderivada es −ΔPAE·e^(−rt)/r.
Así VPN=−C+ΔPAE(1−e^(−rH))/r. Si r=0: VPN=−C+ΔPAE·H.
Se convierte el 6,7 % del Excel a r=0,067. C y V están en colones completos.

Se compara con integrar el flujo mediante Simpson propio. El escenario sin refuerzo
tiene ahorro cero, costo cero y VPN cero. Si las dos inversiones tienen VPN negativo,
el criterio económico favorece no invertir. Eso no certifica seguridad estructural.
La mayor reducción de daño no necesariamente produce el mejor VPN: también importa el costo.

Sensibilidad: cambiar solo b±0,1 y solo r±2 puntos porcentuales, después combinar ambos.
El rango de ±2 pp es supuesto de exploración, no intervalo de confianza estadístico.
Como complemento, un retraso L=meses/12 cambia el factor a
(e^(−rL)−e^(−rH))/r para H≥L. Se conserva el modelo t=0 del enunciado como principal.

## 5. Qué se considera verificado

Error relativo porcentual =100|aproximación−referencia|/|referencia|.
Si la referencia es cero y el valor no lo es, se reporta infinito, nunca cero inventado.
La prueba del seno compara la norma máxima del error con el máximo de la curva exacta,
para evitar divisiones en puntos donde la solución se anula.

En datos reales simulados no conocemos una trayectoria exacta: comparar trapecio y Simpson
es una discrepancia numérica, no una medición del error físico. La integral total de aceleración
es pequeña por cancelación. Una diferencia absoluta pequeña puede ser grande en porcentaje.
Las profundidades faltantes permanecen vacías. Los valores señalados por IQR se conservan
porque una cola de magnitudes grandes es parte del fenómeno que queremos representar.
