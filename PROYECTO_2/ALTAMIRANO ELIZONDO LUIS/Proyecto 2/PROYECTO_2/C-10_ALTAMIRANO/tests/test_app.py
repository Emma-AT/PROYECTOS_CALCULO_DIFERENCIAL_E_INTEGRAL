from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(
    not (RAIZ / "datos" / "P05_C-10_ALTAMIRANO.xlsx").exists(), reason="falta el Excel"
)
def test_la_app_arranca_y_muestra_la_decision_sin_errores():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert "G03" in at.subheader[0].value  # estrategia recomendada
    # Cambiar de grupo y de tarea no rompe la app
    at.selectbox[0].select("G04").run()
    at.selectbox[1].select("T3").run()
    assert not at.exception
