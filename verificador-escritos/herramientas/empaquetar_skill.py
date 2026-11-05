#!/usr/bin/env python3
"""Empaqueta la skill en un único ZIP listo para subir a Claude.

Uso: python3 herramientas/empaquetar_skill.py
Resultado: ../descargas/verificador-escritos-pa.zip
"""
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ.parent / "descargas" / "verificador-escritos-pa.zip"
CARPETA = "verificador-escritos-pa"
INCLUIR = ["SKILL.md", "referencias", "motor", "herramientas/extraer_citas.py"]
EXCLUIR_NOMBRES = {"__pycache__", "test_motor.py"}


def archivos():
    for entrada in INCLUIR:
        ruta = RAIZ / entrada
        candidatos = [ruta] if ruta.is_file() else sorted(p for p in ruta.rglob("*") if p.is_file())
        for p in candidatos:
            if not EXCLUIR_NOMBRES.intersection(p.relative_to(RAIZ).parts) and p.suffix != ".pyc":
                yield p


def main() -> int:
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as z:
        for p in archivos():
            z.write(p, f"{CARPETA}/{p.relative_to(RAIZ).as_posix()}")
            n += 1
    print(f"Generado: {DESTINO} ({n} archivos, {DESTINO.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
