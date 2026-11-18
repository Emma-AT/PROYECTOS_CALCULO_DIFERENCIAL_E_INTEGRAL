"""Integración numérica, índice de somnolencia, curva ROC y umbral óptimo.

Las reglas del trapecio y de Simpson, la curva ROC y el AUC se programan
desde cero (sin bibliotecas de aprendizaje automático). ``scipy.integrate``
solo se usa en las pruebas, para comparar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

Metodo = Literal["simpson", "trapecio"]


# --------------------------------------------------------------------------
# Integración numérica
# --------------------------------------------------------------------------
def trapecio(f: np.ndarray, S: np.ndarray) -> float:
    """Regla del trapecio compuesta para datos tabulados.

    Args:
        f: abscisas crecientes (Hz).
        S: valores de la función en f (µV²/Hz).

    Returns:
        Aproximación de la integral de S df (µV²).
    """
    f, S = np.asarray(f, float), np.asarray(S, float)
    return float(np.sum((f[1:] - f[:-1]) * (S[1:] + S[:-1]) / 2.0))


def simpson(f: np.ndarray, S: np.ndarray) -> float:
    """Regla de Simpson 1/3 compuesta para nodos equiespaciados.

    Si el número de subintervalos es impar, los últimos tres se integran
    con la regla de Simpson 3/8, que conserva el orden de precisión.

    Args:
        f: abscisas crecientes y equiespaciadas (Hz).
        S: valores de la función en f (µV²/Hz).

    Returns:
        Aproximación de la integral de S df (µV²).

    Raises:
        ValueError: si hay menos de 3 puntos o el paso no es constante.
    """
    f, S = np.asarray(f, float), np.asarray(S, float)
    n = len(f) - 1  # número de subintervalos
    if n < 2:
        raise ValueError("Simpson necesita al menos 3 puntos.")
    h = np.diff(f)
    if not np.allclose(h, h[0]):
        raise ValueError("Simpson exige nodos equiespaciados.")
    h0 = float(h[0])
    extra = 0.0
    if n % 2 == 1:  # Simpson 3/8 en los últimos 3 subintervalos
        extra = 3 * h0 / 8 * (S[-4] + 3 * S[-3] + 3 * S[-2] + S[-1])
        S, n = S[:-3], n - 3
        if n == 0:
            return float(extra)
    pares = S[0 : n + 1]
    total = pares[0] + pares[-1] + 4 * pares[1:-1:2].sum() + 2 * pares[2:-1:2].sum()
    return float(h0 / 3 * total + extra)


def potencia_banda(
    S: np.ndarray, f: np.ndarray, f1: float, f2: float, metodo: Metodo = "simpson"
) -> float:
    """Potencia de una banda: área bajo S(f) entre f1 y f2.

    Args:
        S: densidad espectral en los nodos f (µV²/Hz).
        f: frecuencias de los nodos (Hz).
        f1: límite inferior de la banda (Hz).
        f2: límite superior de la banda (Hz).
        metodo: "simpson" o "trapecio".

    Returns:
        Potencia de la banda (µV²).

    Raises:
        ValueError: si el método no existe o la banda no tiene nodos.
    """
    f, S = np.asarray(f, float), np.asarray(S, float)
    mascara = (f >= f1) & (f <= f2)
    if mascara.sum() < 2:
        raise ValueError(f"La banda [{f1}, {f2}] Hz tiene menos de 2 nodos.")
    reglas = {"simpson": simpson, "trapecio": trapecio}
    if metodo not in reglas:
        raise ValueError(f"Método desconocido: {metodo!r}.")
    return reglas[metodo](f[mascara], S[mascara])


def error_relativo(aprox: float, referencia: float) -> float:
    """Error relativo |aprox - referencia| / |referencia| (adimensional)."""
    return abs(aprox - referencia) / abs(referencia)


# --------------------------------------------------------------------------
# Verificación analítica: ajuste S(f) ≈ A f^b e integral exacta
# --------------------------------------------------------------------------
def ajustar_ley_potencia(f: np.ndarray, S: np.ndarray) -> tuple[float, float]:
    """Ajusta S(f) = A f^b por mínimos cuadrados en escala log-log.

    Args:
        f: frecuencias positivas (Hz).
        S: densidad espectral positiva (µV²/Hz).

    Returns:
        (A, b): A en µV²/Hz·Hz^(-b) y b adimensional (b < 0 si decrece).
    """
    b, log_a = np.polyfit(np.log(f), np.log(S), 1)
    return float(np.exp(log_a)), float(b)


def integral_ley_potencia(A: float, b: float, f1: float, f2: float) -> float:
    """Integral exacta de A f^b entre f1 y f2 (µV²), para b distinto de -1.

    Usa la antiderivada A f^(b+1) / (b+1); si b = -1, la de A ln f.
    """
    if np.isclose(b, -1.0):
        return float(A * (np.log(f2) - np.log(f1)))
    return float(A / (b + 1.0) * (f2 ** (b + 1.0) - f1 ** (b + 1.0)))


# --------------------------------------------------------------------------
# Potencias e índice de somnolencia
# --------------------------------------------------------------------------
def potencias_por_epoca(
    ancha: pd.DataFrame, params: dict[str, float], metodo: Metodo = "simpson"
) -> pd.DataFrame:
    """Calcula Pθ, Pα, Pβ y la potencia total de cada época.

    Args:
        ancha: tabla época × frecuencia (µV²/Hz), de ``cargar_espectro``.
        params: parámetros de ``leer_parametros`` (Hz).
        metodo: regla de integración.

    Returns:
        DataFrame con columnas theta, alfa, beta y total (µV²).
    """
    f = ancha.columns.to_numpy(dtype=float)
    bandas = {
        "theta": (params["theta_inf"], params["theta_sup"]),
        "alfa": (params["theta_sup"], params["alfa_sup"]),
        "beta": (params["alfa_sup"], params["beta_sup"]),
        "total": (float(f.min()), float(f.max())),
    }
    filas = {
        nombre: [potencia_banda(fila, f, a, b, metodo) for fila in ancha.to_numpy()]
        for nombre, (a, b) in bandas.items()
    }
    return pd.DataFrame(filas, index=ancha.index)


def indice_somnolencia(potencias: pd.DataFrame) -> pd.Series:
    """Índice I = (Pθ + Pα) / Pβ (adimensional)."""
    return (potencias["theta"] + potencias["alfa"]) / potencias["beta"]


def correlacion(x: np.ndarray, y: np.ndarray) -> float:
    """Coeficiente de correlación de Pearson (adimensional)."""
    return float(np.corrcoef(x, y)[0, 1])


# --------------------------------------------------------------------------
# Curva ROC y AUC
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class CurvaROC:
    """Curva ROC: un punto por cada umbral c (alarma si I >= c)."""

    umbrales: np.ndarray  # adimensional, de mayor a menor
    fpr: np.ndarray  # fracción
    tpr: np.ndarray  # fracción
    tp: np.ndarray  # épocas
    fp: np.ndarray  # épocas
    fn: np.ndarray  # épocas
    tn: np.ndarray  # épocas

    @property
    def auc(self) -> float:
        """Área bajo la curva ROC por la regla del trapecio."""
        return auc(self.fpr, self.tpr)


def curva_roc(indice: np.ndarray, etiqueta: np.ndarray) -> CurvaROC:
    """Construye la curva ROC variando el umbral sobre el índice.

    Args:
        indice: índice de somnolencia de cada época (adimensional).
        etiqueta: 1 = somnoliento, 0 = alerta.

    Returns:
        CurvaROC que parte de (0, 0) (umbral infinito) y llega a (1, 1).

    Raises:
        ValueError: si falta alguna de las dos clases o los tamaños difieren.
    """
    indice = np.asarray(indice, float)
    etiqueta = np.asarray(etiqueta, int)
    if indice.shape != etiqueta.shape:
        raise ValueError("indice y etiqueta deben tener el mismo tamaño.")
    positivos = int((etiqueta == 1).sum())
    negativos = int((etiqueta == 0).sum())
    if positivos == 0 or negativos == 0:
        raise ValueError("Se necesitan épocas de ambas clases para la ROC.")
    umbrales = np.concatenate(([np.inf], np.sort(np.unique(indice))[::-1]))
    alarma = indice[None, :] >= umbrales[:, None]
    tp = (alarma & (etiqueta == 1)).sum(axis=1)
    fp = (alarma & (etiqueta == 0)).sum(axis=1)
    return CurvaROC(
        umbrales=umbrales,
        fpr=fp / negativos,
        tpr=tp / positivos,
        tp=tp,
        fp=fp,
        fn=positivos - tp,
        tn=negativos - fp,
    )


def auc(fpr: np.ndarray, tpr: np.ndarray) -> float:
    """Área bajo la curva ROC: integral de TPR d(FPR) por trapecio."""
    return trapecio(np.asarray(fpr, float), np.asarray(tpr, float))


# --------------------------------------------------------------------------
# Umbral óptimo
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ResultadoUmbral:
    """Umbral elegido con su matriz de confusión y sus indicadores."""

    umbral: float  # adimensional
    tp: int
    fp: int
    fn: int
    tn: int
    sensibilidad: float  # fracción
    especificidad: float  # fracción
    costo: float  # unidades relativas

    def matriz_confusion(self) -> pd.DataFrame:
        """Matriz de confusión (filas: realidad; columnas: alarma)."""
        return pd.DataFrame(
            [[self.tn, self.fp], [self.fn, self.tp]],
            index=["alerta", "somnoliento"],
            columns=["sin alarma", "con alarma"],
        )

    def falsas_alarmas_por_hora(self, epocas_alerta: int, duracion_min: float) -> float:
        """Falsas alarmas por hora de conducción alerta.

        Args:
            epocas_alerta: número de épocas alertas evaluadas.
            duracion_min: duración de cada época (min).

        Returns:
            Falsas alarmas por hora.
        """
        horas_alerta = epocas_alerta * duracion_min / 60.0
        return self.fp / horas_alerta


def elegir_umbral(
    roc: CurvaROC, sens_min: float, costo_omision: float, costo_falsa_alarma: float
) -> ResultadoUmbral:
    """Elige el umbral de menor costo que cumple la sensibilidad mínima.

    Costo = costo_omision * FN + costo_falsa_alarma * FP. Entre umbrales
    con igual costo se prefiere el mayor (menos molesto para el chofer).

    Args:
        roc: curva ROC de ``curva_roc``.
        sens_min: sensibilidad mínima exigida (fracción).
        costo_omision: costo relativo de una omisión.
        costo_falsa_alarma: costo relativo de una falsa alarma.

    Returns:
        ResultadoUmbral con la matriz de confusión del umbral elegido.

    Raises:
        ValueError: si ningún umbral alcanza la sensibilidad mínima.
    """
    costo = costo_omision * roc.fn + costo_falsa_alarma * roc.fp
    factibles = np.where((roc.tpr >= sens_min) & np.isfinite(roc.umbrales))[0]
    if factibles.size == 0:
        raise ValueError("Ningún umbral alcanza la sensibilidad mínima exigida.")
    # índices menores = umbrales mayores; argmin devuelve el primero (mayor c)
    mejor = factibles[np.argmin(costo[factibles])]
    return ResultadoUmbral(
        umbral=float(roc.umbrales[mejor]),
        tp=int(roc.tp[mejor]),
        fp=int(roc.fp[mejor]),
        fn=int(roc.fn[mejor]),
        tn=int(roc.tn[mejor]),
        sensibilidad=float(roc.tpr[mejor]),
        especificidad=float(1.0 - roc.fpr[mejor]),
        costo=float(costo[mejor]),
    )


def evaluar_umbral(
    indice: np.ndarray,
    etiqueta: np.ndarray,
    umbral: float,
    costo_omision: float,
    costo_falsa_alarma: float,
) -> ResultadoUmbral:
    """Matriz de confusión e indicadores para un umbral dado (alarma si I >= c).

    Args:
        indice: índice de somnolencia de cada época (adimensional).
        etiqueta: 1 = somnoliento, 0 = alerta.
        umbral: umbral de alarma c (adimensional).
        costo_omision: costo relativo de una omisión.
        costo_falsa_alarma: costo relativo de una falsa alarma.

    Returns:
        ResultadoUmbral para ese umbral.

    Raises:
        ValueError: si falta alguna de las dos clases.
    """
    indice = np.asarray(indice, float)
    etiqueta = np.asarray(etiqueta, int)
    positivos = int((etiqueta == 1).sum())
    negativos = int((etiqueta == 0).sum())
    if positivos == 0 or negativos == 0:
        raise ValueError("Se necesitan épocas de ambas clases.")
    alarma = indice >= umbral
    tp = int((alarma & (etiqueta == 1)).sum())
    fp = int((alarma & (etiqueta == 0)).sum())
    return ResultadoUmbral(
        umbral=float(umbral),
        tp=tp,
        fp=fp,
        fn=positivos - tp,
        tn=negativos - fp,
        sensibilidad=tp / positivos,
        especificidad=1.0 - fp / negativos,
        costo=float(costo_omision * (positivos - tp) + costo_falsa_alarma * fp),
    )
