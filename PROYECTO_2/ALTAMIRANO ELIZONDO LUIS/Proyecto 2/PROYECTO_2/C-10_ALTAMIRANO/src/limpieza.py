"""Lectura, validación y limpieza de la base de datos.

Funciones principales:
- cargar_datos / validar_entradas: leen el Excel y fallan con un mensaje claro si falta algo.
- leer_parametros: convierte la hoja Parametros en un diccionario con nombres cortos.
- depurar_entregas: deja un solo intento por estudiante y tarea, corrige las notas mayores
  que 100, calcula las horas desde la apertura y marca las entregas tardías.
"""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

COLUMNAS = {
    "Entregas": ["tarea", "grupo", "estudiante", "intento", "fecha_hora_entrega", "nota"],
    "Tareas": ["tarea", "grupo", "apertura", "cierre"],
    "Grupos": ["grupo", "estrategia", "estudiantes", "horas_docente_extra_por_tarea"],
    "Parametros": ["parametro", "valor", "unidad"],
}

PARAMETROS = {
    "plazo_normal_h": "Duración normal del plazo",
    "ventana_h": "Ventana de las últimas horas",
    "umbral_nota": "Diferencia mínima de nota relevante",
    "nota_max": "Nota máxima posible",
}

ATIPICOS = ("dividir10", "descartar", "tope")
FALTANTES = ("excluir", "imputar_media_grupo_tarea")


def validar_entradas(hojas: dict[str, pd.DataFrame]) -> bool:
    """Revisa que existan las hojas y columnas esperadas. Lanza ValueError si no."""
    for hoja, columnas in COLUMNAS.items():
        if hoja not in hojas:
            raise ValueError(f"Falta la hoja '{hoja}' en el archivo de Excel.")
        faltan = [c for c in columnas if c not in hojas[hoja].columns]
        if faltan:
            raise ValueError(f"En la hoja '{hoja}' faltan las columnas: {', '.join(faltan)}.")
    return True


def cargar_datos(origen: str | Path | IO[bytes]) -> dict[str, pd.DataFrame]:
    """Lee todas las hojas del Excel (ruta o archivo subido) y las valida."""
    hojas = pd.read_excel(origen, sheet_name=None)
    validar_entradas(hojas)
    return hojas


def leer_parametros(df_parametros: pd.DataFrame) -> dict[str, float]:
    """Devuelve {'plazo_normal_h': 168, 'ventana_h': 24, 'umbral_nota': 1, 'nota_max': 100}."""
    valores = dict(zip(df_parametros["parametro"], df_parametros["valor"]))
    salida = {}
    for clave, nombre in PARAMETROS.items():
        if nombre not in valores:
            raise ValueError(f"Falta el parámetro '{nombre}' en la hoja Parametros.")
        salida[clave] = float(valores[nombre])
    return salida


def _corregir_atipicas(
    nota: pd.Series, nota_max: float, metodo: str
) -> tuple[pd.Series, pd.Series]:
    """Trata las notas mayores que nota_max (error de digitación)."""
    if metodo not in ATIPICOS:
        raise ValueError(f"atipicos debe ser uno de {ATIPICOS}.")
    nota = nota.copy()
    mala = nota > nota_max
    if metodo == "dividir10":
        # Parecen un decimal corrido (513 -> 51,3). Solo se acepta si queda en rango.
        candidata = nota[mala] / 10
        nota.loc[mala] = candidata.where(candidata <= nota_max)
    elif metodo == "descartar":
        nota.loc[mala] = float("nan")
    else:  # tope
        nota.loc[mala] = nota_max
    return nota, mala


def depurar_entregas(
    entregas: pd.DataFrame,
    tareas: pd.DataFrame,
    nota_max: float = 100.0,
    atipicos: str = "dividir10",
    faltantes: str = "excluir",
) -> pd.DataFrame:
    """Devuelve una fila por estudiante y tarea, lista para el modelo.

    Pasos:
    1. Se conserva solo el último intento (mayor número de intento).
    2. Se corrigen las notas mayores que nota_max según `atipicos`.
    3. Las notas faltantes se dejan vacías ('excluir') o se rellenan con la media
       del grupo en esa tarea ('imputar_media_grupo_tarea').
    4. Con Tareas se calculan T (plazo en horas), las horas desde la apertura,
       tau = horas / T y la marca de entrega tardía.

    Entradas: hojas Entregas y Tareas del Excel; nota_max en puntos.
    Salida: tabla con nota (puntos, 0 a 100), horas y plazo_h (h), tau (sin unidad) y tardia.
    """
    if faltantes not in FALTANTES:
        raise ValueError(f"faltantes debe ser uno de {FALTANTES}.")
    df = entregas.copy()
    df["fecha"] = pd.to_datetime(df["fecha_hora_entrega"])

    df = (
        df.sort_values(["grupo", "tarea", "estudiante", "intento"])
        .groupby(["grupo", "tarea", "estudiante"], as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    df["nota_original"] = df["nota"]
    df["nota"], df["nota_atipica"] = _corregir_atipicas(df["nota"], nota_max, atipicos)

    if faltantes == "imputar_media_grupo_tarea":
        media = df.groupby(["grupo", "tarea"])["nota"].transform("mean")
        df["nota"] = df["nota"].fillna(media)

    t = tareas.copy()
    t["apertura"] = pd.to_datetime(t["apertura"])
    t["cierre"] = pd.to_datetime(t["cierre"])
    t["plazo_h"] = (t["cierre"] - t["apertura"]).dt.total_seconds() / 3600
    df = df.merge(t, on=["grupo", "tarea"], how="left", validate="many_to_one")
    if df["apertura"].isna().any():
        raise ValueError("Hay entregas de una tarea o grupo que no está en la hoja Tareas.")

    df["horas"] = (df["fecha"] - df["apertura"]).dt.total_seconds() / 3600
    df["tau"] = df["horas"] / df["plazo_h"]
    df["tardia"] = df["fecha"] > df["cierre"]
    df["antes_apertura"] = df["horas"] < 0
    return df.drop(columns=["fecha_hora_entrega"])


def informe_depuracion(entregas: pd.DataFrame, depuradas: pd.DataFrame) -> dict[str, int]:
    """Conteos para la bitácora: qué se encontró y qué se hizo."""
    return {
        "registros_originales": len(entregas),
        "intentos_descartados": len(entregas) - len(depuradas),
        "entregas_depuradas": len(depuradas),
        "notas_mayores_que_100": int(depuradas["nota_atipica"].sum()),
        "notas_faltantes": int(depuradas["nota"].isna().sum()),
        "entregas_tardias": int(depuradas["tardia"].sum()),
        "entregas_antes_de_apertura": int(depuradas["antes_apertura"].sum()),
    }
