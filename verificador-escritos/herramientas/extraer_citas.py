#!/usr/bin/env python3
"""Inventario mecánico de afirmaciones verificables en un escrito jurídico panameño.

Produce el punto de partida de los Pasos 2 y 4 del protocolo (SKILL.md):

* inventario de citas normativas, jurisprudenciales y de tratados, con la fuente
  sugerida para su verificación y estado inicial SIN VERIFICAR;
* fechas, montos, cédulas y números de resolución;
* alertas de coherencia detectables sin interpretar el texto (numeración de hechos,
  fechas imposibles o futuras, montos en letras distintos de los montos en cifras,
  una misma cédula atribuida a nombres distintos);
* alertas de régimen procesal (Código Judicial frente a la Ley 402 de 2023);
* posibles instrucciones dirigidas a un modelo de IA ocultas en el material.

La herramienta NO verifica nada contra fuentes: solo extrae. Todo lo que reporta
debe confirmarse contra fuente primaria. Sin dependencias externas: lee .txt, .md y
.docx; para .pdf usa `pdftotext` si está instalado.

Uso:
    python3 extraer_citas.py ESCRITO [--formato md|json] [--fecha-referencia AAAA-MM-DD]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.etree import ElementTree

# ---------------------------------------------------------------------------
# Lectura del documento
# ---------------------------------------------------------------------------

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def leer_docx(ruta: Path) -> str:
    """Extrae el texto de un .docx, incluido el texto oculto o de color blanco."""
    with zipfile.ZipFile(ruta) as z:
        partes = [n for n in z.namelist()
                  if re.fullmatch(r"word/(document|footnotes|endnotes|comments|header\d*|footer\d*)\.xml", n)]
        bloques = []
        for nombre in sorted(partes, key=lambda n: (n != "word/document.xml", n)):
            raiz = ElementTree.fromstring(z.read(nombre))
            for p in raiz.iter(f"{_W_NS}p"):
                texto = "".join(t.text or "" for t in p.iter(f"{_W_NS}t"))
                if texto.strip():
                    bloques.append(texto)
    return "\n".join(bloques)


def leer_pdf(ruta: Path) -> str:
    if not shutil.which("pdftotext"):
        raise RuntimeError("Para leer PDF instale 'pdftotext' (poppler-utils) o convierta el escrito a .txt/.docx.")
    salida = subprocess.run(["pdftotext", "-layout", str(ruta), "-"],
                            capture_output=True, text=True, check=True)
    return salida.stdout


def leer_documento(ruta: Path) -> str:
    sufijo = ruta.suffix.lower()
    if sufijo == ".docx":
        return leer_docx(ruta)
    if sufijo == ".pdf":
        return leer_pdf(ruta)
    return ruta.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class Hallazgo:
    tipo: str
    texto: str
    linea: int
    fuente_sugerida: str = ""
    estado: str = "SIN VERIFICAR"
    nota: str = ""


@dataclass
class Informe:
    citas: list[Hallazgo] = field(default_factory=list)
    datos: list[Hallazgo] = field(default_factory=list)
    alertas: list[Hallazgo] = field(default_factory=list)
    inyeccion: list[Hallazgo] = field(default_factory=list)


def _linea(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


def _norm(s: str) -> str:
    """Minúsculas sin tildes, para comparar."""
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# Patrones
# ---------------------------------------------------------------------------

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}

_NUM = r"(?:N\.?\s?[°ºo]\.?\s*|No\.\s*|núm(?:ero)?\.?\s*)?"
_FECHA_TXT = r"\d{1,2}\s+de\s+(?:" + "|".join(MESES) + r")\s+de\s+\d{4}"

FUENTE_GACETA = "Gaceta Oficial (gacetaoficial.gob.pa) e Infojurídica (infojuridica.procuraduria-admon.gob.pa)"
FUENTE_FALLOS = "Registro Judicial / Órgano Judicial (organojudicial.gob.pa); confirmar texto íntegro del fallo"
FUENTE_TRATADOS = "Ley aprobatoria en Gaceta Oficial; estado de ratificación y reservas en el depositario (ONU/OEA)"

PATRONES_CITAS: list[tuple[str, re.Pattern[str], str]] = [
    ("ley", re.compile(rf"\bLey\s+{_NUM}\d+(?:-[A-Z])?(?:\s+de\s+(?:{_FECHA_TXT}|\d{{4}}))?", re.I), FUENTE_GACETA),
    ("decreto", re.compile(
        rf"\bDecreto(?:\s+(?:Ejecutivo|de\s+Gabinete|Ley))?\s+{_NUM}\d+(?:-[A-Z]+)?"
        rf"(?:\s+de\s+(?:{_FECHA_TXT}|\d{{4}}))?", re.I), FUENTE_GACETA),
    ("resolucion", re.compile(
        rf"\bResoluci[oó]n\s+(?:Administrativa\s+|Ministerial\s+)?{_NUM}[\w./-]*\d[\w./-]*"
        rf"(?:\s+de\s+(?:{_FECHA_TXT}|\d{{4}}))?", re.I),
     "Expediente administrativo y copia autenticada con constancia de notificación"),
    ("acto_legislativo", re.compile(rf"\bActo\s+Legislativo\s+{_NUM}\d+(?:\s+de\s+(?:{_FECHA_TXT}|\d{{4}}))?", re.I),
     FUENTE_GACETA),
    ("fallo", re.compile(
        r"\b(?:Sentencia|Fallo|Resoluci[oó]n\s+judicial|Auto)\s+(?:de\s+)?" + _FECHA_TXT +
        r"(?:\s*,?\s*(?:del?\s+)?(?:Pleno|Sala\s+(?:Primera|Segunda|Tercera|Cuarta|Civil|Penal|Contencioso[- ]Administrativ[ao]|Laboral))"
        r"(?:\s+de\s+la\s+Corte\s+Suprema\s+de\s+Justicia)?)?", re.I), FUENTE_FALLOS),
    ("fallo", re.compile(r"\bRegistro\s+Judicial(?:\s+de\s+\w+\s+de\s+\d{4})?(?:\s*,?\s*p[áa]g(?:ina)?s?\.?\s*\d+)?", re.I),
     FUENTE_FALLOS),
    ("fallo_cidh", re.compile(r"\bCaso\s+[A-ZÁÉÍÓÚÑ][\w\s.,]{2,80}?\s+vs\.?\s+[A-ZÁÉÍÓÚ][a-záéíóúñ]+", re.U),
     "Corte IDH (corteidh.or.cr): sentencia, serie, fecha y párrafo"),
    ("tratado", re.compile(
        r"\b(?:Convenci[oó]n|Pacto|Convenio|Protocolo|Declaraci[oó]n|Tratado)\s+"
        r"(?:(?:de|del|sobre|para|contra|relativ[oa]\s+a|Americana|Internacional|Interamericana|Universal|Facultativo|N\.?\s?[°º]?\s*\d+|n[úu]m(?:ero)?\.?\s*\d+|la|los|las|el|y|\d+|[A-ZÁÉÍÓÚÑ][\w-]+)\s*){1,14}",
        re.U), FUENTE_TRATADOS),
    ("constitucion", re.compile(r"\bConstituci[oó]n\s+(?:Pol[íi]tica|Nacional)(?:\s+de\s+la\s+Rep[úu]blica(?:\s+de\s+Panam[áa])?)?", re.I),
     "Texto único de la Constitución en Gaceta Oficial; verificar actos reformatorios"),
]

# Artículos: se capta "artículo(s) N[, N y N][, numeral X]" y, si sigue inmediatamente
# "de la / del" + un cuerpo normativo reconocible, se completa con él.
RE_ARTICULO = re.compile(
    r"\b(?:art[íi]culos?|arts?\.)\s+\d+(?:-[A-Z])?(?:\s*(?:,|y|al|a)\s*\d+(?:-[A-Z])?)*"
    r"(?:\s*,?\s*(?:numeral|num\.|literal|lit\.|ordinal|par[áa]grafo)\s+[\w]+)*", re.I)
RE_CUERPO = re.compile(
    r"\s*,?\s+(?:del?|de\s+la|de\s+los|de\s+las)\s+("
    rf"Ley\s+{_NUM}\d+(?:-[A-Z])?(?:\s+de\s+(?:{_FECHA_TXT}|\d{{4}}))?"
    rf"|Decreto(?:\s+(?:Ejecutivo|de\s+Gabinete|Ley))?\s+{_NUM}\d+(?:-[A-Z]+)?(?:\s+de\s+(?:{_FECHA_TXT}|\d{{4}}))?"
    r"|Constituci[oó]n(?:\s+(?:Pol[íi]tica|Nacional))?(?:\s+de\s+la\s+Rep[úu]blica(?:\s+de\s+Panam[áa])?)?"
    r"|C[óo]digo(?:\s+(?:de\s+(?:la\s+)?)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}"
    r"|Texto\s+[ÚU]nico[\w\s]{0,40}?(?=[,.;)]|$)"
    r"|(?:Convenci[oó]n|Pacto|Convenio|Protocolo)(?:\s+(?:(?:de|del|sobre|para|contra|la|los|las|el|y)\b|N\.?\s?[°º]?\s*\d+|\d+|[A-ZÁÉÍÓÚÑ][\w-]+)){1,12}"
    r")", re.I)

RE_FECHA_TXT = re.compile(r"\b(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")\s+de\s+(\d{4})\b", re.I)
RE_FECHA_NUM = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
RE_MONTO = re.compile(r"(?:B/\.|USD|US\$|\$)\s?\d{1,3}(?:[,.]\d{3})*(?:[.,]\d{2})?|\b\d{1,3}(?:[,.]\d{3})*(?:[.,]\d{2})?\s+balboas\b", re.I)
RE_CEDULA = re.compile(r"\b(?:\d{1,2}|PE|E|N|PI|AV|[1-9]{1,2}PI|[1-9]{1,2}AV)-\d{1,4}-\d{1,6}\b")
RE_EXPEDIENTE = re.compile(r"\b(?:Expediente|Exp\.|Entrada)\s*(?:N\.?\s?[°º]\s*)?[\w-]*\d[\w/-]*", re.I)
RE_CITA_TEXTUAL = re.compile(r"[\"“«]([^\"”»]{40,})[\"”»]", re.S)

ORDINALES = ["primero", "segundo", "tercero", "cuarto", "quinto", "sexto", "septimo", "octavo", "noveno",
             "decimo", "undecimo", "duodecimo", "decimotercero", "decimocuarto", "decimoquinto",
             "decimosexto", "decimoseptimo", "decimoctavo", "decimonoveno", "vigesimo"]
_ORDINAL_ALIAS = {"decimo primero": "undecimo", "decimoprimero": "undecimo", "decimo segundo": "duodecimo",
                  "decimosegundo": "duodecimo", "setimo": "septimo", "decimo tercero": "decimotercero",
                  "decimo cuarto": "decimocuarto", "decimo quinto": "decimoquinto"}
RE_HECHO = re.compile(
    r"^\s*(?:HECHO\s+)?(" + "|".join(ORDINALES + list(_ORDINAL_ALIAS)) + r")\s*[:.\-–—]",
    re.I | re.M)
RE_HECHO_NUM = re.compile(r"^\s*(?:HECHO\s+)(\d+)\s*[:.\-–—]", re.I | re.M)

PATRONES_INYECCION = [
    r"ignor[ae]\w*\s+(?:las\s+|todas\s+las\s+)?(?:instrucciones|reglas|indicaciones)",
    r"(?:inteligencia\s+artificial|modelo\s+de\s+lenguaje|\bIA\b|\bAI\b|asistente\s+(?:virtual|de\s+IA)|chatgpt|claude|gemini|copilot)",
    r"(?:no\s+(?:reportes|menciones|se[ñn]ales))\s+(?:este|esta|estos|ning[úu]n)",
    r"(?:conclu[iy][re]\w*|declar[ae]\w*)\s+que\s+(?:el\s+escrito|la\s+demanda|este\s+documento)\s+(?:es|est[áa])\s+(?:correct|perfect|impecable|sin\s+errores)",
    r"\b(?:system\s+prompt|prompt|jailbreak|ignore\s+(?:all\s+)?previous)\b",
    r"\bcomp[óo]rtate\s+como\b",
]
RE_INVISIBLES = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")

# ---------------------------------------------------------------------------
# Números en letras (español) para cotejar montos
# ---------------------------------------------------------------------------

_UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
             "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
             "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17,
             "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiun": 21, "veintiuno": 21,
             "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
             "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28,
             "veintinueve": 29, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
             "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100,
             "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300,
             "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500, "quinientas": 500,
             "seiscientos": 600, "seiscientas": 600, "setecientos": 700, "setecientas": 700,
             "ochocientos": 800, "ochocientas": 800, "novecientos": 900, "novecientas": 900}


def letras_a_numero(frase: str) -> int | None:
    """Convierte 'cincuenta mil trescientos' en 50300. Devuelve None si no reconoce."""
    palabras = [p for p in re.split(r"[\s-]+", _norm(frase)) if p and p != "y"]
    if not palabras:
        return None
    total, actual, visto = 0, 0, False
    for p in palabras:
        if p in _UNIDADES:
            actual += _UNIDADES[p]
            visto = True
        elif p == "mil":
            total += (actual or 1) * 1000
            actual, visto = 0, True
        elif p in ("millon", "millones"):
            total += (actual or 1) * 1_000_000
            actual, visto = 0, True
        else:
            return None
    return total + actual if visto else None


_PAL_NUM = "|".join(sorted(list(_UNIDADES) + ["mil", "millon", "millones", "y"], key=len, reverse=True))
RE_MONTO_LETRAS = re.compile(
    rf"\b((?:(?:{_PAL_NUM})[\s-]+)*(?:{_PAL_NUM}))\s+balboas(?:\s+con\s+(\d{{1,2}})/100)?"
    rf"\s*\(\s*(?:B/\.|USD|US\$|\$)\s?([\d.,]+)\s*\)", re.I)


def _cifra_a_float(s: str) -> float | None:
    s = s.strip()
    if re.fullmatch(r"\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?", s) or re.fullmatch(r"\d+(?:\.\d{1,2})?", s):
        return float(s.replace(",", ""))
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?", s):
        return float(s.replace(".", "").replace(",", "."))
    return None


# ---------------------------------------------------------------------------
# Análisis
# ---------------------------------------------------------------------------

def extraer_citas(texto: str, informe: Informe) -> None:
    vistos: set[tuple[str, int, int]] = set()
    for tipo, patron, fuente in PATRONES_CITAS:
        for m in patron.finditer(texto):
            clave = (tipo, m.start(), m.end())
            # Evita duplicar un fragmento ya contenido en otra cita del mismo tipo.
            if any(t == tipo and s <= m.start() and m.end() <= e for t, s, e in vistos):
                continue
            vistos.add(clave)
            frag = re.sub(r"\s+", " ", m.group(0)).strip(" ,.;")
            frag = re.sub(r"(?:\s+(?:de|del|la|los|las|el|y|sobre|para|contra))+$", "", frag, flags=re.I)
            informe.citas.append(Hallazgo(tipo, frag, _linea(texto, m.start()), fuente))

    for m in RE_ARTICULO.finditer(texto):
        fin = m.end()
        cuerpo = RE_CUERPO.match(texto, fin)
        frag = texto[m.start(): cuerpo.end() if cuerpo else fin]
        frag = re.sub(r"\s+", " ", frag).strip(" ,.;")
        nota = "" if cuerpo else "No se identificó el cuerpo normativo a continuación: verificar a qué norma pertenece"
        fuente = FUENTE_GACETA
        if cuerpo and re.match(r"(?:Convenci|Pacto|Convenio|Protocolo)", cuerpo.group(1), re.I):
            fuente = FUENTE_TRATADOS
        informe.citas.append(Hallazgo("articulo", frag, _linea(texto, m.start()), fuente, nota=nota))

    for m in RE_CITA_TEXTUAL.finditer(texto):
        frag = re.sub(r"\s+", " ", m.group(1)).strip()
        informe.citas.append(Hallazgo(
            "cita_textual", (frag[:160] + "…") if len(frag) > 160 else frag, _linea(texto, m.start()),
            "Cotejar literalmente con el texto primario de la norma o fallo",
            nota="Verificar que sea literal y no paráfrasis"))


def _fecha_valida(d: int, mth: int, y: int) -> dt.date | None:
    try:
        return dt.date(y, mth, d)
    except ValueError:
        return None


def extraer_datos(texto: str, informe: Informe, hoy: dt.date) -> None:
    for m in RE_FECHA_TXT.finditer(texto):
        d, mes, y = int(m.group(1)), MESES[m.group(2).lower()], int(m.group(3))
        linea = _linea(texto, m.start())
        informe.datos.append(Hallazgo("fecha", m.group(0), linea, "Documento de soporte"))
        f = _fecha_valida(d, mes, y)
        if f is None:
            informe.alertas.append(Hallazgo("fecha_imposible", m.group(0), linea, estado="ALERTA",
                                            nota="La fecha no existe en el calendario"))
        elif f > hoy:
            informe.alertas.append(Hallazgo("fecha_futura", m.group(0), linea, estado="ALERTA",
                                            nota=f"Posterior a la fecha de referencia {hoy.isoformat()}"))
    for m in RE_FECHA_NUM.finditer(texto):
        d, mes, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        linea = _linea(texto, m.start())
        informe.datos.append(Hallazgo("fecha", m.group(0), linea, "Documento de soporte"))
        if _fecha_valida(d, mes, y) is None:
            informe.alertas.append(Hallazgo("fecha_imposible", m.group(0), linea, estado="ALERTA",
                                            nota="Fecha inexistente (se asume formato día/mes/año)"))

    for m in RE_MONTO.finditer(texto):
        informe.datos.append(Hallazgo("monto", m.group(0), _linea(texto, m.start()),
                                      "Cotejar con hechos, pretensión, cuantía y anexos"))
    for m in RE_EXPEDIENTE.finditer(texto):
        informe.datos.append(Hallazgo("expediente", m.group(0), _linea(texto, m.start()), "Expediente / sistema de gestión"))

    # Cédulas: una misma cédula asociada a nombres distintos.
    asociaciones: dict[str, set[str]] = {}
    primera_linea: dict[str, int] = {}
    for m in RE_CEDULA.finditer(texto):
        ced = m.group(0)
        primera_linea.setdefault(ced, _linea(texto, m.start()))
        informe.datos.append(Hallazgo("cedula", ced, _linea(texto, m.start()), "Copia de la cédula / Tribunal Electoral"))
        previo = texto[max(0, m.start() - 160):m.start()]
        nombres = re.findall(r"((?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+){1,4}[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*,?\s*(?:[\w\s,]{0,60})?"
                             r"(?:c[ée]dula|C\.I\.P\.|cip)", previo)
        if nombres:
            asociaciones.setdefault(ced, set()).add(nombres[-1].strip())
    for ced, nombres in asociaciones.items():
        if len(nombres) > 1:
            informe.alertas.append(Hallazgo("cedula_inconsistente", ced, primera_linea[ced], estado="ALERTA",
                                            nota="Asociada a nombres distintos: " + "; ".join(sorted(nombres))))


RE_RESOLUCION_FECHA = re.compile(
    rf"\bResoluci[oó]n\s+(?:Administrativa\s+|Ministerial\s+)?{_NUM}([\w./-]*\d[\w./-]*)\s+de\s+({_FECHA_TXT})", re.I)


def verificar_identidad_actos(texto: str, informe: Informe) -> None:
    """Control H-09: un mismo número de resolución no puede aparecer con fechas distintas."""
    fechas: dict[str, dict[str, int]] = {}
    for m in RE_RESOLUCION_FECHA.finditer(texto):
        fechas.setdefault(m.group(1).upper(), {}).setdefault(_norm(m.group(2)), _linea(texto, m.start()))
    for numero, variantes in fechas.items():
        if len(variantes) > 1:
            informe.alertas.append(Hallazgo(
                "acto_identificado_distinto", f"Resolución {numero}", min(variantes.values()), estado="ALERTA",
                nota="Aparece con fechas distintas: " + "; ".join(
                    f"{f} (línea {ln})" for f, ln in sorted(variantes.items(), key=lambda x: x[1]))))


def verificar_montos_en_letras(texto: str, informe: Informe) -> None:
    for m in RE_MONTO_LETRAS.finditer(texto):
        valor_letras = letras_a_numero(m.group(1))
        centavos = int(m.group(2)) / 100 if m.group(2) else 0.0
        valor_cifra = _cifra_a_float(m.group(3))
        if valor_letras is None or valor_cifra is None:
            continue
        if abs((valor_letras + centavos) - valor_cifra) > 0.005:
            informe.alertas.append(Hallazgo(
                "monto_letras_vs_cifras", re.sub(r"\s+", " ", m.group(0)), _linea(texto, m.start()),
                estado="ALERTA",
                nota=f"En letras: {valor_letras + centavos:,.2f}; en cifras: {valor_cifra:,.2f}"))


def verificar_numeracion_hechos(texto: str, informe: Informe) -> None:
    encontrados = []
    for m in RE_HECHO.finditer(texto):
        clave = _ORDINAL_ALIAS.get(_norm(m.group(1)), _norm(m.group(1)))
        if clave in ORDINALES:
            encontrados.append((ORDINALES.index(clave) + 1, m.group(1), _linea(texto, m.start())))
    for m in RE_HECHO_NUM.finditer(texto):
        encontrados.append((int(m.group(1)), m.group(1), _linea(texto, m.start())))
    encontrados.sort(key=lambda x: x[2])
    if not encontrados:
        return
    # Una enumeración nueva (otra sección) puede reiniciar en 1.
    esperado = None
    for n, etiqueta, linea in encontrados:
        if n == 1:
            esperado = 2
            continue
        if esperado is not None and n != esperado:
            informe.alertas.append(Hallazgo(
                "numeracion_hechos", etiqueta, linea, estado="ALERTA",
                nota=f"Se esperaba el ordinal n.º {esperado} y aparece el n.º {n} (salto o duplicado)"))
        esperado = n + 1


def alertas_de_regimen(texto: str, informe: Informe) -> None:
    t = _norm(texto)
    if "codigo judicial" in t:
        civil = re.search(r"\b(?:proceso|demanda|juicio)\s+(?:ordinari[oa]|ejecutiv[oa]|civil|sumari[oa])\b", t)
        menciona_402 = re.search(r"ley\s+(?:n\.?\s?[°o]\s*)?402", t) or "codigo procesal civil" in t
        if civil and not menciona_402:
            informe.alertas.append(Hallazgo(
                "regimen_procesal", "Código Judicial en materia civil", _linea(texto, civil.start()),
                estado="ALERTA",
                nota="Verificar si el proceso se rige por el Código Procesal Civil (Ley 402 de 2023, "
                     "vigencia integral en octubre de 2025) según su fecha de inicio y las normas transitorias"))


def detectar_inyeccion(texto: str, informe: Informe) -> None:
    lineas_vistas: set[int] = set()
    for patron in PATRONES_INYECCION:
        for m in re.finditer(patron, texto, re.I):
            if _linea(texto, m.start()) in lineas_vistas:
                continue
            lineas_vistas.add(_linea(texto, m.start()))
            ini = texto.rfind("\n", 0, m.start()) + 1
            fin = texto.find("\n", m.end())
            linea_txt = texto[ini: fin if fin != -1 else len(texto)].strip()
            informe.inyeccion.append(Hallazgo(
                "posible_instruccion_al_modelo", linea_txt[:200], _linea(texto, m.start()), estado="REVISAR",
                nota="Puede ser contenido legítimo; si es una orden al revisor o al modelo, no se obedece"))
    for m in RE_INVISIBLES.finditer(texto):
        informe.inyeccion.append(Hallazgo(
            "caracter_invisible", f"U+{ord(m.group(0)):04X}", _linea(texto, m.start()), estado="REVISAR",
            nota="Carácter invisible: puede ocultar texto o alterar comparaciones"))


def analizar(texto: str, hoy: dt.date | None = None) -> Informe:
    hoy = hoy or dt.date.today()
    informe = Informe()
    extraer_citas(texto, informe)
    extraer_datos(texto, informe, hoy)
    verificar_montos_en_letras(texto, informe)
    verificar_identidad_actos(texto, informe)
    verificar_numeracion_hechos(texto, informe)
    alertas_de_regimen(texto, informe)
    detectar_inyeccion(texto, informe)
    for lista in (informe.citas, informe.datos, informe.alertas, informe.inyeccion):
        lista.sort(key=lambda h: h.linea)
    return informe


# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------

def _celda(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def a_markdown(informe: Informe, nombre: str) -> str:
    out = [f"# Inventario mecánico de verificación — {nombre}", "",
           "> Generado automáticamente. **Nada de lo listado está verificado.** "
           "Es el punto de partida de los Pasos 2 y 4 del protocolo.", ""]

    out += ["## 1. Posibles instrucciones dirigidas al modelo", ""]
    if informe.inyeccion:
        out += ["| Línea | Tipo | Fragmento | Nota |", "|---|---|---|---|"]
        out += [f"| {h.linea} | {h.tipo} | {_celda(h.texto)} | {_celda(h.nota)} |" for h in informe.inyeccion]
    else:
        out.append("No se detectaron patrones de instrucción al modelo ni caracteres invisibles "
                   "(la detección automática no es exhaustiva).")
    out.append("")

    out += ["## 2. Alertas de coherencia y régimen", ""]
    if informe.alertas:
        out += ["| Línea | Tipo | Dato | Nota |", "|---|---|---|---|"]
        out += [f"| {h.linea} | {h.tipo} | {_celda(h.texto)} | {_celda(h.nota)} |" for h in informe.alertas]
    else:
        out.append("Sin alertas automáticas.")
    out.append("")

    out += ["## 3. Lista de verificación de citas", "",
            "| N.º | Línea | Tipo | Dato citado | Fuente a consultar | Estado | Nota |",
            "|---|---|---|---|---|---|---|"]
    for i, h in enumerate(informe.citas, 1):
        out.append(f"| {i} | {h.linea} | {h.tipo} | {_celda(h.texto)} | {_celda(h.fuente_sugerida)} | {h.estado} | {_celda(h.nota)} |")
    out.append("")

    out += ["## 4. Datos fácticos a cotejar con pruebas", "",
            "| Línea | Tipo | Dato | Cotejar con |", "|---|---|---|---|"]
    out += [f"| {h.linea} | {h.tipo} | {_celda(h.texto)} | {_celda(h.fuente_sugerida)} |" for h in informe.datos]
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("escrito", type=Path)
    ap.add_argument("--formato", choices=("md", "json"), default="md")
    ap.add_argument("--fecha-referencia", type=dt.date.fromisoformat, default=None,
                    help="Fecha contra la cual se marcan fechas futuras (por defecto, hoy)")
    args = ap.parse_args(argv)

    if not args.escrito.is_file():
        print(f"No existe el archivo: {args.escrito}", file=sys.stderr)
        return 2
    try:
        texto = leer_documento(args.escrito)
    except (RuntimeError, zipfile.BadZipFile, ElementTree.ParseError, subprocess.CalledProcessError) as e:
        print(f"No se pudo leer el escrito: {e}", file=sys.stderr)
        return 2

    informe = analizar(texto, args.fecha_referencia)
    if args.formato == "json":
        print(json.dumps(asdict(informe), ensure_ascii=False, indent=2))
    else:
        print(a_markdown(informe, args.escrito.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
