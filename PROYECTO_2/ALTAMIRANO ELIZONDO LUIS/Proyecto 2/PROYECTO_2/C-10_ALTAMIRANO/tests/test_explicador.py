import pytest
import requests

from src import explicador as ex

IND = {
    "recomendada": "G03",
    "umbral_puntos": 1,
    "grupos": {
        "G03": {
            "estrategia": "Entrega parcial obligatoria",
            "nota_media": 78.32,
            "ip": 0.70,
            "horas_docentes": 6.2,
        },
        "G04": {
            "estrategia": "Plazo ampliado 48 h",
            "nota_media": 72.76,
            "ip": 0.81,
            "horas_docentes": 1.0,
        },
    },
}


class RespuestaFalsa:
    def __init__(self, texto):
        self.texto = texto

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self.texto}}]}


def simular(monkeypatch, texto=None, error=None):
    def falso(*args, **kwargs):
        if error:
            raise error
        return RespuestaFalsa(texto)

    monkeypatch.setattr(ex.requests, "post", falso)


def test_sin_clave_usa_texto_local(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    texto, origen = ex.explicar(IND)
    assert origen == "local"
    assert "G03" in texto and "78.3" in texto


def test_con_clave_y_texto_valido_usa_ia(monkeypatch):
    simular(monkeypatch, "G03 logra una nota media de 78.3 frente a 72.8 de G04.")
    texto, origen = ex.explicar(IND, clave="clave-falsa")
    assert origen == "ia"
    assert "78.3" in texto


def test_cifra_inventada_se_descarta(monkeypatch):
    simular(monkeypatch, "G03 mejora la nota en 15 puntos.")
    texto, origen = ex.explicar(IND, clave="clave-falsa")
    assert origen == "local"
    assert "15" not in texto


def test_porcentaje_derivado_de_los_datos_es_valido():
    # ip = 0.70 puede decirse como 70 %
    assert ex.cifras_validas("El índice es de 70 %.", IND)
    assert not ex.cifras_validas("El índice es de 55 %.", IND)


def test_nombres_de_grupo_no_cuentan_como_cifras():
    assert ex.cifras_validas("G03 y G04 son los grupos comparados.", IND)


def test_falla_de_red_usa_texto_local(monkeypatch):
    simular(monkeypatch, error=requests.ConnectionError("sin internet"))
    _texto, origen = ex.explicar(IND, clave="clave-falsa")
    assert origen == "local"


def test_respuesta_vacia_usa_texto_local(monkeypatch):
    simular(monkeypatch, "")
    _, origen = ex.explicar(IND, clave="clave-falsa")
    assert origen == "local"


def test_indicadores_incompletos_dan_error_claro():
    malos = {"recomendada": "G03", "grupos": {"G03": {"estrategia": "x"}}}
    with pytest.raises(ValueError, match="no tiene"):
        ex.explicar(malos)
