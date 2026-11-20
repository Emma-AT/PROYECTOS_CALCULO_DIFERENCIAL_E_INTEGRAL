"""Verificación de la interfaz con controles y escenario de descuento cero."""

from streamlit.testing.v1 import AppTest

from src.limpieza import RUTA_BASE


def test_app_y_controles() -> None:
    """Carga, cambia b para modificar la decisión y permite r=0 sin excepciones."""
    app = AppTest.from_file(str(RUTA_BASE / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert "Opción A" in app.success[0].value
    app.number_input[0].set_value(app.number_input[0].value + 0.1).run()
    assert not app.exception
    assert "ninguna opción" in app.warning[0].value
    app.number_input[1].set_value(0).run()
    assert not app.exception
