"""Escenarios, sensibilidad y recomendación del umbral de alarma.

Los parámetros base (sensibilidad mínima y costos) se leen de la hoja
``Parametros``; los escenarios los modifican con factores relativos.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from src import limpieza, modelo


@dataclass(frozen=True)
class Datos:
    """Datos preparados para el modelo (una fila por época)."""

    potencias: pd.DataFrame  # µV², columnas theta, alfa, beta, total
    indice: pd.Series  # adimensional
    somnolencia: np.ndarray  # 1 = somnoliento, 0 = alerta
    tiempo_reaccion: np.ndarray  # ms
    artefacto: np.ndarray  # bool
    params: dict[str, float]
    ancha: pd.DataFrame  # espectro época × frecuencia, µV²/Hz


@dataclass(frozen=True)
class Escenario:
    """Política de alarma: costos, sensibilidad mínima y uso de artefactos."""

    nombre: str
    sens_min: float  # fracción
    costo_omision: float  # unidades relativas
    costo_falsa_alarma: float  # unidades relativas
    excluir_artefactos: bool  # True: el equipo descarta épocas con movimiento


def preparar_datos(ruta: str | Path, umbral_z: float = 10.0) -> Datos:
    """Lee el Excel y calcula potencias, índice y artefactos.

    Args:
        ruta: ruta del archivo .xlsx entregado.
        umbral_z: puntaje z modificado para marcar artefactos.

    Returns:
        Datos listos para construir ROC y escenarios.
    """
    base = limpieza.leer_base(ruta)
    params = limpieza.leer_parametros(base["Parametros"])
    ancha = limpieza.cargar_espectro(ruta)
    pot = modelo.potencias_por_epoca(ancha, params, "simpson")
    et = base["Etiquetas"].set_index(["viaje", "epoca"]).loc[ancha.index]
    art = limpieza.detectar_artefactos(pot["total"], umbral_z)
    return Datos(
        potencias=pot,
        indice=modelo.indice_somnolencia(pot),
        somnolencia=et["somnolencia_video"].to_numpy(dtype=int),
        tiempo_reaccion=et["tiempo_reaccion_ms"].to_numpy(dtype=float),
        artefacto=art.to_numpy(dtype=bool),
        params=params,
        ancha=ancha,
    )


def construir_escenarios(params: dict[str, float]) -> list[Escenario]:
    """Crea el escenario base y dos alternativas a partir de ``Parametros``.

    Args:
        params: parámetros de ``leer_parametros``.

    Returns:
        [base, menos falsas alarmas, sin filtro de artefactos].
    """
    base = Escenario(
        "Base (Parametros)",
        params["sens_min"],
        params["costo_omision"],
        params["costo_falsa_alarma"],
        True,
    )
    return [
        base,
        replace(
            base,
            nombre="Chofer prioritario (falsa alarma x10)",
            costo_falsa_alarma=10 * params["costo_falsa_alarma"],
        ),
        replace(
            base, nombre="Equipo sin filtro de artefactos", excluir_artefactos=False
        ),
    ]


def evaluar_escenario(esc: Escenario, datos: Datos) -> dict[str, float | str]:
    """Calcula ROC, umbral óptimo e indicadores de un escenario.

    Args:
        esc: escenario a evaluar.
        datos: datos preparados.

    Returns:
        Diccionario con umbral, sensibilidad, especificidad, AUC, costo y
        falsas alarmas por hora (de épocas alertas).
    """
    usar = ~datos.artefacto if esc.excluir_artefactos else np.ones_like(datos.artefacto)
    y = datos.somnolencia[usar]
    roc = modelo.curva_roc(datos.indice.to_numpy()[usar], y)
    r = modelo.elegir_umbral(
        roc, esc.sens_min, esc.costo_omision, esc.costo_falsa_alarma
    )
    fa_h = r.falsas_alarmas_por_hora(
        int((y == 0).sum()), datos.params["duracion_epoca_min"]
    )
    return {
        "escenario": esc.nombre,
        "epocas_usadas": int(usar.sum()),
        "AUC": roc.auc,
        "umbral": r.umbral,
        "sensibilidad": r.sensibilidad,
        "especificidad": r.especificidad,
        "omisiones": r.fn,
        "falsas_alarmas": r.fp,
        "costo": r.costo,
        "falsas_alarmas_por_hora": fa_h,
    }


def comparar_escenarios(datos: Datos) -> pd.DataFrame:
    """Tabla comparativa de los escenarios (una fila por escenario)."""
    filas = [evaluar_escenario(e, datos) for e in construir_escenarios(datos.params)]
    return pd.DataFrame(filas)


def barrido_sensibilidad(
    datos: Datos, razones: np.ndarray, sens_mins: np.ndarray
) -> pd.DataFrame:
    """Umbral óptimo al variar la razón de costos y la sensibilidad mínima.

    Args:
        datos: datos preparados.
        razones: razón costo_omision / costo_falsa_alarma a probar.
        sens_mins: sensibilidades mínimas a probar (fracción).

    Returns:
        DataFrame con razon, sens_min, umbral, sensibilidad y falsas_alarmas.
        Las combinaciones sin umbral factible quedan fuera.
    """
    usar = ~datos.artefacto
    roc = modelo.curva_roc(datos.indice.to_numpy()[usar], datos.somnolencia[usar])
    filas = []
    for razon in razones:
        for s in sens_mins:
            try:
                r = modelo.elegir_umbral(roc, float(s), float(razon), 1.0)
            except ValueError:
                continue
            filas.append(
                {
                    "razon_omision_falsa_alarma": razon,
                    "sens_min": s,
                    "umbral": r.umbral,
                    "sensibilidad": r.sensibilidad,
                    "falsas_alarmas": r.fp,
                }
            )
    return pd.DataFrame(filas)
