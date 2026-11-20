"""Explicación en lenguaje sencillo de los resultados del modelo.

Reglas de este módulo:
1. Todas las cifras las calcula el código del proyecto (modelo.py, escenarios.py).
   La IA solo las redacta; nunca calcula nada.
2. Si la IA devuelve una cifra que no sale de los datos, se descarta su texto.
3. Si no hay clave, no hay internet o la API falla, se usa texto_basico(),
   que no depende de ningún servicio externo.

Entrada esperada (la arma la app con sus propios resultados):
    {
      "recomendada": "G03",
      "umbral_puntos": 1,
      "grupos": {
        "G03": {"estrategia": "Entrega parcial obligatoria", "nota_media": 78.3,
                "ip": 0.70, "horas_docentes": 6.2},
        ...
      }
    }
"""

from __future__ import annotations

import os
import re

import requests

URL = "https://api.groq.com/openai/v1/chat/completions"
# Revisa en la consola de Groq que este identificador siga vigente.
MODELO_DEFECTO = "openai/gpt-oss-120b"

CAMPOS = ("estrategia", "nota_media", "ip", "horas_docentes")

INSTRUCCION = (
    "Eres un analista que le explica resultados a una coordinadora académica "
    "que no sabe matemática. Escribe en español, en un solo párrafo de máximo "
    "100 palabras. Usa únicamente las cifras de los datos y escríbelas tal "
    "como aparecen. No inventes cifras, no calcules nada nuevo y no hagas "
    "afirmaciones causales: los grupos no se asignaron al azar."
)


def validar_indicadores(ind: dict) -> None:
    """Falla con un mensaje claro si falta algo en los datos de entrada."""
    for clave in ("recomendada", "grupos"):
        if clave not in ind:
            raise ValueError(f"Falta '{clave}' en los indicadores.")
    if ind["recomendada"] not in ind["grupos"]:
        raise ValueError("'recomendada' no está entre los grupos.")
    for g, datos in ind["grupos"].items():
        faltan = [c for c in CAMPOS if c not in datos]
        if faltan:
            raise ValueError(f"El grupo {g} no tiene: {', '.join(faltan)}.")


def texto_basico(ind: dict) -> str:
    """Texto armado solo con el código del proyecto (sin IA)."""
    validar_indicadores(ind)
    g = ind["recomendada"]
    d = ind["grupos"][g]
    texto = (
        f"La estrategia recomendada es «{d['estrategia']}» ({g}): "
        f"nota media de {d['nota_media']:.1f}, índice de procrastinación de "
        f"{d['ip']:.2f} y {d['horas_docentes']:.1f} horas docentes por tarea."
    )
    otros = [(x, v) for x, v in ind["grupos"].items() if x != g]
    if otros:
        x, v = max(otros, key=lambda p: p[1]["nota_media"])
        dif = d["nota_media"] - v["nota_media"]
        texto += (
            f" La siguiente mejor es «{v['estrategia']}» ({x}), con nota media "
            f"de {v['nota_media']:.1f} (diferencia de {dif:.1f} puntos)."
        )
    return texto


# --- Guardia contra cifras inventadas --------------------------------------


def _numeros_en(obj: object) -> list[float]:
    """Todos los números que aparecen en los datos (y sus versiones en %)."""
    if isinstance(obj, bool):
        return []
    if isinstance(obj, (int, float)):
        return [float(obj), float(obj) * 100]
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in _numeros_en(v)]
    if isinstance(obj, (list, tuple)):
        return [n for v in obj for n in _numeros_en(v)]
    return []


def cifras_validas(texto: str, ind: dict) -> bool:
    """True si cada cifra del texto es un redondeo de una cifra de los datos."""
    permitidas = _numeros_en(ind)
    sin_ids = re.sub(r"G\d+", "", texto)  # G03 es un nombre, no una cifra
    for token in re.findall(r"\d+(?:[.,]\d+)?", sin_ids):
        token = token.replace(",", ".")
        decimales = len(token.split(".")[1]) if "." in token else 0
        n = float(token)
        tolerancia = 0.5 * 10 ** (-decimales) + 1e-9
        if not any(abs(n - p) <= tolerancia for p in permitidas):
            return False
    return True


# --- Llamada a la API -------------------------------------------------------


def _pedir_a_la_api(ind: dict, clave: str, modelo: str, timeout: float) -> str:
    import json

    cuerpo = {
        "model": modelo,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": INSTRUCCION},
            {"role": "user", "content": json.dumps(ind, ensure_ascii=False)},
        ],
    }
    r = requests.post(
        URL,
        headers={"Authorization": f"Bearer {clave}"},
        json=cuerpo,
        timeout=timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def explicar(
    ind: dict, clave: str | None = None, modelo: str | None = None, timeout: float = 15
) -> tuple[str, str]:
    """Devuelve (texto, origen). origen es 'ia' o 'local'."""
    validar_indicadores(ind)
    clave = clave or os.environ.get("GROQ_API_KEY")
    if not clave:
        return texto_basico(ind), "local"
    modelo = modelo or os.environ.get("GROQ_MODEL", MODELO_DEFECTO)
    try:
        texto = _pedir_a_la_api(ind, clave, modelo, timeout)
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return texto_basico(ind), "local"
    if not texto or not cifras_validas(texto, ind):
        return texto_basico(ind), "local"
    return texto, "ia"
