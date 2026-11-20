"""Configuración compartida de pytest.

El análisis completo se calcula una sola vez por sesión y se reutiliza en
todas las pruebas que reciben el argumento ``analisis``.
"""

import pytest

from src.pipeline import AnalisisCafeina


@pytest.fixture(scope="session")
def analisis() -> AnalisisCafeina:
    """Análisis del Excel del proyecto con todas las tablas ya calculadas."""
    a = AnalisisCafeina.desde_excel()
    a.calcular_tablas()
    return a
