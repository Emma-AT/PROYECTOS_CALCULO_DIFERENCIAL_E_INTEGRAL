"""Agrega la insignia del workflow real cuando el estudiante conoce su fork."""

import argparse
import re

from src.limpieza import RUTA_BASE


def main() -> None:
    """Recibe usuario y repositorio de GitHub; actualiza únicamente el README local."""
    parser = argparse.ArgumentParser()
    parser.add_argument("usuario")
    parser.add_argument("repositorio")
    args = parser.parse_args()
    if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in [args.usuario, args.repositorio]):
        parser.error("Usá nombres de GitHub, sin URL ni espacios.")
    url = f"https://github.com/{args.usuario}/{args.repositorio}/actions/workflows/pruebas.yml"
    insignia = f"[![Pruebas]({url}/badge.svg)]({url})"
    ruta = RUTA_BASE / "README.md"
    texto = ruta.read_text(encoding="utf-8")
    texto = re.sub(r"\[!\[Pruebas\].*\n", "", texto)
    lineas = texto.splitlines()
    lineas.insert(2, insignia)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("Insignia vinculada. Confirmá el estado real en GitHub Actions.")


if __name__ == "__main__":
    main()
