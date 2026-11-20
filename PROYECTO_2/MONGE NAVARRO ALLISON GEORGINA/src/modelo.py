"""Modelo matemático del paso de aves rapaces sobre Kèköldi.

Idea general, en palabras sencillas
-----------------------------------
Los voluntarios cuentan aves por hora. Ese conteo es una TASA:
"cuántas aves pasan por hora" (unidades: aves/h).

* Si sumamos (integramos) la tasa a lo largo de un día, obtenemos el
  total de aves de ese día (aves).
* Si integramos los totales diarios a lo largo de la temporada,
  obtenemos el total de la temporada (aves).
* Con la integral acumulada sabemos qué fracción del paso ya ocurrió
  en cada fecha, y de ahí salen las fechas del 5, 50 y 95 %.
* Con una "integral móvil" G(a) buscamos la campaña de L días que
  registra más aves.

Todas las integrales se programan aquí desde cero (trapecio y Simpson).
La biblioteca scipy solo se usa en las pruebas, para comparar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

Arreglo = NDArray[np.float64]


# ----------------------------------------------------------------------
# Funciones de apoyo
# ----------------------------------------------------------------------
def _como_arreglo(valores: ArrayLike) -> Arreglo:
    """Convierte una lista (o columna de pandas) en un arreglo de números."""
    return np.asarray(valores, dtype=float)


def _eje_por_defecto(y: Arreglo, x: ArrayLike | None) -> Arreglo:
    """Si no se da el eje x, usa 0, 1, 2, ... (por ejemplo, días)."""
    if x is None:
        return np.arange(y.size, dtype=float)
    return _como_arreglo(x)


def _validar_xy(x: Arreglo, y: Arreglo) -> None:
    """Revisa que x e y sirvan para integrar.

    Reglas: mismo tamaño, al menos dos puntos, x siempre creciente
    y sin valores vacíos (NaN). Si algo falla, lanza un error claro.
    """
    if x.shape != y.shape:
        raise ValueError(f"x tiene {x.size} valores y y tiene {y.size}; deben ser iguales.")
    if x.size < 2:
        raise ValueError("Se necesitan al menos 2 puntos para integrar.")
    if np.any(np.diff(x) <= 0):
        raise ValueError("Los valores de x deben ir siempre en aumento.")
    if np.isnan(x).any() or np.isnan(y).any():
        raise ValueError("Hay valores vacíos (NaN). Limpie los datos antes de integrar.")


def error_relativo(aproximado: float, referencia: float) -> float:
    """Error relativo entre dos resultados.

    Entradas: dos números con las mismas unidades.
    Salida: |aproximado - referencia| / |referencia| (sin unidades).
    Si la referencia es 0, devuelve la diferencia absoluta.
    """
    if referencia == 0:
        return abs(aproximado - referencia)
    return abs(aproximado - referencia) / abs(referencia)


# ----------------------------------------------------------------------
# Reglas de integración programadas desde cero
# ----------------------------------------------------------------------
def trapecio(y: ArrayLike, x: ArrayLike | None = None) -> float:
    """Regla del trapecio: área bajo los puntos (x, y).

    Idea: entre cada par de puntos se dibuja una recta y se suma el
    área de cada trapecio: ancho * (altura izquierda + altura derecha) / 2.

    Entradas:
        y: valores de la función (por ejemplo, aves/día).
        x: posiciones (por ejemplo, días). Si no se da, se usa 0, 1, 2, ...
    Salida:
        El área, en unidades de y por unidades de x (por ejemplo, aves).
    """
    y_arr = _como_arreglo(y)
    x_arr = _eje_por_defecto(y_arr, x)
    _validar_xy(x_arr, y_arr)
    anchos = np.diff(x_arr)
    alturas_promedio = (y_arr[:-1] + y_arr[1:]) / 2
    return float(np.sum(anchos * alturas_promedio))


def simpson(y: ArrayLike, x: ArrayLike | None = None) -> float:
    """Regla de Simpson 1/3: área usando parábolas en vez de rectas.

    Necesita puntos igualmente espaciados. Simpson trabaja de dos en dos
    intervalos; si la cantidad de intervalos es impar, el último
    intervalo se calcula con un trapecio (se avisa en la documentación).

    Entradas y salida: igual que en `trapecio`.
    """
    y_arr = _como_arreglo(y)
    x_arr = _eje_por_defecto(y_arr, x)
    _validar_xy(x_arr, y_arr)
    pasos = np.diff(x_arr)
    if not np.allclose(pasos, pasos[0]):
        raise ValueError("Simpson necesita puntos igualmente espaciados.")
    h = pasos[0]
    intervalos = y_arr.size - 1

    # Si hay un número impar de intervalos, separamos el último.
    resto = 0.0
    if intervalos % 2 == 1:
        resto = h * (y_arr[-2] + y_arr[-1]) / 2
        y_arr = y_arr[:-1]
    if y_arr.size < 3:
        return float(resto)

    # Fórmula: h/3 * [y0 + 4*(impares) + 2*(pares internos) + yn]
    impares = y_arr[1:-1:2].sum()
    pares = y_arr[2:-1:2].sum()
    area = h / 3 * (y_arr[0] + 4 * impares + 2 * pares + y_arr[-1])
    return float(area + resto)


def integral_acumulada(y: ArrayLike, x: ArrayLike | None = None) -> Arreglo:
    """Integral acumulada C(x) = área desde el primer punto hasta x.

    Usa trapecios uno por uno y los va sumando.
    Salida: arreglo del mismo tamaño que y; empieza en 0 y el último
    valor es igual a `trapecio(y, x)`. Unidades: las de y por las de x.
    """
    y_arr = _como_arreglo(y)
    x_arr = _eje_por_defecto(y_arr, x)
    _validar_xy(x_arr, y_arr)
    areas = np.diff(x_arr) * (y_arr[:-1] + y_arr[1:]) / 2
    return np.concatenate(([0.0], np.cumsum(areas)))


# ----------------------------------------------------------------------
# Paso 2: total diario (bloques horarios + colas triangulares)
# ----------------------------------------------------------------------
def colas_triangulares(
    conteos: ArrayLike, hi: float, hf: float, inicio_obs: float = 7.0, duracion_bloque: float = 1.0
) -> tuple[float, float]:
    """Aves estimadas en las horas NO observadas (antes y después del conteo).

    Supuesto: antes de que empiece el conteo, la tasa sube en línea recta
    desde 0 (a la hora hi) hasta la tasa de la primera hora contada.
    Después del conteo baja en línea recta hasta 0 (a la hora hf).
    El área de cada triángulo es base * altura / 2.

    Entradas:
        conteos: aves contadas en cada bloque horario (aves), en orden.
        hi, hf: hora de inicio y fin del vuelo migratorio (h, ej. 5.5).
        inicio_obs: hora en que empieza el conteo (h). Por defecto 7:00.
        duracion_bloque: duración de cada bloque (h). Por defecto 1 h.
    Salida:
        (aves antes del conteo, aves después del conteo), en aves.
    """
    c = _como_arreglo(conteos)
    fin_obs = inicio_obs + c.size * duracion_bloque
    if hi > inicio_obs or hf < fin_obs:
        raise ValueError("hi debe ser <= inicio del conteo y hf >= fin del conteo.")
    tasa_primera = c[0] / duracion_bloque  # aves/h
    tasa_ultima = c[-1] / duracion_bloque  # aves/h
    antes = 0.5 * (inicio_obs - hi) * tasa_primera
    despues = 0.5 * (hf - fin_obs) * tasa_ultima
    return float(antes), float(despues)


def total_diario(
    conteos: ArrayLike, hi: float, hf: float, inicio_obs: float = 7.0, duracion_bloque: float = 1.0
) -> float:
    """Total de aves de un día: N_d = integral de r_d(x) desde hi hasta hf.

    Método (regla de bloques): durante cada hora contada la tasa se toma
    constante, así que el área de ese bloque es exactamente el conteo.
    A eso se le suman los dos triángulos de las horas no observadas.

    Entradas: ver `colas_triangulares`. Los conteos no pueden tener NaN.
    Salida: total del día (aves).
    """
    c = _como_arreglo(conteos)
    if c.size == 0 or np.isnan(c).any():
        raise ValueError("Los conteos están vacíos o tienen NaN; límpielos primero.")
    antes, despues = colas_triangulares(c, hi, hf, inicio_obs, duracion_bloque)
    return float(c.sum() + antes + despues)


def total_diario_trapecio(
    conteos: ArrayLike, hi: float, hf: float, inicio_obs: float = 7.0, duracion_bloque: float = 1.0
) -> float:
    """Segunda forma de calcular el total diario, para comparar.

    Cada conteo se ubica a la mitad de su hora (ej. 7:30) como tasa
    (aves/h), se agregan los puntos (hi, 0) y (hf, 0), y se aplica la
    regla del trapecio a todo el día. Salida: aves.
    """
    c = _como_arreglo(conteos)
    if c.size == 0 or np.isnan(c).any():
        raise ValueError("Los conteos están vacíos o tienen NaN; límpielos primero.")
    centros = inicio_obs + duracion_bloque * (np.arange(c.size) + 0.5)
    x = np.concatenate(([hi], centros, [hf]))
    y = np.concatenate(([0.0], c / duracion_bloque, [0.0]))
    return trapecio(y, x)


# ----------------------------------------------------------------------
# Paso 3: curva acumulada, percentiles, fecha media y dispersión
# ----------------------------------------------------------------------
def acumulada(n: ArrayLike, t: ArrayLike | None = None) -> Arreglo:
    """Fracción acumulada del paso F(t) = (1/N) * integral de n desde t0 hasta t.

    Entradas: n = aves por día; t = días (por defecto 0, 1, 2, ...).
    Salida: arreglo que empieza en 0 y termina en 1 (sin unidades).
    Ejemplo: F = 0,30 significa que ya pasó el 30 % de las aves.
    """
    c = integral_acumulada(n, t)
    if c[-1] <= 0:
        raise ValueError("El total es cero: no se puede calcular la fracción.")
    return c / c[-1]


def fecha_percentil(F: ArrayLike, t: ArrayLike, p: float) -> float:
    """Fecha en la que ya pasó la fracción p de las aves.

    Busca dónde la curva F cruza el valor p e interpola en línea recta
    entre los dos días vecinos.

    Entradas: F (fracción acumulada), t (días), p entre 0 y 1
    (por ejemplo 0.05, 0.50, 0.95).
    Salida: la fecha (días desde el inicio de la temporada).
    """
    F_arr, t_arr = _como_arreglo(F), _como_arreglo(t)
    if not 0 <= p <= 1:
        raise ValueError("p debe estar entre 0 y 1 (ej. 0.5 para el 50 %).")
    i = int(np.searchsorted(F_arr, p, side="left"))
    if i == 0:
        return float(t_arr[0])
    if i >= F_arr.size:
        return float(t_arr[-1])
    # Interpolación lineal entre (F[i-1], t[i-1]) y (F[i], t[i]).
    proporcion = (p - F_arr[i - 1]) / (F_arr[i] - F_arr[i - 1])
    return float(t_arr[i - 1] + proporcion * (t_arr[i] - t_arr[i - 1]))


def fecha_media(n: ArrayLike, t: ArrayLike | None = None) -> float:
    """Fecha media del paso: t_media = (1/N) * integral de t * n(t) dt.

    Es un promedio de fechas "pesado" por la cantidad de aves de cada día.
    Salida: días desde el inicio de la temporada.
    """
    n_arr = _como_arreglo(n)
    t_arr = _eje_por_defecto(n_arr, t)
    return trapecio(t_arr * n_arr, t_arr) / trapecio(n_arr, t_arr)


def dispersion(n: ArrayLike, t: ArrayLike | None = None) -> float:
    """Qué tan "ancho" es el paso (desviación estándar, en días).

    Fórmula: raíz de (1/N) * integral de (t - t_media)^2 * n(t) dt.
    Un valor pequeño indica que las aves pasan concentradas en pocos días.
    """
    n_arr = _como_arreglo(n)
    t_arr = _eje_por_defecto(n_arr, t)
    t_m = fecha_media(n_arr, t_arr)
    varianza = trapecio((t_arr - t_m) ** 2 * n_arr, t_arr) / trapecio(n_arr, t_arr)
    return float(np.sqrt(varianza))


def media_movil(n: ArrayLike, ancho: int = 5) -> Arreglo:
    """Suaviza una serie promediando cada día con sus vecinos.

    Entradas: n (aves/día) y ancho = cuántos días se promedian (impar).
    En los bordes se promedian solo los días que existen.
    Salida: serie suavizada, mismas unidades que n.
    """
    if ancho < 1 or ancho % 2 == 0:
        raise ValueError("El ancho debe ser un número impar positivo (ej. 3, 5, 7).")
    n_arr = _como_arreglo(n)
    ventana = np.ones(ancho)
    sumas = np.convolve(n_arr, ventana, mode="same")
    cuantos = np.convolve(np.ones_like(n_arr), ventana, mode="same")
    return sumas / cuantos


# ----------------------------------------------------------------------
# Paso 4: ventana óptima de la campaña  G(a) = integral de a hasta a+L
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoVentana:
    """Resultado de buscar la mejor campaña de L días.

    inicio, fin: días de inicio y fin de la mejor campaña.
    aves: aves que pasan dentro de la campaña (aves).
    fraccion: aves de la campaña / total de la temporada (0 a 1).
    inicios, G: todas las fechas de inicio probadas y su G(a), para graficar.
    """

    inicio: float
    fin: float
    aves: float
    fraccion: float
    inicios: Arreglo
    G: Arreglo


def aves_en_ventana(n: ArrayLike, inicio: float, L: float, t: ArrayLike | None = None) -> float:
    """G(a): aves que pasan entre el día `inicio` y el día `inicio + L`.

    Usa el teorema fundamental del cálculo:
    G(a) = C(a + L) - C(a), donde C es la integral acumulada.
    Sirve también para evaluar la campaña tradicional. Salida: aves.
    """
    n_arr = _como_arreglo(n)
    t_arr = _eje_por_defecto(n_arr, t)
    if inicio < t_arr[0] or inicio + L > t_arr[-1]:
        raise ValueError("La campaña se sale de la temporada observada.")
    c = integral_acumulada(n_arr, t_arr)
    return float(np.interp(inicio + L, t_arr, c) - np.interp(inicio, t_arr, c))


def mejor_ventana(n: ArrayLike, L: float, t: ArrayLike | None = None) -> ResultadoVentana:
    """Busca la fecha de inicio a que hace máximo G(a) (integral móvil).

    Se prueban todas las fechas de inicio posibles. Como en el máximo
    G'(a) = n(a + L) - n(a) = 0, en la ventana óptima la cantidad de aves
    del primer y del último día debe ser parecida.

    Entradas: n (aves/día), L (duración en días), t (días, igualmente
    espaciados). L debe ser múltiplo del paso de t.
    Salida: un `ResultadoVentana`.
    """
    n_arr = _como_arreglo(n)
    t_arr = _eje_por_defecto(n_arr, t)
    paso = t_arr[1] - t_arr[0]
    k = int(round(L / paso))
    if k < 1 or k >= t_arr.size:
        raise ValueError("La duración L debe ser mayor que 0 y menor que la temporada.")
    if not np.isclose(k * paso, L):
        raise ValueError("L debe ser múltiplo del paso entre fechas.")
    c = integral_acumulada(n_arr, t_arr)
    G = c[k:] - c[:-k]  # G(a) = C(a+L) - C(a) para cada inicio posible
    inicios = t_arr[:-k]
    mejor = int(np.argmax(G))
    return ResultadoVentana(
        inicio=float(inicios[mejor]),
        fin=float(inicios[mejor] + L),
        aves=float(G[mejor]),
        fraccion=float(G[mejor] / c[-1]),
        inicios=inicios,
        G=G,
    )


# ----------------------------------------------------------------------
# Paso 5: mejor turno de horas consecutivas
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoTurno:
    """Resultado de buscar el mejor turno de horas seguidas.

    hora_inicio, hora_fin: horario del turno (h, ej. 9.0 a 12.0).
    aves: aves promedio por día registradas en el turno (aves).
    fraccion: aves del turno / aves del día completo (0 a 1).
    inicios, aves_por_inicio: todas las opciones probadas, para graficar.
    """

    hora_inicio: float
    hora_fin: float
    aves: float
    fraccion: float
    inicios: Arreglo
    aves_por_inicio: Arreglo


def mejor_turno(
    perfil: ArrayLike,
    horas: int,
    inicio_obs: float = 7.0,
    total_dia: float | None = None,
) -> ResultadoTurno:
    """Elige el turno de `horas` horas seguidas que registra más aves.

    Entradas:
        perfil: aves promedio en cada bloque horario de la temporada
            (aves), empezando a la hora `inicio_obs`.
        horas: duración del turno (número entero de horas).
        inicio_obs: hora del primer bloque (h).
        total_dia: aves de un día completo (con colas) para calcular la
            fracción. Si no se da, se usa la suma del perfil.
    Salida: un `ResultadoTurno`.
    """
    p = _como_arreglo(perfil)
    if not 1 <= horas <= p.size:
        raise ValueError(f"El turno debe durar entre 1 y {p.size} horas.")
    # Suma móvil con sumas acumuladas: S[j+h] - S[j] = aves de j a j+h.
    s = np.concatenate(([0.0], np.cumsum(p)))
    aves_por_inicio = s[horas:] - s[:-horas]
    inicios = inicio_obs + np.arange(aves_por_inicio.size, dtype=float)
    mejor = int(np.argmax(aves_por_inicio))
    denominador = total_dia if total_dia is not None else float(p.sum())
    return ResultadoTurno(
        hora_inicio=float(inicios[mejor]),
        hora_fin=float(inicios[mejor] + horas),
        aves=float(aves_por_inicio[mejor]),
        fraccion=float(aves_por_inicio[mejor] / denominador),
        inicios=inicios,
        aves_por_inicio=aves_por_inicio,
    )


# ----------------------------------------------------------------------
# Clase propia: reúne todo lo de una especie
# ----------------------------------------------------------------------
@dataclass
class CurvaDePaso:
    """Paso migratorio de una especie durante la temporada.

    Atributos:
        nombre: nombre de la especie.
        t: días desde el inicio de la temporada (días).
        n: aves por día (aves/día), ya limpias y con las colas incluidas.
    """

    nombre: str
    t: Arreglo
    n: Arreglo

    def __post_init__(self) -> None:
        self.t = _como_arreglo(self.t)
        self.n = _como_arreglo(self.n)
        _validar_xy(self.t, self.n)
        if np.any(self.n < 0):
            raise ValueError("No puede haber cantidades negativas de aves.")

    @property
    def total(self) -> float:
        """N: aves de la temporada (integral con trapecio)."""
        return trapecio(self.n, self.t)

    @property
    def total_simpson(self) -> float:
        """N calculado con Simpson, para comparar con el trapecio."""
        return simpson(self.n, self.t)

    @property
    def F(self) -> Arreglo:
        """Fracción acumulada F(t), de 0 a 1."""
        return acumulada(self.n, self.t)

    def percentil(self, p: float) -> float:
        """Fecha (días) en que ya pasó la fracción p de las aves."""
        return fecha_percentil(self.F, self.t, p)

    def fecha_media(self) -> float:
        """Fecha media del paso (días)."""
        return fecha_media(self.n, self.t)

    def dispersion(self) -> float:
        """Desviación estándar del paso (días)."""
        return dispersion(self.n, self.t)

    def mejor_ventana(self, L: float) -> ResultadoVentana:
        """Mejor campaña de L días para esta especie."""
        return mejor_ventana(self.n, L, self.t)

    def resumen(self) -> dict[str, float | str]:
        """Indicadores principales en un diccionario (para tablas)."""
        return {
            "especie": self.nombre,
            "total_aves": self.total,
            "total_aves_simpson": self.total_simpson,
            "error_relativo": error_relativo(self.total_simpson, self.total),
            "fecha_5": self.percentil(0.05),
            "fecha_50": self.percentil(0.50),
            "fecha_95": self.percentil(0.95),
            "fecha_media": self.fecha_media(),
            "dispersion_dias": self.dispersion(),
        }


# ----------------------------------------------------------------------
# Funciones que trabajan con la tabla limpia del Excel
# ----------------------------------------------------------------------
def totales_diarios(limpio: pd.DataFrame, hi: float, hf: float) -> pd.DataFrame:
    """Total de aves de cada día y especie: N_d = integral de r_d(x) de hi a hf.

    Entrada: tabla limpia (columnas especie, dia, fecha, hora, aves_limpias)
        y las horas de inicio y fin del vuelo (h).
    Salida: tabla con una fila por día (dia, fecha), una columna por especie
        y la columna "Total" (aves/día). Incluye las colas triangulares.
    """
    filas = []
    for (especie, dia), grupo in limpio.groupby(["especie", "dia"]):
        grupo = grupo.sort_values("hora")
        total = total_diario(grupo["aves_limpias"], hi, hf, inicio_obs=float(grupo["hora"].min()))
        filas.append({"dia": dia, "fecha": grupo["fecha"].iloc[0], "especie": especie, "n": total})
    largo = pd.DataFrame(filas)
    ancho = largo.pivot_table(index=["dia", "fecha"], columns="especie", values="n").reset_index()
    ancho.columns.name = None
    especies = [c for c in ancho.columns if c not in ("dia", "fecha")]
    ancho["Total"] = ancho[especies].sum(axis=1)
    return ancho


def perfil_horario(limpio: pd.DataFrame, dias: tuple[float, float] | None = None) -> pd.DataFrame:
    """Aves promedio por día en cada bloque horario (perfil de la temporada).

    Entrada: tabla limpia y, opcionalmente, un rango de días (inicio, fin)
        para usar solo los días de la campaña.
    Salida: tabla con la hora (h), una columna por especie y "Total" (aves).
    """
    datos = limpio
    if dias is not None:
        datos = limpio[(limpio["dia"] >= dias[0]) & (limpio["dia"] < dias[1])]
    perfil = datos.pivot_table(
        index="hora", columns="especie", values="aves_limpias", aggfunc="mean"
    )
    perfil.columns.name = None
    perfil["Total"] = perfil.sum(axis=1)
    return perfil.reset_index()


def verificar_total(n: ArrayLike, t: ArrayLike | None = None) -> dict[str, float]:
    """Verifica el total de la temporada calculándolo de tres formas.

    suma: suma simple de los totales diarios (acumulado observado).
    trapecio y simpson: integrales de n(t). Se reportan los errores
    relativos de cada integral respecto de la suma. Unidades: aves.
    """
    n_arr = _como_arreglo(n)
    suma = float(n_arr.sum())
    trap = trapecio(n_arr, t)
    simp = simpson(n_arr, t)
    return {
        "suma": suma,
        "trapecio": trap,
        "simpson": simp,
        "error_trapecio": error_relativo(trap, suma),
        "error_simpson": error_relativo(simp, suma),
    }
