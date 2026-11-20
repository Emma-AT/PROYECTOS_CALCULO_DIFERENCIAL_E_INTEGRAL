"""Modelo de un compartimento con absorción, integrales y verificación.

Modelo (dosis D en mg, t en h, C en mg/L):

    C(t) = D ka / (V (ka - k)) * (exp(-k t) - exp(-ka t)),   t >= 0

Integral exacta (se obtiene integrando cada exponencial):

    ∫_0^t C(s) ds = D ka / (V (ka - k)) * [(1 - e^{-k t})/k - (1 - e^{-ka t})/ka]

y en el límite t -> ∞ (integral impropia convergente porque k, ka > 0):

    AUC = D / (V k)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from src.config import HORIZONTE_VALIDACION_H, T_TERMINAL_H

# ---------------------------------------------------------------------------
# Métodos numéricos propios
# ---------------------------------------------------------------------------
# Implementados a mano (no se usa scipy) para mostrar el método del curso:
# trapecio, trapecio acumulado, Simpson, bisección y mínimos cuadrados.


def trapecio(x: np.ndarray, y: np.ndarray) -> float:
    """Regla del trapecio compuesta para datos con espaciado arbitrario.

    Entradas: x (p. ej. h) creciente, y (p. ej. mg/L) del mismo tamaño.
    Salidas: aproximación de ∫ y dx en unidades de x·y (p. ej. mg·h/L).
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.sum(np.diff(x) * (y[1:] + y[:-1]) / 2))


def trapecio_acumulado(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Integral acumulada F(x_i) = ∫_{x_0}^{x_i} y dx con trapecios.

    Entradas: x creciente, y.  Salidas: arreglo del tamaño de x, F(x_0) = 0.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    areas = np.diff(x) * (y[1:] + y[:-1]) / 2
    return np.concatenate([[0.0], np.cumsum(areas)])


def simpson(x: np.ndarray, y: np.ndarray) -> float:
    """Regla de Simpson compuesta para espaciado irregular.

    Integra una parábola por cada par de subintervalos. Si el número de
    subintervalos es impar, el último se integra con la parábola que pasa
    por los tres últimos puntos (corrección de Cartwright).
    Entradas: x creciente (al menos 3 puntos), y.
    Salidas: aproximación de ∫ y dx en unidades de x·y.
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.size < 3:
        return trapecio(x, y)
    # 1) Parábola por cada par de subintervalos (h0, h1), con pesos para espaciado irregular
    h = np.diff(x)
    n_pares = h.size // 2
    h0, h1 = h[0 : 2 * n_pares : 2], h[1 : 2 * n_pares : 2]
    f0, f1, f2 = y[0 : 2 * n_pares : 2], y[1 : 2 * n_pares + 1 : 2], y[2 : 2 * n_pares + 1 : 2]
    suma = (
        (h0 + h1) / 6 * ((2 - h1 / h0) * f0 + (h0 + h1) ** 2 / (h0 * h1) * f1 + (2 - h0 / h1) * f2)
    )
    total = float(np.sum(suma))
    # 2) Si sobra un subintervalo, se integra con la parábola de los tres últimos puntos
    if h.size % 2 == 1:
        a, b = h[-2], h[-1]
        alfa = (2 * b**2 + 3 * a * b) / (6 * (a + b))
        beta = (b**2 + 3 * a * b) / (6 * a)
        eta = b**3 / (6 * a * (a + b))
        total += alfa * y[-1] + beta * y[-2] - eta * y[-3]
    return total


def biseccion(
    f: Callable[[float], float], a: float, b: float, tol: float = 1e-9, max_iter: int = 200
) -> float:
    """Raíz de f en [a, b] por bisección (requiere cambio de signo).

    Entradas: función continua f, extremos a < b, tolerancia en x.
    Salidas: x con |f(x)| ≈ 0 y error en x menor que ``tol``.
    """
    fa, fb = f(a), f(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        raise ValueError("La función no cambia de signo en el intervalo dado")
    # Teorema del valor intermedio: la raíz queda en la mitad donde f cambia de signo
    for _ in range(max_iter):
        m = (a + b) / 2
        fm = f(m)
        if fm == 0 or (b - a) / 2 < tol:
            return m
        if fa * fm < 0:
            b = m
        else:
            a, fa = m, fm
    return (a + b) / 2


def pendiente_minimos_cuadrados(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Recta de mínimos cuadrados y = m x + b.

    Entradas: x, y.  Salidas: (m, b, R²).
    """
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.sum((x - x.mean()) * (y - y.mean())) / np.sum((x - x.mean()) ** 2)
    b = y.mean() - m * x.mean()
    residuo = y - (m * x + b)
    r2 = 1 - np.sum(residuo**2) / np.sum((y - y.mean()) ** 2)
    return float(m), float(b), float(r2)


# ---------------------------------------------------------------------------
# Modelo farmacocinético
# ---------------------------------------------------------------------------
# La clase ModeloUnCompartimento es la fórmula C(t) con sus integrales exactas;
# analizar_voluntario estima k, AUC, CL y V a partir de los datos de cada persona.


@dataclass(frozen=True)
class ModeloUnCompartimento:
    """Modelo de un compartimento con absorción de primer orden.

    Atributos: k (1/h) eliminación, ka (1/h) absorción, v_l (L) volumen.
    """

    k: float
    ka: float
    v_l: float

    @property
    def vida_media(self) -> float:
        """Vida media de eliminación t½ = ln 2 / k (h)."""
        return float(np.log(2) / self.k)

    @property
    def depuracion(self) -> float:
        """Depuración CL = V k (L/h)."""
        return self.v_l * self.k

    def concentracion(self, t: np.ndarray | float, dosis: float) -> np.ndarray:
        """C(t) en mg/L para una dosis (mg) tomada en t = 0; C = 0 si t < 0.

        Usa el límite D k t e^{-k t} / V cuando ka = k.
        """
        t = np.asarray(t, float)
        tp = np.clip(t, 0.0, None)
        if np.isclose(self.ka, self.k):
            c = dosis * self.k * tp * np.exp(-self.k * tp) / self.v_l
        else:
            factor = dosis * self.ka / (self.v_l * (self.ka - self.k))
            c = factor * (np.exp(-self.k * tp) - np.exp(-self.ka * tp))
        return np.where(t >= 0, c, 0.0)

    def auc_hasta(self, t: np.ndarray | float, dosis: float) -> np.ndarray:
        """Integral exacta ∫_0^t C(s) ds en mg·h/L (antiderivada analítica)."""
        tp = np.clip(np.asarray(t, float), 0.0, None)
        factor = dosis * self.ka / (self.v_l * (self.ka - self.k))
        return factor * (
            (1 - np.exp(-self.k * tp)) / self.k - (1 - np.exp(-self.ka * tp)) / self.ka
        )

    def auc_infinito(self, dosis: float) -> float:
        """Integral impropia ∫_0^∞ C dt = D / (V k) en mg·h/L."""
        return dosis / (self.v_l * self.k)

    def tiempo_maximo(self) -> float:
        """Tiempo del pico t_max = ln(ka/k)/(ka − k) en h (C'(t) = 0)."""
        return float(np.log(self.ka / self.k) / (self.ka - self.k))


@dataclass(frozen=True)
class ResultadoVoluntario:
    """Indicadores farmacocinéticos de un voluntario (unidades en el nombre)."""

    k_1_h: float
    vida_media_h: float
    r2_terminal: float
    auc_0_24_trapecio: float
    auc_0_24_simpson: float
    cola_mg_h_l: float
    auc_total: float
    pct_cola: float
    cl_l_h: float
    v_l: float
    error_rel_trap_simpson: float


def analizar_voluntario(
    t: np.ndarray,
    c: np.ndarray,
    dosis: float,
    t_terminal: float = T_TERMINAL_H,
    usar_en_k: np.ndarray | None = None,
) -> ResultadoVoluntario:
    """k, vida media, AUC (trapecio + cola impropia), CL y V de un voluntario.

    Entradas: t (h) y c (mg/L) sin faltantes; dosis (mg); inicio de la fase
    terminal (h); máscara opcional de puntos válidos para estimar k
    (para excluir valores imputados).
    Salidas: ``ResultadoVoluntario``. El AUC incluye el punto C(0) = 0 y la
    cola ∫_{t_n}^∞ C dt ≈ C(t_n)/k.
    """
    t, c = np.asarray(t, float), np.asarray(c, float)
    # 1) k = −pendiente de ln C en la fase terminal (solo puntos observados)
    mascara = (t >= t_terminal) & (c > 0)
    if usar_en_k is not None:
        mascara &= np.asarray(usar_en_k, bool)
    pendiente, _, r2 = pendiente_minimos_cuadrados(t[mascara], np.log(c[mascara]))
    k = -pendiente
    # 2) Área de 0 a 24 h con trapecio (y Simpson para comparar), agregando C(0) = 0
    t0, c0 = np.concatenate([[0.0], t]), np.concatenate([[0.0], c])
    auc_trap, auc_simp = trapecio(t0, c0), simpson(t0, c0)
    # 3) Cola impropia ∫_24^∞ C(24) e^{−k(t−24)} dt = C(24)/k
    cola = c[-1] / k
    auc_total = auc_trap + cola
    # 4) Depuración CL = D/AUC y volumen V = CL/k
    cl = dosis / auc_total
    return ResultadoVoluntario(
        k_1_h=k,
        vida_media_h=float(np.log(2) / k),
        r2_terminal=r2,
        auc_0_24_trapecio=auc_trap,
        auc_0_24_simpson=auc_simp,
        cola_mg_h_l=cola,
        auc_total=auc_total,
        pct_cola=100 * cola / auc_total,
        cl_l_h=cl,
        v_l=cl / k,
        error_rel_trap_simpson=abs(auc_trap - auc_simp) / abs(auc_simp),
    )


def analizar_todos(conc_limpio: pd.DataFrame, dosis: float) -> pd.DataFrame:
    """Aplica ``analizar_voluntario`` a cada voluntario.

    Entradas: concentraciones limpias (con columna ``estado``); dosis (mg).
    Salidas: DataFrame indexado por voluntario con los indicadores.
    """
    filas = {}
    for vol, g in conc_limpio.sort_values("tiempo_h").groupby("voluntario"):
        res = analizar_voluntario(
            g["tiempo_h"].to_numpy(),
            g["concentracion_mg_L"].to_numpy(),
            dosis,
            usar_en_k=(g["estado"] == "observado").to_numpy(),
        )
        filas[vol] = asdict(res)
    return pd.DataFrame.from_dict(filas, orient="index").rename_axis("voluntario")


def modelo_de(fila: pd.Series, ka: float) -> ModeloUnCompartimento:
    """Construye el modelo de un voluntario a partir de su fila de resultados."""
    return ModeloUnCompartimento(k=float(fila["k_1_h"]), ka=ka, v_l=float(fila["v_l"]))


# ---------------------------------------------------------------------------
# Validación y verificación
# ---------------------------------------------------------------------------
# Comprueban que las integrales numéricas coinciden con las fórmulas exactas
# (validación) y que el modelo reproduce lo medido (verificación).


def integral_exponencial_truncada(k: float, t_max: float, n: int = 4000) -> float:
    """∫_0^{t_max} e^{-k t} dt con Simpson propio (debe tender a 1/k).

    Entradas: k (1/h), t_max (h), n subintervalos.  Salidas: valor en h.
    """
    t = np.linspace(0.0, t_max, n + 1)
    return simpson(t, np.exp(-k * t))


def validar_auc_modelo(
    resultados: pd.DataFrame, ka: float, dosis: float, t_max: float = HORIZONTE_VALIDACION_H
) -> pd.DataFrame:
    """Integra C(t) de cada voluntario hasta ``t_max`` y lo compara con D/(V k).

    Entradas: resultados por voluntario, ka (1/h), dosis (mg), t_max (h).
    Salidas: DataFrame con auc_numerica, auc_formula (mg·h/L) y error_rel.
    """
    t = np.linspace(0.0, t_max, 20001)
    filas = {}
    for vol, fila in resultados.iterrows():
        modelo = modelo_de(fila, ka)
        numerica = simpson(t, modelo.concentracion(t, dosis))
        formula = modelo.auc_infinito(dosis)
        filas[vol] = {
            "auc_numerica": numerica,
            "auc_formula": formula,
            "error_rel": abs(numerica - formula) / formula,
        }
    return pd.DataFrame.from_dict(filas, orient="index").rename_axis("voluntario")


def verificar_contra_datos(
    conc_limpio: pd.DataFrame, resultados: pd.DataFrame, ka: float, dosis: float
) -> pd.DataFrame:
    """Compara el modelo con lo observado en cada voluntario.

    Calcula el acumulado observado ∫_0^24 C dt (trapecio) contra la integral
    exacta del modelo en [0, 24] y el error medio de las concentraciones.
    Entradas: concentraciones limpias, resultados, ka (1/h), dosis (mg).
    Salidas: DataFrame con auc_obs_0_24, auc_modelo_0_24, error_rel_acumulado,
    rmse_mg_L y r2.
    """
    filas = {}
    for vol, g in conc_limpio.sort_values("tiempo_h").groupby("voluntario"):
        modelo = modelo_de(resultados.loc[vol], ka)
        t = g["tiempo_h"].to_numpy()
        c = g["concentracion_mg_L"].to_numpy()
        pred = modelo.concentracion(t, dosis)
        obs = resultados.loc[vol, "auc_0_24_trapecio"]
        simp = resultados.loc[vol, "auc_0_24_simpson"]
        exacto = float(modelo.auc_hasta(t.max(), dosis))
        filas[vol] = {
            "auc_obs_0_24": obs,
            "auc_modelo_0_24": exacto,
            "error_rel_acumulado": abs(obs - exacto) / obs,
            "error_rel_simpson_modelo": abs(simp - exacto) / exacto,
            "rmse_mg_L": float(np.sqrt(np.mean((c - pred) ** 2))),
            "r2": float(1 - np.sum((c - pred) ** 2) / np.sum((c - c.mean()) ** 2)),
        }
    return pd.DataFrame.from_dict(filas, orient="index").rename_axis("voluntario")


# ---------------------------------------------------------------------------
# Atención: tiempo de reacción contra concentración
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelacionAtencion:
    """Recta mejora_ms = pendiente · C (+ intercepto), ajustada por mínimos cuadrados.

    Atributos: pendiente (ms por mg/L), intercepto (ms), r2, basal_ms
    (tiempo de reacción medio sin cafeína).
    """

    pendiente: float
    intercepto: float
    r2: float
    basal_ms: float

    def mejora(self, c: np.ndarray | float) -> np.ndarray:
        """Mejora esperada del tiempo de reacción (ms) a concentración c (mg/L)."""
        return self.intercepto + self.pendiente * np.asarray(c, float)


def ajustar_atencion(atencion: pd.DataFrame) -> RelacionAtencion:
    """Ajusta la mejora del tiempo de reacción en función de la concentración.

    Entradas: tabla de ``limpieza.unir_atencion`` (mejora_ms, concentracion_mg_L).
    Salidas: ``RelacionAtencion``.
    """
    m, b, r2 = pendiente_minimos_cuadrados(
        atencion["concentracion_mg_L"].to_numpy(), atencion["mejora_ms"].to_numpy()
    )
    basal = float(atencion.loc[atencion["tiempo_h"] == 0, "tiempo_reaccion_ms"].mean())
    return RelacionAtencion(pendiente=m, intercepto=b, r2=r2, basal_ms=basal)


# ---------------------------------------------------------------------------
# Horas con efecto: integral de la función indicadora
# ---------------------------------------------------------------------------


def horas_efecto(t: np.ndarray, c: np.ndarray, umbral: float, inicio: float, fin: float) -> float:
    """H = ∫_inicio^fin 1[C(t) >= umbral] dt sobre la interpolación lineal de C.

    En cada subintervalo se calcula exactamente la fracción en que la recta
    que une (t_i, c_i) y (t_{i+1}, c_{i+1}) supera el umbral.
    Entradas: malla t (h), concentraciones c (mg/L), umbral (mg/L),
    inicio y fin de la jornada (h).
    Salidas: horas con efecto (h).
    """
    t, c = np.asarray(t, float), np.asarray(c, float)
    # 1) Recortar la curva exactamente a la jornada [inicio, fin]
    dentro = (t > inicio) & (t < fin)
    tt = np.concatenate([[inicio], t[dentro], [fin]])
    cc = np.concatenate([[np.interp(inicio, t, c)], c[dentro], [np.interp(fin, t, c)]])
    # 2) En cada tramo: todo arriba (1), todo abajo (0) o la fracción hasta el cruce
    d0, d1 = cc[:-1] - umbral, cc[1:] - umbral
    largo = np.diff(tt)
    mixto = (d0 >= 0) != (d1 >= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        fraccion = np.where(mixto, np.maximum(d0, d1) / np.abs(d0 - d1), (d0 >= 0) * 1.0)
    return float(np.sum(largo * fraccion))


def horas_efecto_filas(t: np.ndarray, c: np.ndarray, umbral: float) -> np.ndarray:
    """Versión vectorizada de ``horas_efecto`` para muchas curvas a la vez.

    Entradas: malla t (h) que ya cubre exactamente la jornada; matriz c
    (una curva por fila, mg/L); umbral (mg/L).
    Salidas: arreglo con las horas con efecto de cada fila (h).
    """
    d0, d1 = c[:, :-1] - umbral, c[:, 1:] - umbral
    mixto = (d0 >= 0) != (d1 >= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        fraccion = np.where(mixto, np.maximum(d0, d1) / np.abs(d0 - d1), (d0 >= 0) * 1.0)
    return fraccion @ np.diff(t)


def horas_efecto_biseccion(
    f: Callable[[float], float], umbral: float, inicio: float, fin: float, paso: float = 0.25
) -> float:
    """Horas con C(t) >= umbral hallando los cruces con bisección.

    Entradas: función C(t) en mg/L, umbral (mg/L), inicio y fin (h), paso
    de búsqueda de cambios de signo (h).
    Salidas: horas con efecto (h), para comparar con ``horas_efecto``.
    """
    # 1) Buscar tramos con cambio de signo de C(t) − umbral y afinar cada cruce con bisección
    nodos = np.append(np.arange(inicio, fin, paso), fin)
    g = np.array([f(x) - umbral for x in nodos])
    cortes = [inicio]
    for a, b, ga, gb in zip(nodos[:-1], nodos[1:], g[:-1], g[1:], strict=True):
        if (ga >= 0) != (gb >= 0):
            cortes.append(biseccion(lambda x: f(x) - umbral, a, b))
    cortes.append(fin)
    # 2) Sumar los tramos entre cruces en los que la curva está sobre el umbral
    total = 0.0
    for a, b in zip(cortes[:-1], cortes[1:], strict=True):
        if f((a + b) / 2) >= umbral:
            total += b - a
    return total
