"""Limpieza de los conteos horarios.

Dos problemas que hay que tratar (como en datos reales):

1. "Cero de más": alguien escribió 120 en vez de 12. Lo detectamos
   porque el valor es más de 5 veces el promedio de sus horas vecinas.
2. Horas sin conteo (por lluvia): aparecen vacías (NaN).

Tratamiento: los valores sospechosos se marcan como vacíos y luego
todos los vacíos se rellenan por interpolación DENTRO DEL MISMO DÍA,
es decir, con una línea recta entre las horas vecinas de ese día.

Además, un valor solo se marca si es de al menos `minimo` aves (20 por
defecto). Con conteos tan pequeños, pasar de 1 a 5 aves es variación
normal y no un error de digitación (ver docs/bitacora_supuestos.md).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

Arreglo = NDArray[np.float64]


def promedio_vecinos(conteos: ArrayLike) -> Arreglo:
    """Promedio de la hora anterior y la siguiente para cada hora.

    En la primera y la última hora solo hay un vecino, y se usa ese.
    Si los vecinos están vacíos (NaN), se ignoran.
    Salida: arreglo del mismo tamaño (aves); NaN si no hay vecinos.
    """
    c = np.asarray(conteos, dtype=float)
    izquierda = np.concatenate(([np.nan], c[:-1]))
    derecha = np.concatenate((c[1:], [np.nan]))
    vecinos = np.vstack((izquierda, derecha))
    cuantos = np.sum(~np.isnan(vecinos), axis=0)
    suma = np.nansum(vecinos, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cuantos > 0, suma / cuantos, np.nan)


def detectar_cero_de_mas(
    conteos: ArrayLike, factor: float = 5.0, minimo: float = 20.0
) -> NDArray[np.bool_]:
    """Marca las horas cuyo conteo parece tener un cero de más.

    Criterio: conteo > factor * promedio de las horas vecinas
    y conteo >= minimo. Si los vecinos están vacíos no se marca,
    porque no hay con qué comparar.

    Entradas: conteos de un día (aves), el factor (por defecto 5) y el
    mínimo de aves para considerar un error (por defecto 20).
    Salida: arreglo de verdadero/falso; verdadero = sospechoso.
    """
    c = np.asarray(conteos, dtype=float)
    vecinos = promedio_vecinos(c)
    with np.errstate(invalid="ignore"):
        return ~np.isnan(vecinos) & (c >= minimo) & (c > factor * vecinos)


def interpolar_huecos(conteos: ArrayLike) -> Arreglo:
    """Rellena las horas vacías (NaN) con una línea recta dentro del día.

    Si el hueco está al principio o al final del día, se copia el valor
    de la hora más cercana. Si el día está completamente vacío, se
    devuelve igual (ese día se reporta aparte).
    Salida: conteos sin huecos (aves).
    """
    c = np.asarray(conteos, dtype=float).copy()
    validos = ~np.isnan(c)
    if validos.all() or not validos.any():
        return c
    posiciones = np.arange(c.size)
    c[~validos] = np.interp(posiciones[~validos], posiciones[validos], c[validos])
    return c


@dataclass(frozen=True)
class DiaLimpio:
    """Resultado de limpiar un día.

    conteos: conteos ya corregidos (aves).
    atipicos: cuántas horas tenían un cero de más.
    faltantes: cuántas horas estaban vacías desde el inicio.
    """

    conteos: Arreglo
    atipicos: int
    faltantes: int


def limpiar_dia(conteos: ArrayLike, factor: float = 5.0, minimo: float = 20.0) -> DiaLimpio:
    """Limpia los conteos de un día: quita ceros de más y rellena huecos.

    Pasos: (1) contar los huecos originales, (2) marcar los ceros de más
    como vacíos, (3) interpolar todos los vacíos dentro del día.
    """
    c = np.asarray(conteos, dtype=float).copy()
    faltantes = int(np.isnan(c).sum())
    sospechosos = detectar_cero_de_mas(c, factor, minimo)
    c[sospechosos] = np.nan
    return DiaLimpio(
        conteos=interpolar_huecos(c),
        atipicos=int(sospechosos.sum()),
        faltantes=faltantes,
    )


def limpiar_conteos(df: pd.DataFrame, factor: float = 5.0, minimo: float = 20.0) -> pd.DataFrame:
    """Limpia la tabla completa de conteos, día por día y especie por especie.

    Entrada: la tabla preparada por `datos.preparar_conteos` (columnas
        especie, dia, hora, aves_contadas, ...).
    Salida: una COPIA de la tabla con dos columnas nuevas:
        aves_limpias: conteo corregido (aves).
        correccion: "atípico", "faltante" o "" si no se tocó.
    La columna original `aves_contadas` se conserva sin cambios.
    """
    resultado = df.sort_values(["especie", "dia", "hora"]).copy()
    resultado["aves_limpias"] = np.nan
    resultado["correccion"] = ""
    for _, grupo in resultado.groupby(["especie", "dia"]):
        original = grupo["aves_contadas"].to_numpy(dtype=float)
        sospechosos = detectar_cero_de_mas(original, factor, minimo)
        dia = limpiar_dia(original, factor, minimo)
        resultado.loc[grupo.index, "aves_limpias"] = dia.conteos
        etiquetas = np.where(sospechosos, "atípico", np.where(np.isnan(original), "faltante", ""))
        resultado.loc[grupo.index, "correccion"] = etiquetas
    if resultado["aves_limpias"].isna().any():
        raise ValueError("Hay un día sin ningún conteo; no se puede interpolar dentro del día.")
    return resultado


def resumen_limpieza(limpio: pd.DataFrame) -> pd.DataFrame:
    """Tabla con cuántas horas se corrigieron por especie y tipo."""
    marcados = limpio[limpio["correccion"] != ""]
    return marcados.groupby(["especie", "correccion"]).size().unstack(fill_value=0).reset_index()
