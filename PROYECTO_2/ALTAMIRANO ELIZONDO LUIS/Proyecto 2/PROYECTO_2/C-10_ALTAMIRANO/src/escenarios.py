"""Indicadores por grupo, elección de la estrategia, sensibilidad e incertidumbre.

Criterio del cliente: se elige la estrategia con mayor nota media; si otra queda a menos
de la diferencia mínima (hoja Parametros), se prefiere la que requiere menos horas docentes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.limpieza import depurar_entregas
from src.modelo import GrupoEntregas, ip_modelo


def resumen_grupo(
    dep: pd.DataFrame, grupos: pd.DataFrame, ventana_h: float = 24.0, nota_max: float = 100.0
) -> pd.DataFrame:
    """Tabla con una fila por grupo y los indicadores que pide el cliente.

    - nota_media: promedio de las notas de todas las entregas (a tiempo y tardías).
    - nota_media_con_ceros: las entregas que no existen cuentan como 0.
    - ip_obs, k, ip_modelo: índice de procrastinación observado, k estimado y IP del modelo.
    - ultimas_obs / ultimas_modelo: fracción de entregas a tiempo en las últimas 24 h.
    """
    filas = []
    n_tareas = dep["tarea"].nunique()
    for g, s in dep.groupby("grupo"):
        info = grupos.set_index("grupo").loc[g]
        T = float(s["plazo_h"].iloc[0])
        a_tiempo = s[~s["tardia"] & ~s["antes_apertura"]]
        gr = GrupoEntregas(g, T, a_tiempo["horas"].to_numpy())
        ip = gr.ip_observado()
        k = gr.k_estimado()
        esperadas = int(info["estudiantes"]) * n_tareas
        filas.append(
            {
                "grupo": g,
                "estrategia": info["estrategia"],
                "horas_docente": float(info["horas_docente_extra_por_tarea"]),
                "T_h": T,
                "entregas_esperadas": esperadas,
                "entregas": len(s),
                "no_entregas_pct": 100 * (1 - len(s) / esperadas),
                "tardias_pct": 100 * s["tardia"].mean(),
                "nota_media": s["nota"].mean(),
                "nota_media_con_ceros": s["nota"].fillna(s["nota"].mean()).sum() / esperadas,
                "ip_obs": ip,
                "k": k,
                "ip_modelo": ip_modelo(k, T),
                "ultimas_obs": gr.ultimas_observada(ventana_h),
                "ultimas_modelo": gr.ultimas_modelo(ventana_h),
            }
        )
    return pd.DataFrame(filas)


def elegir_estrategia(
    resumen: pd.DataFrame, umbral: float, columna_nota: str = "nota_media"
) -> tuple[str, dict]:
    """Aplica el criterio del cliente. Devuelve (grupo_elegido, explicación)."""
    mejor = resumen.loc[resumen[columna_nota].idxmax()]
    cercanas = resumen[mejor[columna_nota] - resumen[columna_nota] < umbral]
    elegido = cercanas.sort_values(["horas_docente", columna_nota], ascending=[True, False]).iloc[0]
    explicacion = {
        "mejor_nota": mejor["grupo"],
        "candidatas": cercanas["grupo"].tolist(),
        "elegida": elegido["grupo"],
        "umbral": umbral,
        "diferencia_con_mejor": float(mejor[columna_nota] - elegido[columna_nota]),
    }
    return elegido["grupo"], explicacion


def sensibilidad_umbral(resumen: pd.DataFrame, umbrales: list[float]) -> pd.DataFrame:
    """Qué estrategia se elige para distintos valores de la diferencia mínima."""
    filas = []
    for u in umbrales:
        g, _ = elegir_estrategia(resumen, u)
        filas.append({"umbral_puntos": u, "elegida": g})
    return pd.DataFrame(filas)


def umbral_de_cambio(resumen: pd.DataFrame, columna_nota: str = "nota_media") -> pd.DataFrame:
    """Umbrales (en puntos) a partir de los cuales cambia la estrategia elegida."""
    mejor = resumen[columna_nota].max()
    candidatos = sorted((mejor - resumen[columna_nota]).tolist())
    cambios, previa = [], None
    for c in candidatos:
        if c <= 0:
            continue
        g, _ = elegir_estrategia(resumen, c + 1e-9, columna_nota)
        if g != previa:
            cambios.append({"umbral_puntos": round(c, 2), "pasa_a": g})
            previa = g
    return pd.DataFrame(cambios)


def sensibilidad_tratamientos(
    entregas: pd.DataFrame,
    tareas: pd.DataFrame,
    grupos: pd.DataFrame,
    ventana_h: float,
    nota_max: float,
    umbral: float,
) -> pd.DataFrame:
    """Repite todo el análisis con distintos tratamientos de datos y mide si cambia la decisión."""
    casos = [
        ("Base: notas >100 ÷10, faltantes excluidas", "dividir10", "excluir", False),
        ("Notas >100 descartadas", "descartar", "excluir", False),
        ("Notas >100 con tope 100", "tope", "excluir", False),
        ("Faltantes con media grupo-tarea", "dividir10", "imputar_media_grupo_tarea", False),
        ("No entregas cuentan como 0", "dividir10", "excluir", True),
    ]
    filas = []
    for nombre, atip, falt, ceros in casos:
        dep = depurar_entregas(entregas, tareas, nota_max, atip, falt)
        res = resumen_grupo(dep, grupos, ventana_h, nota_max)
        col = "nota_media_con_ceros" if ceros else "nota_media"
        elegida, _ = elegir_estrategia(res, umbral, col)
        fila = {"caso": nombre}
        fila.update({g: round(v, 2) for g, v in zip(res["grupo"], res[col])})
        fila["elegida"] = elegida
        filas.append(fila)
    return pd.DataFrame(filas)


def bootstrap_diferencia(
    dep: pd.DataFrame, g1: str, g2: str, repeticiones: int = 5000, semilla: int = 0
) -> tuple[float, float, float]:
    """Intervalo del 95 % para la diferencia de nota media entre dos grupos.

    Se remuestrean estudiantes (no entregas sueltas), porque las notas de una misma persona
    no son independientes. Devuelve (diferencia, límite_inferior, límite_superior).
    """
    rng = np.random.default_rng(semilla)
    medias = dep.groupby(["grupo", "estudiante"])["nota"].mean().dropna()
    a = medias[g1].to_numpy()
    b = medias[g2].to_numpy()
    difs = np.empty(repeticiones)
    for i in range(repeticiones):
        difs[i] = rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean()
    return (
        float(a.mean() - b.mean()),
        float(np.percentile(difs, 2.5)),
        float(np.percentile(difs, 97.5)),
    )


def texto_recomendacion(
    resumen: pd.DataFrame, elegida: str, explicacion: dict, n_tareas: int = 8
) -> str:
    """Recomendación cuantificada con los números calculados (sin IA)."""
    r = resumen.set_index("grupo")
    e = r.loc[elegida]
    base = r.loc["G01"] if "G01" in r.index else r.iloc[0]
    horas_sem = e["horas_docente"] * n_tareas
    return (
        f"Aplicar «{e['estrategia']}» ({elegida}) en todos los grupos. En el semestre anterior ese grupo "
        f"obtuvo nota media {e['nota_media']:.1f}, {e['nota_media'] - base['nota_media']:+.1f} puntos "
        f"respecto a «{base['estrategia']}»; sus entregas tardías fueron {e['tardias_pct']:.1f} % "
        f"(frente a {base['tardias_pct']:.1f} %) y solo {100 * e['ultimas_obs']:.0f} % de las entregas "
        f"llegó en las últimas 24 h (frente a {100 * base['ultimas_obs']:.0f} %). "
        f"Costo docente: {e['horas_docente']:.1f} h por tarea, unas {horas_sem:.0f} h por grupo en {n_tareas} tareas."
    )
