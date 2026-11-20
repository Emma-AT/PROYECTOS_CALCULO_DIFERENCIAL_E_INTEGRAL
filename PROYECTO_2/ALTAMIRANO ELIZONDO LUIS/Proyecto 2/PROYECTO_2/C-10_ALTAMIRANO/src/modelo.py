"""Integrales numéricas propias, índice de procrastinación y ajuste de k.

Modelo (descuento hiperbólico), con t en horas desde la apertura y T la duración del plazo:

    f_k(t) = k / ( ln(1 + kT) * (1 + k(T - t)) )        densidad de entregas, en 1/h
    F_k(t) = 1 - ln(1 + k(T - t)) / ln(1 + kT)           acumulada (se demuestra integrando f_k)
    IP     = (1/T) * integral_0^T (1 - F(t)) dt           = promedio de t/T
    fracción de las últimas h horas = ln(1 + hk) / ln(1 + kT)
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

Vector = NDArray[np.float64]

K_MIN_TINY = 1e-12  # por debajo de esto se usa el límite k -> 0 (densidad uniforme)


# --------------------------------------------------------------------------
# Integración numérica propia
# --------------------------------------------------------------------------
def trapecio(y: ArrayLike, x: ArrayLike) -> float:
    """Regla del trapecio para puntos (x_i, y_i), con espaciado no necesariamente uniforme.

    Entradas: y, valores de la función; x, puntos en orden creciente (misma longitud).
    Salida: integral aproximada, en unidades de y multiplicadas por unidades de x.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if y.shape != x.shape or y.size < 2:
        raise ValueError("x e y deben tener la misma longitud (al menos 2 puntos).")
    return float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2))


def integral_acumulada(y: ArrayLike, x: ArrayLike) -> Vector:
    """Integral acumulada con trapecios: el último valor coincide con trapecio(y, x).

    Entradas: y, valores de la función; x, puntos en orden creciente.
    Salida: arreglo con la integral desde x[0] hasta cada x[i] (primer valor 0).
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    pasos = (x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2
    return np.concatenate(([0.0], np.cumsum(pasos)))


def simpson(f: Callable[[Vector], ArrayLike], a: float, b: float, n: int = 2000) -> float:
    """Regla de Simpson compuesta de f en [a, b] con n subintervalos (n par).

    Entradas: f, función que acepta un arreglo; a y b, límites; n, subintervalos.
    Salida: integral aproximada, en unidades de f multiplicadas por unidades de t.
    """
    if n % 2 != 0 or n < 2:
        raise ValueError("n debe ser un entero par mayor o igual que 2.")
    x = np.linspace(a, b, n + 1)
    y = np.asarray(f(x), dtype=float)
    h = (b - a) / n
    return float(h / 3 * (y[0] + y[-1] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum()))


def error_relativo(aproximado: float, exacto: float) -> float:
    """Error relativo |aproximado - exacto| / |exacto| (sin unidad; absoluto si exacto = 0)."""
    if exacto == 0:
        return abs(aproximado)
    return abs(aproximado - exacto) / abs(exacto)


# --------------------------------------------------------------------------
# Parte empírica
# --------------------------------------------------------------------------
def f_empirica(tau: ArrayLike, n: int = 1000) -> tuple[Vector, Vector]:
    """F empírica (fracción de entregas con tau <= u) en una malla de n+1 puntos de [0, 1].

    Entradas: tau, fracciones del plazo (sin unidad); n, subintervalos de la malla.
    Salida: (malla, F), ambos sin unidad.
    """
    tau = np.sort(np.asarray(tau, dtype=float))
    if tau.size == 0:
        raise ValueError("No hay entregas para construir F.")
    malla = np.linspace(0.0, 1.0, n + 1)
    F = np.searchsorted(tau, malla, side="right") / tau.size
    return malla, F


def indice_procrastinacion(tau: ArrayLike, n: int = 1000) -> float:
    """IP = integral de 1 - F en [0, 1] con trapecio propio (tau = t/T en [0, 1]).

    Entradas: tau, fracciones del plazo de las entregas a tiempo (sin unidad).
    Salida: IP, fracción entre 0 (todo al abrir) y 1 (todo al cierre).
    """
    malla, F = f_empirica(tau, n)
    return trapecio(1.0 - F, malla)


# --------------------------------------------------------------------------
# Modelo teórico
# --------------------------------------------------------------------------
def densidad_modelo(t: ArrayLike, k: float, T: float) -> Vector:
    """f_k(t). Si k es casi 0 se usa el límite 1/T (entregas uniformes).

    Entradas: t, horas desde la apertura (h); k, intensidad (1/h); T, plazo (h).
    Salida: densidad de entregas, en 1/h.
    """
    t = np.asarray(t, dtype=float)
    if k < K_MIN_TINY:
        return np.full_like(t, 1.0 / T)
    return k / (math.log1p(k * T) * (1.0 + k * (T - t)))


def f_modelo(t: ArrayLike, k: float, T: float) -> Vector:
    """F_k(t): fracción acumulada de entregas hasta la hora t (sin unidad)."""
    t = np.asarray(t, dtype=float)
    if k < K_MIN_TINY:
        return t / T
    return 1.0 - np.log1p(k * (T - t)) / math.log1p(k * T)


def ip_modelo(k: float, T: float, n: int = 2000) -> float:
    """IP del modelo = (1/T) * integral_0^T (1 - F_k(t)) dt, con Simpson propio.

    Entradas: k, intensidad (1/h); T, plazo (h); n, subintervalos de Simpson.
    Salida: IP del modelo, fracción entre 0,5 y 1.
    """
    return simpson(lambda t: 1.0 - f_modelo(t, k, T), 0.0, T, n) / T


def ip_modelo_cerrado(k: float, T: float) -> float:
    """Fórmula cerrada del IP (solo para verificar a Simpson): 1 + 1/kT - 1/ln(1 + kT)."""
    kap = k * T
    if kap < 1e-4:
        return 0.5 + kap / 12.0
    return 1.0 + 1.0 / kap - 1.0 / math.log1p(kap)


def fraccion_ultimas(k: float, T: float, ventana: float = 24.0) -> float:
    """Fracción de entregas en las últimas `ventana` horas: ln(1 + hk) / ln(1 + kT).

    Entradas: k (1/h); T y ventana (h). Salida: fracción entre 0 y 1.
    """
    if k < K_MIN_TINY:
        return ventana / T
    return math.log1p(ventana * k) / math.log1p(k * T)


def estimar_k(
    ip_obs: float,
    T: float,
    k_min: float = 1e-8,
    k_max: float = 1e4,
    tol: float = 1e-10,
    max_iter: int = 300,
) -> float:
    """Estima k por bisección, igualando ip_modelo(k, T) con el IP observado.

    ip_modelo crece con k (de 0,5 cuando k -> 0 hacia 1 cuando k -> infinito), así que
    por el teorema del valor intermedio hay un único k con ip_modelo(k) = ip_obs.

    Entradas: ip_obs, fracción entre 0,5 y 1; T, plazo (h); [k_min, k_max], búsqueda (1/h).
    Salida: k estimado, en 1/h.
    """
    if not 0.5 < ip_obs < 1.0:
        raise ValueError(f"IP observado={ip_obs:.3f}: el modelo solo representa IP entre 0,5 y 1.")
    a, b = k_min, k_max
    if not ip_modelo(a, T) <= ip_obs <= ip_modelo(b, T):
        raise ValueError("El IP observado queda fuera del rango alcanzable con [k_min, k_max].")
    for _ in range(max_iter):
        m = (a + b) / 2
        if ip_modelo(m, T) < ip_obs:
            a = m
        else:
            b = m
        if b - a < tol * max(1.0, b):
            break
    return (a + b) / 2


def simular_entregas(k: float, T: float, n: int, semilla: int = 0) -> Vector:
    """Genera n horas de entrega del modelo por transformada inversa de F_k (horas, en [0, T])."""
    u = np.random.default_rng(semilla).random(n)
    return T - ((1.0 + k * T) ** (1.0 - u) - 1.0) / k


# --------------------------------------------------------------------------
# Clase propia
# --------------------------------------------------------------------------
@dataclass
class GrupoEntregas:
    """Entregas a tiempo de un grupo: horas desde la apertura y plazo T (ambos en h).

    Reúne en un solo objeto los cálculos de un grupo: IP observado, k del modelo y la
    fracción de entregas de las últimas horas (observada y según el modelo).
    """

    nombre: str
    T: float
    horas: Vector

    @property
    def tau(self) -> Vector:
        """Fracción del plazo transcurrida en cada entrega (sin unidad)."""
        return np.asarray(self.horas, dtype=float) / self.T

    def ip_observado(self) -> float:
        """IP calculado de los datos con trapecio (fracción entre 0 y 1)."""
        return indice_procrastinacion(self.tau)

    def k_estimado(self) -> float:
        """k del modelo por bisección, en 1/h."""
        return estimar_k(self.ip_observado(), self.T)

    def ultimas_observada(self, ventana: float = 24.0) -> float:
        """Fracción de las entregas hechas en las últimas `ventana` horas del plazo."""
        return float((np.asarray(self.horas) >= self.T - ventana).mean())

    def ultimas_modelo(self, ventana: float = 24.0) -> float:
        """Fracción de las últimas `ventana` horas según el modelo ajustado."""
        return fraccion_ultimas(self.k_estimado(), self.T, ventana)
