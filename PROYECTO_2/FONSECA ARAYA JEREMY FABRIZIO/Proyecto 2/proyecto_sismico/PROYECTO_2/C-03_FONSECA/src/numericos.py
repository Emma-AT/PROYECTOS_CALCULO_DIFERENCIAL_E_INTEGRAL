"""Integración propia. SciPy no participa en estos algoritmos."""

import numpy as np
from numpy.typing import ArrayLike, NDArray


def validar_vectores(x: ArrayLike, y: ArrayLike) -> tuple[NDArray, NDArray]:
    """Recibe abscisas y ordenadas; devuelve vectores finitos, ordenados y pareados.

    Conserva las unidades de entrada. Rechaza vacíos, duplicados y desorden.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 1 or y.shape != x.shape or len(x) < 2:
        raise ValueError("Se necesitan dos vectores del mismo tamaño, con al menos 2 datos.")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Los vectores deben contener números finitos, sin faltantes.")
    if np.any(np.diff(x) <= 0):
        raise ValueError("Las abscisas deben crecer estrictamente, sin duplicados.")
    return x, y


def integral_acumulada(t: ArrayLike, y: ArrayLike) -> NDArray:
    """Integra por trapecios desde t[0]; devuelve un valor por muestra, inicial 0.

    Si t está en s e y en cm/s², devuelve cm/s. Admite pasos no uniformes.
    """
    t, y = validar_vectores(t, y)
    areas = np.diff(t) * (y[:-1] + y[1:]) / 2
    return np.concatenate(([0.0], np.cumsum(areas)))


def trapecio(x: ArrayLike, y: ArrayLike) -> float:
    """Integra datos tabulados con trapecios propios; salida en unidad(x)*unidad(y)."""
    x, y = validar_vectores(x, y)
    return float(np.sum(np.diff(x) * (y[:-1] + y[1:]) / 2))


def simpson(x: ArrayLike, y: ArrayLike) -> float:
    """Aplica Simpson 1/3 propio; requiere paso uniforme y número par de intervalos.

    Entradas: x, y tabulados. Salida: integral en unidad(x)*unidad(y).
    """
    x, y = validar_vectores(x, y)
    h = np.diff(x)
    if len(h) % 2 or not np.allclose(h, h[0], rtol=1e-8, atol=1e-12):
        raise ValueError("Simpson requiere intervalos pares y del mismo ancho.")
    return float(h[0] / 3 * (y[0] + y[-1] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum()))


def error_relativo(valor: float, referencia: float) -> float:
    """Devuelve error relativo porcentual; si referencia=0 usa 0 o infinito.

    Las entradas deben tener las mismas unidades. No inventa un denominador.
    """
    if referencia == 0:
        return 0.0 if valor == 0 else float("inf")
    return float(100 * abs(valor - referencia) / abs(referencia))
