"""Lectura, validación y limpieza de la base de cafeína.

Criterios (ver ``docs/bitacora_supuestos.md``):

* Faltantes interiores (t < 24 h): interpolación lineal en el tiempo,
  usando el punto ancla C(0) = 0. Para la regla del trapecio esto equivale
  a unir con una recta los vecinos válidos, de modo que no se inventa área.
* Faltantes en t = 24 h: extrapolación exponencial con la recta de ln C
  de la fase terminal (t >= 6 h), coherente con el modelo de eliminación.
* Atípicos: punto cuyo valor difiere más de ``FACTOR_ATIPICO`` veces de lo
  esperado por interpolación log-lineal entre sus vecinos válidos. Se
  marcan uno a uno (el peor primero) y se tratan como faltantes.
* Los valores imputados no se usan para estimar k.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import FACTOR_ATIPICO, RANGO_TR_MS, T_TERMINAL_H

# ---------------------------------------------------------------------------
# Estructura esperada del Excel
# ---------------------------------------------------------------------------
# Hojas y columnas obligatorias, y nombre/unidad de cada parámetro del problema.
# Si alguien sube otra base desde la aplicación, se valida contra esto.

ESQUEMA: dict[str, list[str]] = {
    "Concentraciones": ["voluntario", "tiempo_h", "concentracion_mg_L"],
    "Voluntarios": [
        "voluntario",
        "sexo",
        "edad",
        "peso_kg",
        "fuma",
        "anticonceptivo_hormonal",
        "tazas_cafe_habituales_dia",
    ],
    "Pruebas_atencion": ["voluntario", "tiempo_h", "tiempo_reaccion_ms"],
    "Bebidas": ["bebida", "cafeina_mg", "volumen_ml"],
    "Planes": ["plan", "hora_toma", "bebida"],
    "Parametros": ["parametro", "valor", "unidad"],
}

PARAMETROS_ESPERADOS: dict[str, tuple[str, str]] = {
    "Dosis de la prueba": ("dosis_mg", "mg"),
    "Constante de absorción típica": ("ka", "1/h"),
    "Umbral de efecto en la atención": ("c_efecto", "mg/L"),
    "Umbral para no afectar el sueño": ("c_sueno", "mg/L"),
    "Hora de acostarse": ("hora_dormir", "hora"),
    "Máximo diario recomendado": ("max_diario_mg", "mg"),
    "Inicio de la jornada de estudio": ("inicio", "hora"),
    "Fin de la jornada de estudio": ("fin", "hora"),
}


# ---------------------------------------------------------------------------
# Lectura y validación
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Parametros:
    """Parámetros del problema leídos de la hoja ``Parametros``.

    Atributos (unidades): dosis_mg (mg), ka (1/h), c_efecto (mg/L),
    c_sueno (mg/L), hora_dormir (h del día), max_diario_mg (mg),
    inicio y fin de la jornada (h del día).
    """

    dosis_mg: float
    ka: float
    c_efecto: float
    c_sueno: float
    hora_dormir: float
    max_diario_mg: float
    inicio: float
    fin: float

    def con_cambios(self, **cambios: float) -> Parametros:
        """Devuelve una copia con algunos parámetros modificados."""
        valores = {**self.__dict__, **cambios}
        return Parametros(**valores)


def validar_base(hojas: dict[str, pd.DataFrame]) -> None:
    """Verifica que existan las hojas y columnas esperadas.

    Entradas: diccionario hoja -> DataFrame (``pd.read_excel(sheet_name=None)``).
    Salidas: ninguna; lanza ``ValueError`` con un mensaje claro si falta algo.
    """
    faltan_hojas = [h for h in ESQUEMA if h not in hojas]
    if faltan_hojas:
        raise ValueError(f"Faltan hojas en el Excel: {', '.join(faltan_hojas)}")
    for hoja, columnas in ESQUEMA.items():
        faltan = [c for c in columnas if c not in hojas[hoja].columns]
        if faltan:
            raise ValueError(f"La hoja '{hoja}' no tiene las columnas: {', '.join(faltan)}")
    for hoja, col in [("Concentraciones", "concentracion_mg_L"), ("Bebidas", "cafeina_mg")]:
        if not pd.api.types.is_numeric_dtype(hojas[hoja][col]):
            raise ValueError(f"La columna '{col}' de '{hoja}' debe ser numérica")


def leer_base(ruta: str | Path) -> dict[str, pd.DataFrame]:
    """Lee el Excel entregado sin modificarlo y valida su estructura.

    Entradas: ruta al archivo .xlsx (o un objeto tipo archivo).
    Salidas: diccionario hoja -> DataFrame.
    """
    hojas = pd.read_excel(ruta, sheet_name=None)
    validar_base(hojas)
    return hojas


def leer_parametros(tabla: pd.DataFrame) -> Parametros:
    """Convierte la hoja ``Parametros`` en un objeto ``Parametros``.

    Verifica que cada parámetro exista y tenga la unidad esperada.
    Entradas: DataFrame con columnas parametro, valor, unidad.
    Salidas: ``Parametros``.
    """
    indexada = tabla.set_index("parametro")
    valores: dict[str, float] = {}
    for nombre, (clave, unidad) in PARAMETROS_ESPERADOS.items():
        if nombre not in indexada.index:
            raise ValueError(f"Falta el parámetro '{nombre}' en la hoja Parametros")
        fila = indexada.loc[nombre]
        if str(fila["unidad"]).strip() != unidad:
            raise ValueError(f"Unidad de '{nombre}' es '{fila['unidad']}', se esperaba '{unidad}'")
        valores[clave] = float(fila["valor"])
    return Parametros(**valores)


def a_horas_decimales(valor: object) -> float:
    """Convierte una hora del día ('08:00', time o número) a horas decimales."""
    if isinstance(valor, dt.time):
        return valor.hour + valor.minute / 60
    if isinstance(valor, (int, float, np.number)):
        return float(valor)
    horas, minutos = str(valor).strip().split(":")[:2]
    return int(horas) + int(minutos) / 60


# ---------------------------------------------------------------------------
# Concentraciones: atípicos, faltantes e imputación
# ---------------------------------------------------------------------------


def _esperado_vecinos(t: np.ndarray, c: np.ndarray, i: int) -> float:
    """Valor esperado en t[i] por interpolación log-lineal de vecinos válidos."""
    validos = ~np.isnan(c) & (c > 0)
    izq = np.flatnonzero(validos[:i])
    der = np.flatnonzero(validos[i + 1 :]) + i + 1
    if izq.size == 0 or der.size == 0:
        return np.nan
    a, b = izq[-1], der[0]
    peso = (t[i] - t[a]) / (t[b] - t[a])
    return float(np.exp((1 - peso) * np.log(c[a]) + peso * np.log(c[b])))


def detectar_atipicos(t: np.ndarray, c: np.ndarray, factor: float = FACTOR_ATIPICO) -> np.ndarray:
    """Marca puntos interiores que se apartan de sus vecinos más de ``factor``.

    Entradas: tiempos t (h) y concentraciones c (mg/L) de un voluntario,
    ordenados; ``factor`` adimensional (> 1).
    Salidas: arreglo booleano, True en los atípicos. Itera marcando el peor
    punto primero para que un atípico no contamine a sus vecinos.
    """
    c = c.astype(float).copy()
    atipico = np.zeros(c.size, dtype=bool)
    while True:
        # Desvío de cada punto interior respecto a lo esperado por sus vecinos (en escala ln)
        desvios = np.full(c.size, 0.0)
        for i in range(1, c.size - 1):
            if np.isnan(c[i]) or c[i] <= 0:
                continue
            esperado = _esperado_vecinos(t, c, i)
            if not np.isnan(esperado):
                desvios[i] = abs(np.log(c[i] / esperado))
        # Si el peor no supera el factor, terminamos; si no, se marca y se repite sin él
        peor = int(np.argmax(desvios))
        if desvios[peor] <= np.log(factor):
            return atipico
        atipico[peor] = True
        c[peor] = np.nan


def recta_terminal(t: np.ndarray, c: np.ndarray, t_terminal: float) -> tuple[float, float]:
    """Pendiente e intercepto de ln C contra t en la fase terminal.

    Entradas: t (h), c (mg/L) con posibles NaN; t_terminal (h).
    Salidas: (pendiente en 1/h, intercepto en ln(mg/L)).
    """
    usar = (t >= t_terminal) & ~np.isnan(c) & (c > 0)
    x, y = t[usar], np.log(c[usar])
    if x.size < 2:
        raise ValueError("Se necesitan al menos dos puntos válidos en la fase terminal")
    pendiente = np.sum((x - x.mean()) * (y - y.mean())) / np.sum((x - x.mean()) ** 2)
    return float(pendiente), float(y.mean() - pendiente * x.mean())


def imputar_voluntario(
    t: np.ndarray, c: np.ndarray, t_terminal: float = T_TERMINAL_H
) -> np.ndarray:
    """Completa los NaN de un perfil según los criterios del módulo.

    Entradas: t (h) ordenado y c (mg/L) con NaN en faltantes/atípicos.
    Salidas: arreglo c sin NaN (mg/L).
    """
    c = c.astype(float).copy()
    # 1) Falta el valor de 24 h: se prolonga la recta de ln C (decaimiento exponencial)
    ultimo = np.isnan(c) & (t == t.max())
    if ultimo.any():
        pendiente, intercepto = recta_terminal(t, c, t_terminal)
        c[ultimo] = np.exp(intercepto + pendiente * t[ultimo])
    # 2) Faltantes interiores: recta entre vecinos válidos, con el ancla C(0) = 0
    faltan = np.isnan(c)
    if faltan.any():
        t_ok = np.concatenate([[0.0], t[~faltan]])
        c_ok = np.concatenate([[0.0], c[~faltan]])
        c[faltan] = np.interp(t[faltan], t_ok, c_ok)
    return c


def limpiar_concentraciones(
    conc: pd.DataFrame, factor: float = FACTOR_ATIPICO
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Detecta y trata faltantes y atípicos de la hoja ``Concentraciones``.

    Entradas: DataFrame original; ``factor`` de detección de atípicos.
    Salidas: (datos limpios con columnas extra ``estado`` y
    ``valor_original``; bitácora con cada registro tratado).
    """
    # 1) Por voluntario: detectar atípicos, tratarlos como faltantes e imputar
    partes = []
    for _, grupo in conc.sort_values(["voluntario", "tiempo_h"]).groupby("voluntario"):
        t = grupo["tiempo_h"].to_numpy(float)
        c = grupo["concentracion_mg_L"].to_numpy(float)
        faltante = np.isnan(c)
        atipico = detectar_atipicos(t, c, factor)
        c_trabajo = np.where(atipico, np.nan, c)
        grupo = grupo.assign(
            valor_original=c,
            concentracion_mg_L=imputar_voluntario(t, c_trabajo),
            estado=np.select([faltante, atipico], ["faltante", "atípico"], "observado"),
        )
        partes.append(grupo)
    # 2) Bitácora: cada valor tratado, su valor original, el final y el método usado
    limpio = pd.concat(partes, ignore_index=True)
    tratados = limpio[limpio["estado"] != "observado"].copy()
    tratados["tratamiento"] = np.where(
        tratados["tiempo_h"] == limpio["tiempo_h"].max(),
        "extrapolación exponencial (fase terminal)",
        "interpolación lineal en el tiempo",
    )
    bitacora = tratados[
        ["voluntario", "tiempo_h", "estado", "valor_original", "concentracion_mg_L", "tratamiento"]
    ].rename(columns={"concentracion_mg_L": "valor_final"})
    return limpio, bitacora.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Pruebas de atención y resumen de calidad
# ---------------------------------------------------------------------------


def revisar_pruebas(pruebas: pd.DataFrame) -> pd.DataFrame:
    """Marca tiempos de reacción faltantes o fuera del rango plausible.

    Entradas: hoja ``Pruebas_atencion``.
    Salidas: copia con columna booleana ``valido``.
    """
    bajo, alto = RANGO_TR_MS
    tr = pruebas["tiempo_reaccion_ms"]
    return pruebas.assign(valido=tr.between(bajo, alto) & tr.notna())


def unir_atencion(pruebas: pd.DataFrame, conc_limpio: pd.DataFrame) -> pd.DataFrame:
    """Empareja cada prueba de atención con la concentración del mismo momento.

    En t = 0 (antes de la toma) se asume C = 0 mg/L.
    Entradas: pruebas revisadas y concentraciones limpias.
    Salidas: DataFrame con tiempo_reaccion_ms y concentracion_mg_L.
    """
    unido = pruebas.merge(
        conc_limpio[["voluntario", "tiempo_h", "concentracion_mg_L"]],
        on=["voluntario", "tiempo_h"],
        how="left",
    )
    unido.loc[unido["tiempo_h"] == 0, "concentracion_mg_L"] = 0.0
    # Mejora = tiempo sin cafeína (t = 0) menos el tiempo actual; positivo = reacciona más rápido
    basal = unido[unido["tiempo_h"] == 0].set_index("voluntario")["tiempo_reaccion_ms"]
    unido["mejora_ms"] = unido["voluntario"].map(basal) - unido["tiempo_reaccion_ms"]
    return unido[unido["valido"] & unido["concentracion_mg_L"].notna()].reset_index(drop=True)


def resumen_calidad(hojas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Tabla de registros, faltantes y rango de cada columna numérica.

    Entradas: diccionario de hojas originales.
    Salidas: DataFrame (hoja, columna, registros, faltantes, mínimo, máximo).
    """
    filas = []
    for hoja in ["Concentraciones", "Voluntarios", "Pruebas_atencion"]:
        datos = hojas[hoja]
        for col in datos.select_dtypes("number").columns:
            filas.append(
                {
                    "hoja": hoja,
                    "columna": col,
                    "registros": len(datos),
                    "faltantes": int(datos[col].isna().sum()),
                    "minimo": datos[col].min(),
                    "maximo": datos[col].max(),
                }
            )
    return pd.DataFrame(filas)
