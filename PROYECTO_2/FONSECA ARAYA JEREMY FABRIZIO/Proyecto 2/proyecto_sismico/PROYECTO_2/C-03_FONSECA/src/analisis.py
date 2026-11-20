"""Orquesta el mismo cálculo para la aplicación, el cuaderno y el reporte."""

import numpy as np
import pandas as pd

from src.escenarios import comparar_escenarios, recomendar, sensibilidad
from src.limpieza import BaseDatos
from src.modelo import (
    analizar_movimiento,
    estimar_b,
    probabilidad,
    validar_seno,
    verificar_integrales,
    vpn_refuerzo,
)
from src.numericos import error_relativo, simpson


def analizar(base: BaseDatos, b: float | None = None, r: float | None = None) -> dict:
    """Devuelve cálculos, indicadores y tablas desde BaseDatos y controles b, r.

    b adimensional y r fracción anual. Ningún resultado se obtiene con IA.
    """
    catalogo = base.hojas["Catalogo_sismos"]
    b_base = estimar_b(catalogo, base.m0)
    b = b_base if b is None else b
    r = base.parametro("Tasa de descuento anual") / 100 if r is None else r
    lam = len(catalogo) / base.anos_catalogo
    series, indicadores = analizar_movimiento(base)
    escenarios = comparar_escenarios(base, b, r)
    verificacion = verificar_integrales(base, b, series)
    H = base.parametro("Horizonte de evaluación")
    t = np.linspace(0, H, 1001)
    filas = []
    for _, fila in escenarios.iloc[1:].iterrows():
        exacta = vpn_refuerzo(fila.costo_colones, fila.ahorro_anual_colones, r, H)
        numerica = simpson(t, fila.ahorro_anual_colones * np.exp(-r * t)) - fila.costo_colones
        filas.append(
            {
                "integral": f"VPN {fila.escenario}",
                "metodo": "Simpson",
                "valor": numerica,
                "referencia": "Fórmula exacta",
                "valor_referencia": exacta,
                "unidad": "colones",
                "error_relativo_pct": error_relativo(numerica, exacta),
            }
        )
    verificacion = pd.concat([verificacion, pd.DataFrame(filas)], ignore_index=True)
    verificacion["diferencia_absoluta"] = abs(verificacion.valor - verificacion.valor_referencia)
    return {
        "b": b,
        "b_estimado": b_base,
        "r": r,
        "H": H,
        "lambda3": lam,
        "prob6_50": probabilidad(6, lam, b, 50),
        "prob7_50": probabilidad(7, lam, b, 50),
        "series": series,
        "indicadores": indicadores,
        "escenarios": escenarios,
        "recomendacion": recomendar(escenarios).to_dict(),
        "verificacion": verificacion,
        "sensibilidad": sensibilidad(base, b_base),
        "seno": validar_seno(),
    }


def formato_colones(valor: float) -> str:
    """Recibe colones y devuelve texto costarricense, sin cambiar la unidad."""
    return ("-" if valor < 0 else "") + "₡" + f"{abs(valor):,.0f}".replace(",", ".")


def tabla_visible(tabla: pd.DataFrame) -> pd.DataFrame:
    """Convierte tabla numérica de escenarios en una copia con rótulos y moneda."""
    copia = tabla[
        [
            "escenario",
            "costo_colones",
            "pae_colones_ano",
            "ahorro_anual_colones",
            "vpn_colones",
            "plazo_meses",
        ]
    ].copy()
    for col in ["costo_colones", "pae_colones_ano", "ahorro_anual_colones", "vpn_colones"]:
        copia[col] = copia[col].map(formato_colones)
    copia.columns = [
        "Alternativa",
        "Inversión",
        "Pérdida anual",
        "Ahorro anual",
        "VPN",
        "Obra (meses)",
    ]
    return copia
