"""Lectura, validación y limpieza de la base P09_C-01_AGUIRRE.xlsx."""

import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNAS = {
    "Viento_horario": ["fecha_hora", "velocidad_m_s", "temperatura_C", "produccion_planta_MWh"],
    "Curvas_potencia": ["velocidad_m_s", "actual_V47_kW", "opcion_A_kW", "opcion_B_kW"],
    "Opciones": [
        "opcion",
        "turbinas",
        "potencia_nominal_kW",
        "diametro_rotor_m",
        "altura_buje_m",
        "inversion_colones",
        "mantenimiento_anual_colones",
    ],
    "Parametros": ["parametro", "valor", "unidad"],
}

# clave interna -> texto que aparece en la columna "parametro" (sin tildes)
CLAVES_PARAMETROS = {
    "h_ref_m": "anemometro",
    "alpha": "cizalladura",
    "k_anual": "forma k",
    "c_anual_ms": "escala c",
    "presion_kpa": "presion",
    "r_aire": "constante",
    "rho_ref": "densidad de referencia",
    "precio": "precio",
    "tasa_pct": "tasa de descuento",
    "vida_anios": "vida util",
}


def _normalizar(texto: str) -> str:
    """Devuelve el texto en minúsculas y sin tildes."""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    return "".join(ch for ch in descompuesto if not unicodedata.combining(ch)).lower()


def cargar_datos(fuente) -> dict[str, pd.DataFrame]:
    """Lee todas las hojas del Excel y valida hojas y columnas.

    Entradas: fuente, ruta (str | Path) o archivo en memoria (BytesIO).
    Salidas: diccionario {nombre de hoja: DataFrame}.
    Errores: FileNotFoundError si no existe; ValueError si falta una hoja o columna.
    """
    if isinstance(fuente, (str, Path)) and not Path(fuente).exists():
        raise FileNotFoundError(f"No existe el archivo: {fuente}")
    hojas = pd.read_excel(fuente, sheet_name=None)
    for hoja, columnas in COLUMNAS.items():
        if hoja not in hojas:
            raise ValueError(f"Falta la hoja '{hoja}' en el Excel.")
        faltan = set(columnas) - set(hojas[hoja].columns)
        if faltan:
            raise ValueError(f"En la hoja '{hoja}' faltan las columnas {sorted(faltan)}.")
    return hojas


def leer_parametros(df: pd.DataFrame) -> dict[str, float]:
    """Convierte la hoja Parametros en un diccionario {clave: valor}.

    Unidades: las de la columna 'unidad' (m, kPa, J/(kg·K), kg/m³, colones/kWh, %, años).
    """
    nombres = df["parametro"].map(_normalizar)
    params = {}
    for clave, texto in CLAVES_PARAMETROS.items():
        fila = df[nombres.str.contains(texto, regex=False)]
        if fila.empty:
            raise ValueError(f"No se encontró el parámetro que contiene '{texto}'.")
        params[clave] = float(fila["valor"].iloc[0])
    return params


def limpiar_viento(df: pd.DataFrame, v_max: float = 35.0, salto_max: float = 8.0) -> pd.DataFrame:
    """Marca y trata faltantes y picos del anemómetro.

    Criterio: una hora es "pico" si v > v_max (m/s) o si se aleja más de salto_max
    (m/s) de la mediana móvil de 5 horas. Picos y faltantes se reemplazan por
    interpolación lineal en el tiempo. La producción faltante (MWh) se interpola igual.
    Salidas: copia con columnas v_limpia_m_s, prod_limpia_MWh y estado_viento.
    """
    out = df.copy()
    out["fecha_hora"] = pd.to_datetime(out["fecha_hora"])
    v = out["velocidad_m_s"].astype(float)
    mediana = v.rolling(5, center=True, min_periods=3).median()
    pico = (v > v_max) | ((v - mediana).abs() > salto_max)
    out["estado_viento"] = np.select([v.isna(), pico], ["faltante", "pico"], default="ok")
    out["v_limpia_m_s"] = v.mask(pico).interpolate(limit_direction="both")
    out["prod_limpia_MWh"] = out["produccion_planta_MWh"].interpolate(limit_direction="both")
    return out


def densidad_aire(temperatura_c, presion_pa: float, r_aire: float):
    """Densidad del aire por gas ideal: rho = p / (R · T_K).

    Entradas: temperatura en °C, presión en Pa, R en J/(kg·K). Salida: kg/m³.
    """
    return presion_pa / (r_aire * (np.asarray(temperatura_c, dtype=float) + 273.15))
