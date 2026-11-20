"""Recorre la app con la API de agente de Streamlit y reporta excepciones (uso local)."""

import json
import sys
import urllib.request
from collections import Counter

URL = "http://127.0.0.1:8765/_stcore/agent/interact"


def pedir(cuerpo: dict) -> dict:
    req = urllib.request.Request(
        URL, json.dumps(cuerpo).encode(), {"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:800])
        raise


def recorrer(nodo, tipos: Counter, problemas: list, textos: list) -> None:
    if isinstance(nodo, dict):
        t = nodo.get("type")
        if isinstance(t, str):
            tipos[t] += 1
            if t in ("exception",):
                problemas.append(json.dumps(nodo, ensure_ascii=False)[:1500])
            if t in ("success", "warning", "error", "info", "alert"):
                textos.append(json.dumps(nodo.get("props", nodo), ensure_ascii=False)[:300])
        for v in nodo.values():
            recorrer(v, tipos, problemas, textos)
    elif isinstance(nodo, list):
        for v in nodo:
            recorrer(v, tipos, problemas, textos)


def resumen(nombre: str, r: dict) -> int:
    tipos, problemas, textos = Counter(), [], []
    recorrer(r.get("tree", r), tipos, problemas, textos)
    print(f"== {nombre}: status={r.get('status')} elementos={dict(tipos.most_common(12))}")
    for p in problemas:
        print("   EXCEPCION:", p)
    for t in textos[:4]:
        print("   aviso:", t)
    return len(problemas) + (r.get("status") == "error")


errores = 0
r = pedir({})
sid = r["session_id"]
if "-v" in sys.argv:
    print(json.dumps(r, ensure_ascii=False)[:4000])
print("paginas:", r.get("pages"))
errores += resumen("inicio", r)
for pagina in ["simulador", "planes", "escenarios", "metodo", "glosario"]:
    errores += resumen(pagina, pedir({"session_id": sid, "page": pagina}))
r = pedir({"session_id": sid, "page": "simulador"})
print("acciones simulador:", json.dumps(r.get("actions"), ensure_ascii=False)[:800])
boton = next(
    (a["key"] for a in r.get("actions", []) if isinstance(a, dict) and a.get("type") == "button"),
    None,
)
if boton:
    errores += resumen("simulador · recomendado", pedir({"session_id": sid, "trigger": {"key": boton}}))
for tipo in ["Rápida", "Lenta"]:
    pedir({"session_id": sid, "widget_state": {"tipo": tipo, "n_bebidas": 4}})
    errores += resumen(
        f"simulador · {tipo} · 4 bebidas · 5 días",
        pedir(
            {
                "session_id": sid,
                "widget_state": {"dias": 5, "bebida_3": "Energética grande · 160 mg", "hora_3": "21:00"},
            }
        ),
    )
r = pedir({"session_id": sid, "page": "metodo"})
for s in ["El modelo", "Verificación", "Quién elimina más rápido", "Cafeína y atención"]:
    errores += resumen(f"metodo · {s}", pedir({"session_id": sid, "widget_state": {"seccion": s}}))
print("ERRORES:", errores)
