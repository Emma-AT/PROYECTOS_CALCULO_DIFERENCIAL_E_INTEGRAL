"""Punto de entrada de la app en Streamlit Community Cloud.

La carpeta del proyecto tiene espacios en el nombre y Streamlit Cloud no
logra instalar las dependencias desde una ruta con espacios. Este archivo
solo abre la carpeta real del proyecto y ejecuta su app.py.
"""

import os
import runpy
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "PROYECTO_2" / "MONGE NAVARRO ALLISON GEORGINA"
sys.path.insert(0, str(CARPETA))
os.chdir(CARPETA)
runpy.run_path(str(CARPETA / "app.py"), run_name="__main__")