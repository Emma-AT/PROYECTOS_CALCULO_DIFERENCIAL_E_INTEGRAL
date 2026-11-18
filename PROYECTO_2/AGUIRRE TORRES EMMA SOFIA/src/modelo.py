"""Integración numérica propia, curvas de potencia y distribución de Weibull."""

import math
from dataclasses import dataclass

import numpy as np


def trapecio(y, dx: float) -> float:
    """Regla del trapecio compuesta con paso constante dx.

    Entradas: valores y (unidades de y) y paso dx (unidades de x).
    Salida: integral aproximada (unidades de y · unidades de x).
    """
    y = np.asarray(y, dtype=float)
    if y.size < 2:
        raise ValueError("Se necesitan al menos 2 puntos.")
    return float(dx * (y.sum() - 0.5 * (y[0] + y[-1])))


def trapecio_acumulado(y, dx: float) -> np.ndarray:
    """Integral acumulada F(x_i) = ∫ y dx desde x_0 hasta x_i por trapecios (F(x_0) = 0)."""
    y = np.asarray(y, dtype=float)
    return np.concatenate(([0.0], np.cumsum(0.5 * dx * (y[1:] + y[:-1]))))


def simpson(y, dx: float) -> float:
    """Regla de Simpson 1/3 compuesta; requiere un número par de subintervalos."""
    y = np.asarray(y, dtype=float)
    n = y.size - 1
    if n < 2 or n % 2 != 0:
        raise ValueError("Simpson necesita un número par de subintervalos.")
    return float(dx / 3 * (y[0] + y[-1] + 4 * y[1:-1:2].sum() + 2 * y[2:-1:2].sum()))


@dataclass
class Turbina:
    """Una opción de la planta: N turbinas iguales con su curva de potencia.

    Unidades: potencia kW, diámetro y altura m, inversión colones,
    mantenimiento colones/año, curva_v m/s, curva_p kW (a densidad de referencia).
    """

    nombre: str
    n: int
    p_nom_kw: float
    diametro_m: float
    altura_m: float
    inversion: float
    mantenimiento: float
    curva_v: np.ndarray
    curva_p: np.ndarray

    @property
    def area_m2(self) -> float:
        """Área barrida por el rotor A = π D² / 4 (m²)."""
        return math.pi * self.diametro_m**2 / 4

    def cp(self, rho_ref: float) -> np.ndarray:
        """Coeficiente de potencia Cp(v) = P(v) / (½ ρ A v³) en cada punto de la curva."""
        cp = np.zeros_like(self.curva_v, dtype=float)
        ok = self.curva_v > 0
        p_viento_w = 0.5 * rho_ref * self.area_m2 * self.curva_v[ok] ** 3
        cp[ok] = 1000 * self.curva_p[ok] / p_viento_w
        return cp


def turbinas_desde_excel(hojas) -> list[Turbina]:
    """Crea una Turbina por cada fila de la hoja Opciones.

    Supuesto: la fila i de Opciones corresponde a la columna i+1 de Curvas_potencia
    (Mantener -> actual_V47_kW, Opción A -> opcion_A_kW, Opción B -> opcion_B_kW).
    """
    curvas = hojas["Curvas_potencia"]
    v = curvas["velocidad_m_s"].to_numpy(dtype=float)
    lista = []
    for (_, fila), col in zip(hojas["Opciones"].iterrows(), curvas.columns[1:], strict=True):
        lista.append(
            Turbina(
                nombre=str(fila["opcion"]),
                n=int(fila["turbinas"]),
                p_nom_kw=float(fila["potencia_nominal_kW"]),
                diametro_m=float(fila["diametro_rotor_m"]),
                altura_m=float(fila["altura_buje_m"]),
                inversion=float(fila["inversion_colones"]),
                mantenimiento=float(fila["mantenimiento_anual_colones"]),
                curva_v=v,
                curva_p=curvas[col].to_numpy(dtype=float),
            )
        )
    return lista


def potencia(v, turbina: Turbina, rho, rho_ref: float) -> np.ndarray:
    """Potencia de UNA turbina (kW): interpola su curva y corrige por densidad.

    P(v, ρ) = P_curva(v) · ρ / ρ_ref, sin superar la potencia nominal.
    Por encima de la velocidad de corte la potencia es 0.
    """
    p = np.interp(v, turbina.curva_v, turbina.curva_p, left=0.0, right=0.0)
    return np.minimum(p * np.asarray(rho, dtype=float) / rho_ref, turbina.p_nom_kw)


def energia(p_kw, dt_h: float = 1.0) -> float:
    """Energía E = ∫ P dt con trapecio propio. Entradas kW y h; salida kWh."""
    return trapecio(p_kw, dt_h)


def calibrar_perdidas(e_teorica_kwh: float, e_medida_kwh: float) -> float:
    """Pérdidas totales L = 1 − E_medida / E_teórica (fracción, sin unidades)."""
    return 1.0 - e_medida_kwh / e_teorica_kwh


def weibull_momentos(v) -> tuple[float, float]:
    """Estima k (sin unidades) y c (m/s) por el método de momentos.

    Resuelve (σ/μ)² = Γ(1+2/k) / Γ(1+1/k)² − 1 por bisección y luego c = μ / Γ(1+1/k).
    """
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    cv2 = (v.std(ddof=1) / v.mean()) ** 2

    def g(k: float) -> float:
        return math.gamma(1 + 2 / k) / math.gamma(1 + 1 / k) ** 2 - 1 - cv2

    a, b = 0.5, 20.0
    for _ in range(60):
        m = 0.5 * (a + b)
        if g(a) * g(m) <= 0:
            b = m
        else:
            a = m
    k = 0.5 * (a + b)
    return k, float(v.mean() / math.gamma(1 + 1 / k))


def densidad_weibull(v, k: float, c: float) -> np.ndarray:
    """f(v) = (k/c)(v/c)^(k−1) e^(−(v/c)^k) para v ≥ 0. Unidades: s/m."""
    v = np.clip(np.asarray(v, dtype=float), 0.0, None)
    return (k / c) * (v / c) ** (k - 1) * np.exp(-((v / c) ** k))


def potencia_media(turbina: Turbina, k: float, c: float, rho, rho_ref: float, n: int = 1000):
    """P̄ = ∫_0^∞ P(v) f(v) dv (kW) con Simpson propio.

    Como P(v) = 0 después de la velocidad de corte, basta integrar hasta ese valor.
    """
    v = np.linspace(0.0, turbina.curva_v.max(), n + 1)
    integrando = potencia(v, turbina, rho, rho_ref) * densidad_weibull(v, k, c)
    return simpson(integrando, v[1] - v[0])
