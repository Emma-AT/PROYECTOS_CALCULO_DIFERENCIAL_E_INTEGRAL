"""Lectura, validación y limpieza de la base de EEG (Proyecto 1, MA-0321).

Todas las funciones leen los datos del Excel entregado; los parámetros
(bandas, sensibilidad mínima, costos) se toman de la hoja ``Parametros``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HOJAS_REQUERIDAS: dict[str, list[str]] = {
    "Espectro_EEG": [
        "viaje",
        "epoca",
        "minuto_inicio",
        "frecuencia_Hz",
        "potencia_uV2_Hz",
    ],
    "Etiquetas": ["viaje", "epoca", "somnolencia_video", "tiempo_reaccion_ms"],
    "Parametros": ["parametro", "valor", "unidad"],
}

# Nombres de las filas de la hoja Parametros (se buscan por texto, no por valor).
CLAVES_PARAMETROS: dict[str, str] = {
    "theta_inf": "Banda theta, límite inferior",
    "theta_sup": "Banda theta, límite superior",
    "alfa_sup": "Banda alfa, límite superior",
    "beta_sup": "Banda beta, límite superior",
    "duracion_epoca_min": "Duración de cada época",
    "sens_min": "Sensibilidad mínima exigida",
    "costo_omision": "Costo relativo de una omisión",
    "costo_falsa_alarma": "Costo relativo de una falsa alarma",
}


def leer_base(ruta: str | Path) -> dict[str, pd.DataFrame]:
    """Lee todas las hojas del Excel y valida hojas y columnas.

    Args:
        ruta: ruta del archivo .xlsx entregado (no se modifica).

    Returns:
        Diccionario {nombre de hoja: DataFrame}.

    Raises:
        FileNotFoundError: si el archivo no existe.
        ValueError: si falta alguna hoja o columna requerida.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo de datos: {ruta}")
    hojas = pd.read_excel(ruta, sheet_name=None)
    for hoja, columnas in HOJAS_REQUERIDAS.items():
        if hoja not in hojas:
            raise ValueError(f"Falta la hoja '{hoja}' en {ruta.name}.")
        faltan = [c for c in columnas if c not in hojas[hoja].columns]
        if faltan:
            raise ValueError(f"En la hoja '{hoja}' faltan las columnas: {faltan}.")
    return hojas


def leer_parametros(hoja: pd.DataFrame) -> dict[str, float]:
    """Convierte la hoja ``Parametros`` en un diccionario con claves cortas.

    Args:
        hoja: DataFrame con columnas parametro, valor y unidad.

    Returns:
        Diccionario {clave corta: valor}. Unidades: Hz para frecuencias,
        min para la duración de la época, fracción para la sensibilidad y
        unidades relativas para los costos.

    Raises:
        ValueError: si falta algún parámetro necesario.
    """
    por_nombre = dict(zip(hoja["parametro"], hoja["valor"]))
    resultado: dict[str, float] = {}
    for clave, nombre in CLAVES_PARAMETROS.items():
        if nombre not in por_nombre:
            raise ValueError(f"Falta el parámetro '{nombre}' en la hoja Parametros.")
        resultado[clave] = float(por_nombre[nombre])
    return resultado


def cargar_espectro(ruta: str | Path) -> pd.DataFrame:
    """Devuelve la tabla ancha época × frecuencia con faltantes interpolados.

    Los faltantes se completan por interpolación lineal en la frecuencia,
    dentro de cada época (nunca entre épocas distintas).

    Args:
        ruta: ruta del archivo .xlsx entregado.

    Returns:
        DataFrame con índice (viaje, epoca), columnas = frecuencia (Hz) y
        valores en µV²/Hz.
    """
    espectro = leer_base(ruta)["Espectro_EEG"]
    ancha = espectro.pivot_table(
        index=["viaje", "epoca"],
        columns="frecuencia_Hz",
        values="potencia_uV2_Hz",
        aggfunc="mean",
    )
    return ancha.interpolate(axis=1, method="linear", limit_direction="both")


def contar_faltantes(ruta: str | Path) -> int:
    """Cuenta los registros de potencia faltantes en la hoja Espectro_EEG.

    Args:
        ruta: ruta del archivo .xlsx entregado.

    Returns:
        Número de celdas de potencia vacías (adimensional).
    """
    return int(leer_base(ruta)["Espectro_EEG"]["potencia_uV2_Hz"].isna().sum())


def detectar_artefactos(potencia_total: pd.Series, umbral_z: float = 10.0) -> pd.Series:
    """Marca épocas atípicas por viaje con el puntaje z modificado (MAD).

    Se usa la mediana y la desviación absoluta mediana porque, a diferencia
    de la media y la desviación estándar, no se distorsionan con el propio
    artefacto. El criterio clásico de Iglewicz y Hoaglin (1993) es z > 3,5,
    pero en esta base la dispersión dentro de cada viaje es tan pequeña que
    marca también épocas somnolientas legítimas (más potencia lenta). Los
    artefactos de movimiento son mucho más extremos (z > 40), por lo que se
    usa z > 10 por defecto; el valor se puede cambiar y debe documentarse.

    Args:
        potencia_total: Serie con índice (viaje, epoca) y la potencia total
            de cada época en µV².
        umbral_z: puntaje z modificado a partir del cual hay artefacto.

    Returns:
        Serie booleana con el mismo índice; True = época con artefacto.
    """

    def _marcar(grupo: pd.Series) -> pd.Series:
        mediana = grupo.median()
        mad = (grupo - mediana).abs().median()
        if mad == 0:
            return pd.Series(False, index=grupo.index)
        z = 0.6745 * (grupo - mediana) / mad
        return z.abs() > umbral_z

    return potencia_total.groupby(level="viaje", group_keys=False).apply(_marcar)


def vector_a_array(serie: pd.Series) -> np.ndarray:
    """Convierte una Serie en arreglo de float (utilidad para los modelos)."""
    return serie.to_numpy(dtype=float)
