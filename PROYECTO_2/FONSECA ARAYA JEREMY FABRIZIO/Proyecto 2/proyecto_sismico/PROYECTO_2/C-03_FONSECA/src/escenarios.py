"""Comparación de situación actual, opción A y opción B, con sensibilidad."""

import numpy as np
import pandas as pd

from src.limpieza import BaseDatos
from src.modelo import perdida_anual, vpn_refuerzo


def comparar_escenarios(base: BaseDatos, b: float, r: float | None = None) -> pd.DataFrame:
    """Devuelve costos, PAE, ahorro, VPN y plazo de tres escenarios.

    b adimensional, r fracción anual; demás parámetros proceden del Excel.
    """
    r = base.parametro("Tasa de descuento anual") / 100 if r is None else r
    H = base.parametro("Horizonte de evaluación")
    V = base.parametro("Valor de reposición del pabellón")
    lambda3 = len(base.hojas["Catalogo_sismos"]) / base.anos_catalogo
    vul = base.hojas["Vulnerabilidad"]
    m = vul.magnitud_Mw.to_numpy()
    opciones = base.hojas["Opciones_refuerzo"].set_index("opcion")
    pae_actual = perdida_anual(m, vul.dano_actual_pct / 100, lambda3, b, V)
    filas = []
    for nombre, columna in [
        ("Sin refuerzo", "dano_actual_pct"),
        ("Opción A", "dano_opcion_A_pct"),
        ("Opción B", "dano_opcion_B_pct"),
    ]:
        actual = nombre == "Sin refuerzo"
        costo = 0.0 if actual else float(opciones.loc[nombre, "costo_colones"])
        plazo = 0.0 if actual else float(opciones.loc[nombre, "plazo_obra_meses"])
        pae = perdida_anual(m, vul[columna] / 100, lambda3, b, V)
        ahorro = pae_actual - pae
        filas.append(
            {
                "escenario": nombre,
                "costo_colones": costo,
                "pae_colones_ano": pae,
                "ahorro_anual_colones": ahorro,
                "vpn_colones": vpn_refuerzo(costo, ahorro, r, H),
                "plazo_meses": plazo,
                "ahorro_anual_por_colon": ahorro / costo if costo else np.nan,
                "descripcion": "Mantener el estado actual"
                if actual
                else opciones.loc[nombre, "descripcion"],
            }
        )
    return pd.DataFrame(filas)


def recomendar(tabla: pd.DataFrame) -> pd.Series:
    """Selecciona el mayor VPN (colones), incluyendo no invertir, cuyo VPN es cero."""
    return tabla.loc[tabla.vpn_colones.idxmax()]


def sensibilidad(base: BaseDatos, b: float) -> pd.DataFrame:
    """Compara b±0,1 y r base±2 puntos porcentuales, solos y combinados.

    Perturbación de b del enunciado. ±2 pp es supuesto explícito de sensibilidad.
    """
    r = base.parametro("Tasa de descuento anual") / 100
    filas = []
    for db in [-0.1, 0.0, 0.1]:
        for dr in [-0.02, 0.0, 0.02]:
            if b + db <= 0 or r + dr < 0:
                continue
            tabla = comparar_escenarios(base, b + db, r + dr)
            elegida = recomendar(tabla).escenario
            for _, fila in tabla.iterrows():
                filas.append(
                    {
                        "b": b + db,
                        "r_pct": (r + dr) * 100,
                        "delta_b": db,
                        "delta_r_pp": dr * 100,
                        "escenario": fila.escenario,
                        "vpn_colones": fila.vpn_colones,
                        "recomendacion": elegida,
                    }
                )
    return pd.DataFrame(filas)
