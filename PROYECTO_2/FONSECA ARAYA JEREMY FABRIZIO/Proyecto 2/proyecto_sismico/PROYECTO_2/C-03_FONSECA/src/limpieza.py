"""Lectura del Excel original, validación y registro explícito de tratamientos."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

RUTA_BASE = Path(__file__).resolve().parents[1]
EXCEL = RUTA_BASE / "datos" / "P03_C-03_FONSECA.xlsx"

# Esquema y unidades del Diccionario entregado, no parámetros del cálculo.
ESQUEMA = {
    "Catalogo_sismos": {
        "id_sismo": "---",
        "fecha_hora": "fecha y hora",
        "magnitud_Mw": "Mw",
        "profundidad_km": "km",
        "distancia_sitio_km": "km",
    },
    "Acelerograma": {"tiempo_s": "s", "aceleracion_cm_s2": "cm/s²"},
    "Evento": {
        "evento": "---",
        "fecha": "fecha",
        "magnitud_Mw": "Mw",
        "distancia_km": "km",
        "estacion": "---",
        "segundos_previos_al_sismo": "s",
    },
    "Vulnerabilidad": {
        "magnitud_Mw": "Mw",
        "dano_actual_pct": "% del valor",
        "dano_opcion_A_pct": "% del valor",
        "dano_opcion_B_pct": "% del valor",
    },
    "Edificacion": {"parametro": "---", "valor": "ver columna unidad", "unidad": "---"},
    "Opciones_refuerzo": {
        "opcion": "---",
        "descripcion": "---",
        "costo_colones": "colones",
        "plazo_obra_meses": "meses",
    },
}
PARAMETROS = {
    "Valor de reposición del pabellón": "colones",
    "Ocupantes promedio (pacientes y personal)": "personas",
    "Tasa de descuento anual": "%",
    "Horizonte de evaluación": "años",
}


@dataclass
class BaseDatos:
    """Tablas de trabajo y bitácora. El archivo original nunca se sobrescribe."""

    hojas: dict[str, pd.DataFrame]
    incidencias: pd.DataFrame
    anos_catalogo: int
    m0: float
    resolucion_magnitud: float

    def parametro(self, nombre: str) -> float:
        """Obtiene un parámetro por nombre, con las unidades de Edificacion."""
        tabla = self.hojas["Edificacion"].set_index("parametro")
        return float(tabla.loc[nombre, "valor"])


def validar_esquema(hojas: dict[str, pd.DataFrame]) -> None:
    """Valida hojas, columnas y unidades declaradas; no modifica datos."""
    requeridas = set(ESQUEMA) | {"Diccionario"}
    if faltan := requeridas - hojas.keys():
        raise ValueError(f"Faltan hojas: {', '.join(sorted(faltan))}.")
    dic = hojas["Diccionario"]
    if not {"hoja", "columna", "descripcion", "unidad"} <= set(dic.columns):
        raise ValueError("El Diccionario debe indicar hoja, columna, descripcion y unidad.")
    if dic.duplicated(["hoja", "columna"]).any():
        raise ValueError("Hay definiciones duplicadas en Diccionario.")
    unidades = dic.set_index(["hoja", "columna"])["unidad"]
    for hoja, columnas in ESQUEMA.items():
        if hojas[hoja].empty or not columnas.keys() <= set(hojas[hoja].columns):
            raise ValueError(f"La hoja {hoja} está vacía o le faltan columnas requeridas.")
        for columna, unidad in columnas.items():
            if unidades.get((hoja, columna)) != unidad:
                raise ValueError(f"Unidad inválida: {hoja}.{columna} debe indicar {unidad}.")


def interpolar_faltantes(t: ArrayLike, a: ArrayLike) -> NDArray:
    """Interpola linealmente aceleración interna faltante (cm/s²) sobre tiempo (s).

    No extrapola extremos ni acepta tiempos faltantes, repetidos o desordenados.
    """
    t, a = np.asarray(t, dtype=float), np.asarray(a, dtype=float)
    if t.ndim != 1 or a.shape != t.shape or len(t) < 3:
        raise ValueError("El acelerograma necesita al menos tres pares tiempo-aceleración.")
    if not np.isfinite(t).all() or np.any(np.diff(t) <= 0):
        raise ValueError("Los tiempos deben ser finitos y estrictamente crecientes.")
    if np.isinf(a).any() or not np.isfinite(a[[0, -1]]).all():
        raise ValueError("No se extrapolan aceleraciones faltantes en los extremos ni infinitos.")
    validos = np.isfinite(a)
    return np.interp(t, t[validos], a[validos])


def corregir_linea_base(t: ArrayLike, a: ArrayLike, t0: float) -> NDArray:
    """Interpola a (cm/s²) y resta su media en t<t0; devuelve aceleración en cm/s².

    t y t0 en segundos. El promedio utiliza solo muestras previas al evento.
    """
    limpia = interpolar_faltantes(t, a)
    t = np.asarray(t, dtype=float)
    if not np.isfinite(t0) or not t[0] < t0 < t[-1]:
        raise ValueError("El inicio del sismo debe estar dentro del registro.")
    return limpia - limpia[t < t0].mean()


def leer_base(ruta: str | Path | BytesIO = EXCEL) -> BaseDatos:
    """Lee todas las hojas con pandas.read_excel y valida el esquema del profesor.

    Entrada: ruta o archivo en memoria. Salida: BaseDatos, sin alterar el Excel.
    """
    try:
        hojas = pd.read_excel(ruta, sheet_name=None)
    except Exception as exc:
        raise ValueError("No se pudo leer el Excel. Revisá que sea un .xlsx válido.") from exc
    validar_esquema(hojas)
    registros: list[dict] = []
    for nombre, tabla in hojas.items():
        for col in tabla:
            n = int(tabla[col].isna().sum())
            if n:
                permitido = (nombre, col) in {
                    ("Catalogo_sismos", "profundidad_km"),
                    ("Acelerograma", "aceleracion_cm_s2"),
                }
                if not permitido:
                    raise ValueError(f"Faltan {n} valores esenciales en {nombre}.{col}.")
                registros.append(
                    {
                        "hoja": nombre,
                        "variable": col,
                        "tipo": "Faltantes",
                        "cantidad": n,
                        "criterio": "Interpolación lineal interna"
                        if nombre == "Acelerograma"
                        else "Se conservan vacíos; no intervienen en b ni lambda",
                    }
                )
    catalogo = hojas["Catalogo_sismos"]
    try:
        catalogo["fecha_hora"] = pd.to_datetime(catalogo["fecha_hora"], errors="raise")
        for nombre in ["Catalogo_sismos", "Acelerograma", "Vulnerabilidad"]:
            for col in hojas[nombre]:
                if col != "fecha_hora":
                    hojas[nombre][col] = pd.to_numeric(hojas[nombre][col], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError("Hay fechas o números con un formato inválido.") from exc
    for nombre in ["Catalogo_sismos", "Acelerograma", "Vulnerabilidad"]:
        if np.isinf(hojas[nombre].select_dtypes(include="number").to_numpy()).any():
            raise ValueError(f"Hay valores infinitos en {nombre}.")
    if catalogo.id_sismo.duplicated().any() or catalogo.duplicated().any():
        raise ValueError("El catálogo contiene sismos duplicados; revisá su procedencia.")
    if (catalogo[["magnitud_Mw", "profundidad_km", "distancia_sitio_km"]] < 0).any().any():
        raise ValueError("Hay magnitudes, profundidades o distancias negativas.")
    for col in ["magnitud_Mw", "profundidad_km", "distancia_sitio_km"]:
        q1, q3 = catalogo[col].quantile([0.25, 0.75])
        mascara = (catalogo[col] < q1 - 1.5 * (q3 - q1)) | (catalogo[col] > q3 + 1.5 * (q3 - q1))
        registros.append(
            {
                "hoja": "Catalogo_sismos",
                "variable": col,
                "tipo": "Señal IQR",
                "cantidad": int(mascara.sum()),
                "criterio": "Conservar: cola sísmica plausible; señal estadística no prueba error",
            }
        )
    acel = hojas["Acelerograma"]
    interpolar_faltantes(acel.tiempo_s, acel.aceleracion_cm_s2)
    if not np.allclose(np.diff(acel.tiempo_s), np.diff(acel.tiempo_s)[0]):
        raise ValueError("El acelerograma debe tener paso uniforme para comparar con Simpson.")
    if (len(acel) - 1) % 2:
        raise ValueError("El acelerograma necesita un número par de intervalos para Simpson.")
    if not np.isclose(acel.tiempo_s.iloc[0], 0):
        raise ValueError("El acelerograma debe comenzar en t=0 segundos.")
    if len(hojas["Evento"]) != 1:
        raise ValueError("Evento debe contener exactamente un evento.")
    corregir_linea_base(
        acel.tiempo_s,
        acel.aceleracion_cm_s2,
        float(hojas["Evento"].segundos_previos_al_sismo.iloc[0]),
    )
    vulnerabilidad = hojas["Vulnerabilidad"]
    m = vulnerabilidad.magnitud_Mw.to_numpy()
    if len(m) < 3 or np.any(np.diff(m) <= 0) or (len(m) - 1) % 2:
        raise ValueError("Vulnerabilidad debe tener magnitudes crecientes y intervalos pares.")
    if not np.allclose(np.diff(m), np.diff(m)[0]):
        raise ValueError("La tabla de vulnerabilidad debe estar uniformemente espaciada.")
    danos = vulnerabilidad.iloc[:, 1:].to_numpy(dtype=float)
    if np.any((danos < 0) | (danos > 100)) or np.any(np.diff(danos, axis=0) < 0):
        raise ValueError("El daño debe estar entre 0 y 100 %, sin disminuir con la magnitud.")
    if np.any(danos[:, 1:] > danos[:, [0]]):
        raise ValueError("Un refuerzo no puede aumentar el daño respecto al escenario actual.")
    edi = hojas["Edificacion"]
    if edi.parametro.duplicated().any() or not PARAMETROS.keys() <= set(edi.parametro):
        raise ValueError("Faltan parámetros de Edificacion o están duplicados.")
    edi["valor"] = pd.to_numeric(edi.valor, errors="raise")
    for parametro, unidad in PARAMETROS.items():
        fila = edi[edi.parametro == parametro].iloc[0]
        if fila.unidad != unidad or not np.isfinite(fila.valor) or fila.valor < 0:
            raise ValueError(f"Valor o unidad inválidos para {parametro}.")
        if parametro != "Tasa de descuento anual" and fila.valor == 0:
            raise ValueError(f"{parametro} debe ser positivo.")
    opciones = hojas["Opciones_refuerzo"]
    if set(opciones.opcion) != {"Opción A", "Opción B"} or len(opciones) != 2:
        raise ValueError("Se esperan exactamente Opción A y Opción B, asociadas a sus curvas.")
    for col in ["costo_colones", "plazo_obra_meses"]:
        opciones[col] = pd.to_numeric(opciones[col], errors="raise")
        if not np.isfinite(opciones[col]).all() or (opciones[col] <= 0).any():
            raise ValueError(f"{col} debe ser positivo y finito.")
    mags = np.sort(catalogo.magnitud_Mw.unique())
    if len(mags) < 2:
        raise ValueError("Se necesitan al menos dos magnitudes distintas.")
    resolucion = float(np.min(np.diff(mags)))
    if not np.isclose(resolucion, 0.1):
        raise ValueError("Esta versión espera magnitudes redondeadas a 0,1 Mw, como el enunciado.")
    m0 = float(mags.min())
    if not np.isclose(m0, 3) or not np.allclose(m[[0, -1]], [5, 8]):
        raise ValueError("El modelo del enunciado requiere catálogo desde M=3 y daño en [5,8].")
    anos = int(catalogo.fecha_hora.dt.year.max() - catalogo.fecha_hora.dt.year.min() + 1)
    registros.append(
        {
            "hoja": "Acelerograma",
            "variable": "aceleracion_cm_s2",
            "tipo": "Picos",
            "cantidad": 0,
            "criterio": "No se recortan picos: representan el movimiento sísmico",
        }
    )
    return BaseDatos(hojas, pd.DataFrame(registros), anos, resolucion_magnitud=resolucion, m0=m0)
