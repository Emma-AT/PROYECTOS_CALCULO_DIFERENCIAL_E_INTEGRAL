"""Lectura y revisión del Excel entregado.

Aquí solo se LEE el archivo; nunca se modifica el original.
Antes de usar los datos se revisa que estén las hojas y columnas
esperadas, y si falta algo se muestra un mensaje claro.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import IO

import pandas as pd

# Carpeta del proyecto (sirve para no escribir rutas absolutas).
RAIZ = Path(__file__).resolve().parent.parent
RUTA_POR_DEFECTO = RAIZ / "datos" / "P06_C-06_MONGE.xlsx"

# Hojas y columnas que deben existir en la base.
COLUMNAS_ESPERADAS: dict[str, list[str]] = {
    "Conteo_horario": ["fecha", "hora_inicio", "especie", "aves_contadas", "condicion"],
    "Parametros": ["parametro", "valor", "unidad"],
}

# Cómo se llama cada parámetro en la hoja "Parametros" (empieza con...)
# y el nombre corto que usamos en el código, con su unidad esperada.
PARAMETROS: dict[str, tuple[str, str]] = {
    "hi": ("Hora de inicio del vuelo", "hora"),
    "hf": ("Hora de fin del vuelo", "hora"),
    "dias_campana": ("Días de la campaña", "días"),
    "horas_turno": ("Horas por turno", "horas"),
    "inicio_tradicional": ("Inicio de la campaña tradicional", "días"),
}


@dataclass(frozen=True)
class Parametros:
    """Parámetros del problema leídos del Excel.

    hi, hf: hora de inicio y fin del vuelo migratorio (h, ej. 6.2 = 6:12).
    dias_campana: duración de la campaña de voluntariado L (días).
    horas_turno: duración de un turno de observación (h).
    inicio_tradicional: día en que empieza la campaña tradicional
        (días desde el 20 de septiembre).
    """

    hi: float
    hf: float
    dias_campana: int
    horas_turno: int
    inicio_tradicional: float


@dataclass(frozen=True)
class Base:
    """La base completa: conteos por hora y parámetros."""

    conteos: pd.DataFrame
    parametros: Parametros


def leer_hojas(ruta: str | Path | IO[bytes]) -> dict[str, pd.DataFrame]:
    """Lee todas las hojas del Excel y revisa que tengan lo necesario.

    Entrada: ruta del archivo (o un archivo subido en la app web).
    Salida: diccionario {nombre de hoja: tabla}.
    Lanza ValueError con un mensaje claro si falta una hoja o columna.
    """
    hojas = pd.read_excel(ruta, sheet_name=None)
    for hoja, columnas in COLUMNAS_ESPERADAS.items():
        if hoja not in hojas:
            raise ValueError(f"Falta la hoja '{hoja}' en el Excel.")
        faltan = [c for c in columnas if c not in hojas[hoja].columns]
        if faltan:
            raise ValueError(f"En la hoja '{hoja}' faltan las columnas: {faltan}.")
    return hojas


def leer_parametros(tabla: pd.DataFrame) -> Parametros:
    """Busca cada parámetro por su nombre y revisa su unidad.

    Entrada: la hoja "Parametros".
    Salida: un objeto `Parametros`.
    """
    valores: dict[str, float] = {}
    for corto, (inicio_nombre, unidad) in PARAMETROS.items():
        fila = tabla[tabla["parametro"].str.startswith(inicio_nombre)]
        if fila.empty:
            raise ValueError(f"No se encontró el parámetro '{inicio_nombre}...'.")
        if str(fila["unidad"].iloc[0]).strip() != unidad:
            raise ValueError(f"El parámetro '{inicio_nombre}' debe estar en '{unidad}'.")
        valores[corto] = float(fila["valor"].iloc[0])
    if not valores["hi"] < valores["hf"]:
        raise ValueError("La hora de inicio del vuelo debe ser menor que la de fin.")
    return Parametros(
        hi=valores["hi"],
        hf=valores["hf"],
        dias_campana=int(valores["dias_campana"]),
        horas_turno=int(valores["horas_turno"]),
        inicio_tradicional=valores["inicio_tradicional"],
    )


def preparar_conteos(tabla: pd.DataFrame) -> pd.DataFrame:
    """Convierte las columnas de texto a números útiles.

    Agrega:
        hora: hora de inicio del bloque como número (ej. "07:00" -> 7.0).
        dia: días desde el primer día de la temporada (0, 1, 2, ...).
    No cambia ningún conteo.
    """
    df = tabla.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])
    partes = df["hora_inicio"].astype(str).str.split(":", expand=True).astype(int)
    df["hora"] = partes[0] + partes[1] / 60
    df["dia"] = (df["fecha"] - df["fecha"].min()).dt.days
    if (df["aves_contadas"] < 0).any():
        raise ValueError("Hay conteos negativos en la base.")
    return df.sort_values(["especie", "dia", "hora"]).reset_index(drop=True)


def cargar_base(ruta: str | Path | IO[bytes] = RUTA_POR_DEFECTO) -> Base:
    """Lee el Excel completo y lo deja listo para trabajar.

    Entrada: ruta del Excel (por defecto, el de la carpeta datos/).
    Salida: un objeto `Base` con los conteos y los parámetros.
    """
    hojas = leer_hojas(ruta)
    return Base(
        conteos=preparar_conteos(hojas["Conteo_horario"]),
        parametros=leer_parametros(hojas["Parametros"]),
    )
