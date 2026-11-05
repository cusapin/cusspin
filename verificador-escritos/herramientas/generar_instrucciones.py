#!/usr/bin/env python3
"""Genera instrucciones-proyecto.md a partir de SKILL.md (sin el encabezado YAML).

Uso: python3 herramientas/generar_instrucciones.py
Ejecutar cada vez que cambie SKILL.md y volver a pegar el resultado en las instrucciones
del proyecto de Claude.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AVISO = ("<!-- Archivo generado desde SKILL.md por herramientas/generar_instrucciones.py. "
         "No editar a mano: edite SKILL.md y regenere. -->\n\n")


def main() -> int:
    origen = (RAIZ / "SKILL.md").read_text(encoding="utf-8")
    cuerpo = re.sub(r"\A---\n.*?\n---\n+", "", origen, count=1, flags=re.S)
    if cuerpo == origen:
        print("SKILL.md no tiene encabezado YAML; se copia completo.", file=sys.stderr)
    (RAIZ / "instrucciones-proyecto.md").write_text(AVISO + cuerpo, encoding="utf-8")
    print(f"Generado: {RAIZ / 'instrucciones-proyecto.md'} ({len(cuerpo):,} caracteres)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
