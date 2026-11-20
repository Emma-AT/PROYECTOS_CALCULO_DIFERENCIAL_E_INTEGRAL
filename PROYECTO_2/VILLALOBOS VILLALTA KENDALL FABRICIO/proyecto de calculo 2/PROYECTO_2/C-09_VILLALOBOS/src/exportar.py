"""Exporta tablas a CSV y Excel listos para abrir con Excel o Numbers en español.

* CSV: columnas separadas por punto y coma y coma decimal (lo que espera
  Excel con configuración regional en español), UTF-8 con BOM para las tildes.
* Excel (.xlsx): una hoja por tabla, encabezado en negrita sobre verde claro,
  fila de encabezado fija, filtros y ancho de columnas ajustado al contenido.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

DECIMALES = 4
"""Decimales con que se exportan los números (suficiente para leer y verificar)."""

# ---------------------------------------------------------------------------
# Preparación común
# ---------------------------------------------------------------------------


def preparar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Deja la tabla plana: índice con nombre como columna y números redondeados.

    Entradas: cualquier DataFrame de resultados (puede tener índice con nombre
    o columnas de dos niveles, como el resumen por grupo).
    Salidas: copia con índice 0..n−1 y columnas de un solo nivel.
    """
    salida = tabla.copy()
    if isinstance(salida.columns, pd.MultiIndex):
        salida.columns = ["_".join(str(p) for p in c if str(p)) for c in salida.columns]
    if any(n is not None for n in salida.index.names):
        salida = salida.reset_index()
    else:
        salida = salida.reset_index(drop=True)
    return salida.round(DECIMALES)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------


def tabla_csv(tabla: pd.DataFrame) -> bytes:
    """CSV con ';' entre columnas y ',' decimal, en UTF-8 con BOM (bytes)."""
    texto = preparar(tabla).to_csv(index=False, sep=";", decimal=",")
    return texto.encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------


def _dar_formato(hoja: Worksheet) -> None:
    """Encabezado destacado y fijo, filtros y ancho de cada columna."""
    relleno = PatternFill("solid", fgColor="E3F1E3")
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="1B5E20")
        celda.fill = relleno
        celda.alignment = Alignment(vertical="center", wrap_text=True)
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    for columna in hoja.columns:
        largo = max(len(str(c.value)) if c.value is not None else 0 for c in columna)
        hoja.column_dimensions[get_column_letter(columna[0].column)].width = min(largo + 2, 60)


def libro_excel(tablas: dict[str, pd.DataFrame]) -> bytes:
    """Libro .xlsx con una hoja por tabla (nombre de hoja = clave, máx. 31 caracteres)."""
    memoria = io.BytesIO()
    with pd.ExcelWriter(memoria, engine="openpyxl") as libro:
        for nombre, tabla in tablas.items():
            hoja = nombre[:31]
            preparar(tabla).to_excel(libro, sheet_name=hoja, index=False)
            _dar_formato(libro.sheets[hoja])
    return memoria.getvalue()


def guardar(tablas: dict[str, pd.DataFrame], carpeta: Path, libro: Path) -> list[str]:
    """Escribe cada tabla como CSV en ``carpeta`` y todas juntas en el Excel ``libro``.

    Salidas: nombres de los archivos escritos.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    nombres = []
    for nombre, tabla in tablas.items():
        (carpeta / f"{nombre}.csv").write_bytes(tabla_csv(tabla))
        nombres.append(f"{nombre}.csv")
    libro.write_bytes(libro_excel(tablas))
    nombres.append(libro.name)
    return nombres
