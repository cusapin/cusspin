#!/usr/bin/env python3
"""Motor determinista de verificación de escritos (el "núcleo").

Recibe la REPRESENTACIÓN ESTRUCTURADA del escrito (JSON conforme a esquema_escrito.json),
elaborada por el asistente y confirmada por el apoderado, y comprueba sin intervención de
IA la parte decidible de la verificación:

* coherencia interna: fechas válidas, cronología, identidad del acto, de las partes y de
  los montos, numeración de los hechos;
* completitud de la congruencia: pretensión → hechos → pruebas; normas → hechos y
  pretensiones; existencia del concepto de la infracción;
* requisitos formales del tipo de escrito, según motor/reglas/<tipo>.json;
* plazos, con el calendario de motor/calendario/feriados_pa.json;
* existencia del artículo y literalidad de las citas contra motor/corpus/.

Lo que no es decidible (suficiencia del concepto, contenido de los fallos, interpretación)
lo devuelve como NO_DETERMINABLE, en la zona interpretativa, para el asistente y el
apoderado. El motor nunca convierte un juicio en una certeza.

Resultados posibles: CUMPLE · CUMPLE_CONDICIONADO (regla de base no verificada) ·
INCUMPLE · PREGUNTA (incumpliría, pero la base normativa está SIN VERIFICAR) ·
NO_DETERMINABLE.

Uso:
    python3 verificar_escrito.py REPRESENTACION.json [--formato md|json]
        [--reglas DIR] [--corpus DIR] [--calendario ARCHIVO]

Códigos de salida: 0 sin incumplimientos críticos · 1 hay incumplimientos CRÍTICOS ·
2 error de lectura · 3 la representación no respeta el esquema.
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import difflib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
SEVERIDADES = ["CRÍTICO", "GRAVE", "MODERADO", "FORMAL"]
RESULTADOS = ["INCUMPLE", "PREGUNTA", "NO_DETERMINABLE", "CUMPLE_CONDICIONADO", "CUMPLE"]


@dataclass
class Resultado:
    regla: str
    control: str
    descripcion: str
    resultado: str
    severidad: str = ""
    detalle: str = ""
    base: str = "Coherencia/congruencia lógica (no depende de norma)"
    estado_base: str = "—"
    ubicaciones: list[str] = field(default_factory=list)
    zona: str = "verificada"  # verificada | interpretativa


class ErrorEsquema(Exception):
    def __init__(self, errores: list[str]):
        super().__init__("; ".join(errores))
        self.errores = errores


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s.,;:]+", " ", s).strip()


def fecha(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s.strip())
    except ValueError:
        return None


def menciones(obj: Any) -> list[dict]:
    return obj if isinstance(obj, list) else []


def valores_distintos(ms: list[dict], clave=_norm) -> dict[str, list[str]]:
    """{valor_normalizado: [ubicaciones]} conservando el primer texto visto como clave legible."""
    salida: dict[str, list[str]] = {}
    legible: dict[str, str] = {}
    for m in ms:
        k = clave(str(m.get("valor", "")))
        legible.setdefault(k, str(m.get("valor", "")))
        salida.setdefault(legible[k], []).append(str(m.get("ubicacion", "")))
    return salida


def fechas_validas(ms: list[dict]) -> list[tuple[dt.date, str]]:
    return [(f, m.get("ubicacion", "")) for m in ms if (f := fecha(m.get("valor")))]


def fecha_unica(ms: list[dict]) -> tuple[dt.date | None, str]:
    vals = {f for f, _ in fechas_validas(ms)}
    if len(vals) == 1:
        return vals.pop(), ""
    if not vals:
        return None, "no consta una fecha válida"
    return None, "constan fechas distintas: " + ", ".join(sorted(v.isoformat() for v in vals))


def monto(s: str) -> float | None:
    try:
        return round(float(str(s).replace(",", "")), 2)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Validación estructural (la representación misma)
# ---------------------------------------------------------------------------

REQUERIDOS = ["version_esquema", "escrito", "partes", "pretensiones", "hechos", "pruebas",
              "normas_invocadas", "formalizacion"]


def validar_estructura(rep: dict) -> None:
    err: list[str] = []
    if not isinstance(rep, dict):
        raise ErrorEsquema(["La representación debe ser un objeto JSON"])
    for k in REQUERIDOS:
        if k not in rep:
            err.append(f"Falta la clave obligatoria '{k}'")
    if err:
        raise ErrorEsquema(err)
    if rep.get("version_esquema") != "1.0":
        err.append("version_esquema debe ser '1.0'")
    if not rep["escrito"].get("tipo"):
        err.append("escrito.tipo es obligatorio")
    if "confirmada_por_apoderado" not in rep["formalizacion"]:
        err.append("formalizacion.confirmada_por_apoderado es obligatorio")

    ids: dict[str, set[str]] = {}
    for coleccion in ("partes", "pretensiones", "hechos", "pruebas", "normas_invocadas", "anexos", "fallos_invocados"):
        items = rep.get(coleccion, [])
        if not isinstance(items, list):
            err.append(f"'{coleccion}' debe ser una lista")
            continue
        vistos: set[str] = set()
        for i, it in enumerate(items):
            if not isinstance(it, dict) or not it.get("id"):
                err.append(f"{coleccion}[{i}] sin 'id'")
                continue
            if it["id"] in vistos:
                err.append(f"id duplicado en {coleccion}: {it['id']}")
            vistos.add(it["id"])
        ids[coleccion] = vistos

    obligatorios = {
        "partes": {"rol": None, "nombre": list},
        "pretensiones": {"texto": str, "clase": None, "hechos": list},
        "hechos": {"texto": str, "pruebas": list},
        "pruebas": {"descripcion": str, "estado": None},
        "normas_invocadas": {"cuerpo_texto": str, "articulo": str, "rol": None, "hechos": list, "pretensiones": list},
        "anexos": {"clase": str},
        "fallos_invocados": {"descripcion": str},
    }
    enumerados = {
        ("partes", "rol"): {"demandante", "demandada", "apoderado", "tercero", "testigo", "representante_legal", "otro"},
        ("pretensiones", "clase"): {"declarativa", "condena_pecuniaria", "restablecimiento", "cautelar", "otra"},
        ("pruebas", "estado"): {"aportada", "aducida", "anunciada_sin_aportar"},
        ("normas_invocadas", "rol"): {"infringida", "fundamento", "procesal"},
    }
    for coleccion, campos in obligatorios.items():
        for it in rep.get(coleccion, []) or []:
            if not isinstance(it, dict):
                continue
            for campo, tipo in campos.items():
                if campo not in it:
                    err.append(f"{coleccion} {it.get('id')}: falta '{campo}'")
                elif tipo and not isinstance(it[campo], tipo):
                    err.append(f"{coleccion} {it.get('id')}: '{campo}' debe ser {tipo.__name__}")
                elif (coleccion, campo) in enumerados and it[campo] not in enumerados[(coleccion, campo)]:
                    err.append(f"{coleccion} {it.get('id')}: '{campo}' = '{it[campo]}' no es un valor admitido")

    def refs(coleccion: str, campo: str, destino: str):
        for it in rep.get(coleccion, []) or []:
            for r in it.get(campo, []) or []:
                if r not in ids.get(destino, set()):
                    err.append(f"{coleccion} {it.get('id')}: '{campo}' remite a '{r}', que no existe en {destino}")

    refs("pretensiones", "hechos", "hechos")
    refs("hechos", "pruebas", "pruebas")
    refs("normas_invocadas", "hechos", "hechos")
    refs("normas_invocadas", "pretensiones", "pretensiones")

    def chequear_menciones(ruta: str, valor: Any):
        if valor is None:
            return
        if not isinstance(valor, list) or any(not isinstance(m, dict) or "valor" not in m or "ubicacion" not in m for m in valor):
            err.append(f"{ruta} debe ser una lista de menciones {{valor, ubicacion}}")

    chequear_menciones("escrito.fecha_escrito", rep["escrito"].get("fecha_escrito"))
    chequear_menciones("cuantia_total", rep.get("cuantia_total"))
    for k, v in (rep.get("acto_impugnado") or {}).items():
        chequear_menciones(f"acto_impugnado.{k}", v)
    for p in rep["partes"]:
        chequear_menciones(f"partes {p.get('id')}.nombre", p.get("nombre"))
        chequear_menciones(f"partes {p.get('id')}.cedula", p.get("cedula"))
        chequear_menciones(f"partes {p.get('id')}.domicilio", p.get("domicilio"))
    for p in rep["pretensiones"]:
        chequear_menciones(f"pretensiones {p.get('id')}.monto", p.get("monto"))
    for h in rep["hechos"]:
        chequear_menciones(f"hechos {h.get('id')}.fecha", h.get("fecha"))
    for i, r in enumerate((rep.get("agotamiento") or {}).get("recursos", []) or []):
        for k in ("fecha_interposicion", "fecha_resolucion", "fecha_notificacion"):
            chequear_menciones(f"agotamiento.recursos[{i}].{k}", r.get(k))
    if err:
        raise ErrorEsquema(err)


# ---------------------------------------------------------------------------
# Coherencia
# ---------------------------------------------------------------------------

ORDINALES = ["primero", "segundo", "tercero", "cuarto", "quinto", "sexto", "septimo", "octavo", "noveno",
             "decimo", "undecimo", "duodecimo", "decimotercero", "decimocuarto", "decimoquinto",
             "decimosexto", "decimoseptimo", "decimoctavo", "decimonoveno", "vigesimo"]
ALIAS = {"decimo primero": "undecimo", "decimoprimero": "undecimo", "decimo segundo": "duodecimo",
         "decimosegundo": "duodecimo", "setimo": "septimo"}


def _ordinal(s: str) -> int | None:
    t = _norm(s)
    if t.isdigit():
        return int(t)
    t = ALIAS.get(t, t)
    return ORDINALES.index(t) + 1 if t in ORDINALES else None


def _todas_las_fechas(rep: dict) -> list[tuple[str, list[dict]]]:
    acto = rep.get("acto_impugnado") or {}
    campos = [("fecha del escrito", rep["escrito"].get("fecha_escrito")),
              ("fecha del acto impugnado", acto.get("fecha")),
              ("notificación del acto impugnado", acto.get("fecha_notificacion"))]
    for i, r in enumerate((rep.get("agotamiento") or {}).get("recursos", []) or [], 1):
        for k, etiqueta in (("fecha_interposicion", "interposición"), ("fecha_resolucion", "resolución"),
                            ("fecha_notificacion", "notificación")):
            campos.append((f"{etiqueta} del recurso {i} ({r.get('tipo', '')})", r.get(k)))
    for h in rep["hechos"]:
        campos.append((f"fecha del hecho {h.get('numero_en_escrito') or h['id']}", h.get("fecha")))
    return [(e, menciones(m)) for e, m in campos]


def coherencia(rep: dict) -> list[Resultado]:
    out: list[Resultado] = []

    # H-01 fechas válidas
    for etiqueta, ms in _todas_las_fechas(rep):
        for m in ms:
            if fecha(m.get("valor")) is None:
                out.append(Resultado("COH-01", "H-01", f"Fecha inexistente o mal formada ({etiqueta})", "INCUMPLE",
                                     "GRAVE", f"'{m.get('valor')}' no es una fecha del calendario", ubicaciones=[m.get("ubicacion", "")]))

    # H-01 cronología
    acto = rep.get("acto_impugnado") or {}
    recursos = (rep.get("agotamiento") or {}).get("recursos", []) or []
    cadena: list[tuple[str, list[dict]]] = [("fecha del acto impugnado", menciones(acto.get("fecha"))),
                                            ("notificación del acto impugnado", menciones(acto.get("fecha_notificacion")))]
    for i, r in enumerate(recursos, 1):
        cadena += [(f"interposición del recurso {i}", menciones(r.get("fecha_interposicion"))),
                   (f"resolución del recurso {i}", menciones(r.get("fecha_resolucion"))),
                   (f"notificación de la resolución del recurso {i}", menciones(r.get("fecha_notificacion")))]
    fe = menciones(rep["escrito"].get("fecha_escrito"))
    pares = [(cadena[i], cadena[j]) for i in range(len(cadena)) for j in range(i + 1, len(cadena))]
    pares += [(c, ("fecha del escrito", fe)) for c in cadena]
    pares += [((f"fecha del hecho {h.get('numero_en_escrito') or h['id']}", menciones(h.get("fecha"))), ("fecha del escrito", fe))
              for h in rep["hechos"]]
    fp = fecha(rep["escrito"].get("fecha_presentacion"))
    for (ea, ma), (eb, mb) in pares:
        for fa, ua in fechas_validas(ma):
            for fb, ub in fechas_validas(mb):
                if fa > fb:
                    out.append(Resultado("COH-02", "H-01", "Cronología imposible", "INCUMPLE", "CRÍTICO" if "escrito" in eb else "GRAVE",
                                         f"La {ea} ({fa.isoformat()}) es posterior a la {eb} ({fb.isoformat()})",
                                         ubicaciones=[ua, ub]))
    if fp:
        for f, u in fechas_validas(fe):
            if f > fp:
                out.append(Resultado("COH-02", "H-01", "Cronología imposible", "INCUMPLE", "GRAVE",
                                     f"El escrito está fechado ({f.isoformat()}) después de su presentación ({fp.isoformat()})", ubicaciones=[u]))

    # H-09 identidad del acto
    for campo, etiqueta in (("numero", "número"), ("fecha", "fecha"), ("emisor", "autoridad emisora")):
        distintos = valores_distintos(menciones(acto.get(campo)))
        if len(distintos) > 1:
            out.append(Resultado("COH-03", "H-09", f"El acto impugnado se identifica con {etiqueta} distinta", "INCUMPLE", "GRAVE",
                                 "Variantes: " + "; ".join(f"'{v}' ({', '.join(u)})" for v, u in distintos.items()),
                                 ubicaciones=[x for u in distintos.values() for x in u]))
    distintos = valores_distintos(fe)
    if len(distintos) > 1:
        out.append(Resultado("COH-03", "H-01", "El escrito tiene más de una fecha", "INCUMPLE", "MODERADO",
                             "Variantes: " + "; ".join(distintos)))

    # H-02 partes
    cedulas: dict[str, list[str]] = {}
    for p in rep["partes"]:
        etiqueta = f"{p['rol']} {p['id']}"
        for campo in ("nombre", "cedula"):
            distintos = valores_distintos(menciones(p.get(campo)))
            if len(distintos) > 1:
                out.append(Resultado("COH-04", "H-02", f"La parte {etiqueta} aparece con {campo} distinto", "INCUMPLE", "GRAVE",
                                     "Variantes: " + "; ".join(f"'{v}' ({', '.join(u)})" for v, u in distintos.items())))
        for c in {_norm(m["valor"]) for m in menciones(p.get("cedula"))}:
            cedulas.setdefault(c, []).append(etiqueta)
    for c, quienes in cedulas.items():
        if len(quienes) > 1:
            out.append(Resultado("COH-05", "H-02", "Una misma cédula se atribuye a personas distintas", "INCUMPLE", "GRAVE",
                                 f"Cédula {c}: {', '.join(quienes)}"))

    # H-03 montos
    suma, sumables, montos_ok = 0.0, 0, True
    for pr in rep["pretensiones"]:
        ms = menciones(pr.get("monto"))
        distintos = valores_distintos(ms, clave=lambda v: str(monto(v)))
        if len(distintos) > 1:
            montos_ok = False
            out.append(Resultado("COH-06", "H-03", f"La pretensión {pr['id']} tiene montos distintos", "INCUMPLE", "GRAVE",
                                 "Variantes: " + "; ".join(f"{v} ({', '.join(u)})" for v, u in distintos.items())))
        elif len(distintos) == 1 and (v := monto(next(iter(distintos)))) is not None:
            suma += v
            sumables += 1
    cuantia = valores_distintos(menciones(rep.get("cuantia_total")), clave=lambda v: str(monto(v)))
    if len(cuantia) > 1:
        out.append(Resultado("COH-06", "H-03", "La cuantía total aparece con montos distintos", "INCUMPLE", "GRAVE",
                             "Variantes: " + "; ".join(cuantia)))
    elif len(cuantia) == 1 and sumables and montos_ok:
        total = monto(next(iter(cuantia)))
        if total is not None and abs(total - suma) > 0.005:
            out.append(Resultado("COH-07", "H-03", "La cuantía total no coincide con la suma de las pretensiones", "INCUMPLE", "GRAVE",
                                 f"Cuantía declarada {total:,.2f}; suma de pretensiones {suma:,.2f}"))

    # H-05 numeración
    numeros = [(h, _ordinal(h["numero_en_escrito"])) for h in rep["hechos"] if h.get("numero_en_escrito")]
    esperado = 1
    for h, n in numeros:
        if n is None:
            out.append(Resultado("COH-08", "H-05", "Numeración de hecho no reconocible", "NO_DETERMINABLE", "",
                                 f"'{h['numero_en_escrito']}'", zona="interpretativa"))
            continue
        if n != esperado:
            out.append(Resultado("COH-08", "H-05", "Numeración de los hechos rota", "INCUMPLE", "MODERADO",
                                 f"Se esperaba el n.º {esperado} y aparece '{h['numero_en_escrito']}' (n.º {n})"))
        esperado = n + 1
    return out


# ---------------------------------------------------------------------------
# Congruencia (grafo pretensión → hecho → prueba; norma → hecho/pretensión)
# ---------------------------------------------------------------------------

def congruencia(rep: dict, min_palabras: int) -> list[Resultado]:
    out: list[Resultado] = []
    hechos = {h["id"]: h for h in rep["hechos"]}
    pruebas = {p["id"]: p for p in rep["pruebas"]}
    anexos = {a["id"] for a in rep.get("anexos", []) or []}

    hechos_usados: set[str] = set()
    for pr in rep["pretensiones"]:
        hechos_usados.update(pr.get("hechos", []))
        if pr["clase"] != "cautelar" and not pr.get("hechos"):
            out.append(Resultado("CON-01", "C-01", "Pretensión sin hechos que la sostengan", "INCUMPLE", "CRÍTICO",
                                 f"{pr['id']}: «{pr['texto'][:120]}»", ubicaciones=[pr.get("ubicacion", "")]))

    pruebas_usadas: set[str] = set()
    for h in rep["hechos"]:
        pruebas_usadas.update(h.get("pruebas", []))
        etiqueta = h.get("numero_en_escrito") or h["id"]
        if not h.get("esencial", True):
            continue
        ps = [pruebas[p] for p in h.get("pruebas", []) if p in pruebas]
        if not ps:
            out.append(Resultado("CON-02", "C-02", "Hecho esencial sin prueba", "INCUMPLE", "GRAVE",
                                 f"Hecho {etiqueta}: «{h['texto'][:120]}»"))
        elif all(p["estado"] == "anunciada_sin_aportar" for p in ps):
            out.append(Resultado("CON-02", "C-02", "Hecho esencial cuya prueba solo se anuncia", "INCUMPLE", "GRAVE",
                                 f"Hecho {etiqueta}: pruebas {', '.join(p['id'] for p in ps)} no aportadas ni aducidas formalmente"))
        if h["id"] not in hechos_usados and not any(h["id"] in n.get("hechos", []) for n in rep["normas_invocadas"]):
            out.append(Resultado("CON-05", "C-01", "Hecho que no sostiene ninguna pretensión ni norma", "INCUMPLE", "MODERADO",
                                 f"Hecho {etiqueta}: verificar su relevancia o vincularlo"))

    for p in rep["pruebas"]:
        if p["id"] not in pruebas_usadas:
            out.append(Resultado("CON-03", "C-12", "Prueba no vinculada a ningún hecho", "INCUMPLE", "MODERADO", p["descripcion"][:120]))
        if p["estado"] == "aportada" and p.get("anexo") and p["anexo"] not in anexos:
            out.append(Resultado("CON-03", "H-10", "Prueba aportada que remite a un anexo inexistente", "INCUMPLE", "MODERADO",
                                 f"{p['id']} → anexo '{p['anexo']}'"))

    for n in rep["normas_invocadas"]:
        etiqueta = f"art. {n['articulo']} de {n['cuerpo_texto']}"
        sev = "GRAVE" if n["rol"] == "infringida" else "MODERADO"
        faltan = [x for x, vacio in (("ningún hecho", not n.get("hechos")), ("ninguna pretensión", not n.get("pretensiones"))) if vacio]
        if faltan:
            out.append(Resultado("CON-04", "C-03", "Norma invocada sin conexión con " + " ni con ".join(faltan), "INCUMPLE", sev,
                                 etiqueta, ubicaciones=[n.get("ubicacion", "")]))
        if n["rol"] == "infringida":
            c = n.get("concepto") or {}
            palabras = len((c.get("explicacion") or "").split())
            if c.get("modalidad") and palabras >= min_palabras:
                out.append(Resultado("INT-01", "C-04", "Suficiencia del concepto de la infracción", "NO_DETERMINABLE", "",
                                     f"{etiqueta}: el concepto existe ({palabras} palabras, modalidad '{c['modalidad']}'); "
                                     "su suficiencia es juicio interpretativo", zona="interpretativa"))
    return out


# ---------------------------------------------------------------------------
# Requisitos formales (reglas declarativas)
# ---------------------------------------------------------------------------

def resolver_ruta(rep: Any, ruta: str) -> list[Any]:
    """'partes[rol=demandante].nombre' → lista de valores encontrados."""
    actuales = [rep]
    for seg in ruta.split("."):
        m = re.fullmatch(r"(\w+)(?:\[(\w+)=([^\]]+)\])?", seg)
        if not m:
            raise ValueError(f"Ruta inválida: {ruta}")
        nombre, k, v = m.groups()
        siguientes = []
        for a in actuales:
            if not isinstance(a, dict) or nombre not in a or a[nombre] is None:
                continue
            val = a[nombre]
            if k:
                siguientes += [x for x in (val if isinstance(val, list) else []) if isinstance(x, dict) and str(x.get(k)) == v]
            else:
                siguientes.append(val)
        actuales = siguientes
    return actuales


def _no_vacio(v: Any) -> bool:
    if isinstance(v, list):
        return any(_no_vacio(x) for x in v)
    if isinstance(v, dict):
        return "valor" in v and bool(str(v["valor"]).strip()) or (bool(v) and "valor" not in v)
    return v not in (None, "", False)


def _desde_hasta(rep: dict, clave: str) -> tuple[dt.date | None, str]:
    acto = rep.get("acto_impugnado") or {}
    if clave == "@notificacion_acto_que_agota_via":
        recursos = (rep.get("agotamiento") or {}).get("recursos", []) or []
        if recursos:
            f, motivo = fecha_unica(menciones(recursos[-1].get("fecha_notificacion")))
            return f, motivo and f"notificación de la resolución del último recurso: {motivo}"
        f, motivo = fecha_unica(menciones(acto.get("fecha_notificacion")))
        return f, motivo and f"notificación del acto impugnado: {motivo}"
    if clave == "@notificacion_acto_impugnado":
        f, motivo = fecha_unica(menciones(acto.get("fecha_notificacion")))
        return f, motivo and f"notificación del acto impugnado: {motivo}"
    if clave == "@fecha_presentacion_o_escrito":
        fp = fecha(rep["escrito"].get("fecha_presentacion"))
        if fp:
            return fp, ""
        f, motivo = fecha_unica(menciones(rep["escrito"].get("fecha_escrito")))
        return f, motivo and f"fecha del escrito: {motivo}"
    vals = resolver_ruta(rep, clave)
    return fecha_unica(vals[0] if vals and isinstance(vals[0], list) else [])


class Calendario:
    def __init__(self, datos: dict):
        self.anios = {int(a): {dt.date.fromisoformat(d) for d in dias} for a, dias in (datos.get("anios") or {}).items()}

    def conocido(self, anio: int) -> bool:
        return anio in self.anios

    def inhabil(self, d: dt.date) -> bool:
        return d.weekday() >= 5 or d in self.anios.get(d.year, set())


def sumar_meses(d: dt.date, n: int, dia_inexistente: str) -> dt.date | None:
    mes = d.month - 1 + n
    anio, mes = d.year + mes // 12, mes % 12 + 1
    ultimo = calendar.monthrange(anio, mes)[1]
    if d.day > ultimo:
        if dia_inexistente == "ultimo_del_mes":
            return dt.date(anio, mes, ultimo)
        return None
    return dt.date(anio, mes, d.day)


def calcular_plazo(rep: dict, c: dict, cal: Calendario) -> tuple[str, str]:
    desde, m1 = _desde_hasta(rep, c["desde"])
    hasta, m2 = _desde_hasta(rep, c["hasta"])
    if not desde or not hasta:
        return "NO_DETERMINABLE", "No puede computarse: " + "; ".join(x for x in (m1, m2) if x)
    comp = c.get("computo", {})
    notas = []
    unidad, n = c["unidad"], int(c["cantidad"])
    if unidad == "meses":
        venc = sumar_meses(desde, n, comp.get("dia_inexistente", "ultimo_del_mes"))
        if venc is None:
            return "NO_DETERMINABLE", "El día de vencimiento no existe en el mes y la regla de cómputo no lo resuelve"
    elif unidad == "dias_calendario":
        venc = desde + dt.timedelta(days=n)
    elif unidad == "dias_habiles":
        venc, restantes = desde, n
        while restantes:
            venc += dt.timedelta(days=1)
            if not cal.conocido(venc.year):
                return "NO_DETERMINABLE", f"Calendario de días inhábiles de {venc.year} no confirmado"
            if not cal.inhabil(venc):
                restantes -= 1
    else:
        return "NO_DETERMINABLE", f"Unidad de plazo desconocida: {unidad}"

    if comp.get("prorroga_si_inhabil"):
        while cal.inhabil(venc):
            venc += dt.timedelta(days=1)
        if not cal.conocido(venc.year):
            notas.append(f"no se pudo descartar que el vencimiento caiga en feriado ({venc.year} sin calendario confirmado)")
    margen = (venc - hasta).days
    if notas and abs(margen) <= 10:
        return "NO_DETERMINABLE", (f"Desde {desde.isoformat()}, {n} {unidad}: vence {venc.isoformat()} (provisional); "
                                   f"presentación {hasta.isoformat()}; margen de {margen} días insuficiente: " + "; ".join(notas))
    detalle = (f"Desde {desde.isoformat()}, {n} {unidad}: vence {venc.isoformat()}; presentación/fecha tomada {hasta.isoformat()} "
               f"({'quedan' if margen >= 0 else 'vencido hace'} {abs(margen)} días)")
    if not rep["escrito"].get("fecha_presentacion"):
        detalle += ". Se usó la fecha del escrito por no constar la de presentación"
    if comp.get("nota"):
        detalle += f". {comp['nota']}"
    if notas:
        detalle += ". Nota: " + "; ".join(notas)
    return ("CUMPLE" if margen >= 0 else "INCUMPLE"), detalle


def evaluar_regla(rep: dict, regla: dict, params: dict, cal: Calendario) -> list[Resultado]:
    c = regla["comprobacion"]
    tipo = c["tipo"]
    salida: list[tuple[str, str]] = []  # (resultado, detalle)

    if tipo == "campo_presente":
        ok = any(_no_vacio(v) for v in resolver_ruta(rep, c["ruta"]))
        salida.append(("CUMPLE" if ok else "INCUMPLE", "" if ok else f"No consta: {c['ruta']}"))
    elif tipo == "normas_infringidas_presentes":
        ok = any(n["rol"] == "infringida" for n in rep["normas_invocadas"])
        salida.append(("CUMPLE" if ok else "INCUMPLE", "" if ok else "Ninguna norma figura como infringida"))
    elif tipo == "concepto_por_norma_infringida":
        minimo = params.get("concepto_min_palabras", 25)
        infringidas = [n for n in rep["normas_invocadas"] if n["rol"] == "infringida"]
        for n in infringidas:
            cpt = n.get("concepto") or {}
            palabras = len((cpt.get("explicacion") or "").split())
            if not cpt.get("modalidad") or palabras < minimo:
                faltas = [x for x, cond in (("modalidad", not cpt.get("modalidad")),
                                            (f"explicación ({palabras} palabras; mínimo de existencia {minimo})", palabras < minimo)) if cond]
                salida.append(("INCUMPLE", f"art. {n['articulo']} de {n['cuerpo_texto']}: falta {' y '.join(faltas)}"))
        if not salida:
            salida.append(("CUMPLE" if infringidas else "NO_DETERMINABLE",
                           "" if infringidas else "No hay normas infringidas sobre las cuales evaluar el concepto"))
    elif tipo == "pretensiones_pecuniarias_con_monto":
        sin = [p["id"] for p in rep["pretensiones"] if p["clase"] == "condena_pecuniaria" and not menciones(p.get("monto"))]
        salida.append(("INCUMPLE", "Sin cuantía: " + ", ".join(sin)) if sin else ("CUMPLE", ""))
    elif tipo == "agotamiento_consta":
        ok = bool((rep.get("agotamiento") or {}).get("consta"))
        salida.append(("CUMPLE" if ok else "INCUMPLE", "" if ok else "El escrito no acredita el agotamiento de la vía"))
    elif tipo == "anexo_clase":
        ok = any(a.get("clase") == c["clase"] for a in rep.get("anexos", []) or [])
        salida.append(("CUMPLE" if ok else "INCUMPLE", "" if ok else f"No consta anexo de clase '{c['clase']}'"))
    elif tipo == "poder_consta":
        ok = bool((rep.get("poder") or {}).get("consta"))
        salida.append(("CUMPLE" if ok else "INCUMPLE", "" if ok else "No consta el poder"))
    elif tipo == "plazo":
        salida.append(calcular_plazo(rep, c, cal))
    elif tipo == "normas_presentes":
        rol = c.get("rol")
        ok = any(rol is None or n["rol"] == rol for n in rep["normas_invocadas"])
        salida.append(("CUMPLE" if ok else "INCUMPLE", "" if ok else
                       "El escrito no invoca " + (f"normas con rol '{rol}'" if rol else "fundamento de derecho alguno")))
    elif tipo == "manual":
        salida.append(("NO_DETERMINABLE", "Requisito no decidible mecánicamente; lo verifica el asistente: " + c["pregunta"]))
    else:
        salida.append(("NO_DETERMINABLE", f"Tipo de comprobación desconocido: {tipo}"))

    estado = regla["estado"]
    if tipo == "plazo" and c.get("computo", {}).get("estado_reglas_computo") == "SV" and estado != "SV":
        estado = "SV"  # el plazo puede estar confirmado, pero no su forma de cómputo
    resultados = []
    for res, det in salida:
        if estado == "SV":
            if res == "INCUMPLE":
                res, det = "PREGUNTA", det + ". Base normativa SIN VERIFICAR: confirme el requisito antes de tenerlo por incumplido"
            elif res == "CUMPLE":
                res = "CUMPLE_CONDICIONADO"
        resultados.append(Resultado(regla["id"], regla["control"], regla["descripcion"], res,
                                    regla["severidad"] if res in ("INCUMPLE", "PREGUNTA") else "", det,
                                    regla["base"], regla["estado"],
                                    zona="interpretativa" if res == "NO_DETERMINABLE" else "verificada"))
    return resultados


# ---------------------------------------------------------------------------
# Cotejo contra el corpus verificado
# ---------------------------------------------------------------------------

def _norm_literal(s: str) -> str:
    s = s.replace("“", '"').replace("”", '"').replace("«", '"').replace("»", '"').replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().strip('"').strip()


BASE_CORPUS = "Corpus verificado del despacho (motor/corpus/)"


def cotejar_corpus(rep: dict, dir_corpus: Path) -> list[Resultado]:
    out: list[Resultado] = []
    fecha_acto, _ = fecha_unica(menciones((rep.get("acto_impugnado") or {}).get("fecha")))
    for n in rep["normas_invocadas"]:
        etiqueta = f"art. {n['articulo']} de {n['cuerpo_texto']}"
        if not n.get("cuerpo_id"):
            out.append(Resultado("COR-00", "V-01", "Existencia y texto de la norma", "NO_DETERMINABLE", "",
                                 f"{etiqueta}: sin 'cuerpo_id'; verificar manualmente", zona="interpretativa", base=BASE_CORPUS))
            continue
        archivo = dir_corpus / f"{n['cuerpo_id']}.json"
        if not archivo.is_file():
            out.append(Resultado("COR-00", "V-01", "Existencia y texto de la norma", "NO_DETERMINABLE", "",
                                 f"{etiqueta}: '{n['cuerpo_id']}' no está en el corpus verificado", zona="interpretativa", base=BASE_CORPUS))
            continue
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        f_rel = fecha(n.get("fecha_relevante")) or fecha_acto
        version = None
        for v in datos.get("versiones", []):
            ini, fin = fecha(v.get("vigente_desde")), fecha(v.get("vigente_hasta"))
            if f_rel is None:
                if fin is None:
                    version = v
            elif (ini is None or ini <= f_rel) and (fin is None or f_rel <= fin):
                version = v
        if version is None:
            out.append(Resultado("COR-01", "V-04", "Versión vigente de la norma", "NO_DETERMINABLE", "",
                                 f"{etiqueta}: el corpus no tiene versión vigente a {f_rel or 'la fecha actual'}", zona="interpretativa", base=BASE_CORPUS))
            continue
        primaria = version.get("estado") == "C-1"
        fuente = version.get("fuente", "")
        texto = (version.get("articulos") or {}).get(str(n["articulo"]))
        if texto is None:
            out.append(Resultado("COR-02", "V-01", "El artículo citado no existe en la versión aplicable",
                                 "INCUMPLE" if primaria else "PREGUNTA", "GRAVE",
                                 f"{etiqueta} (versión según {fuente})", base=fuente, estado_base=version.get("estado", "")))
            continue
        out.append(Resultado("COR-02", "V-01", "El artículo citado existe en la versión aplicable",
                             "CUMPLE" if primaria else "CUMPLE_CONDICIONADO", "", f"{etiqueta} (según {fuente})",
                             base=fuente, estado_base=version.get("estado", "")))
        if n.get("cita_textual"):
            cita, art = _norm_literal(n["cita_textual"]), _norm_literal(texto)
            if cita and cita in art:
                out.append(Resultado("COR-03", "V-03", "La cita textual es literal",
                                     "CUMPLE" if primaria else "CUMPLE_CONDICIONADO", "", etiqueta,
                                     base=fuente, estado_base=version.get("estado", "")))
            else:
                bloques = difflib.SequenceMatcher(None, cita, art, autojunk=False).get_matching_blocks()
                cobertura = sum(b.size for b in bloques) / max(len(cita), 1)
                out.append(Resultado("COR-03", "V-03", "La cita textual NO coincide con el texto del artículo",
                                     "INCUMPLE" if primaria else "PREGUNTA", "GRAVE",
                                     f"{etiqueta}: coincidencia aproximada del {cobertura:.0%}; posible paráfrasis o alteración",
                                     base=fuente, estado_base=version.get("estado", "")))
    for f in rep.get("fallos_invocados", []) or []:
        out.append(Resultado("INT-02", "V-06/V-07", "Existencia y contenido del fallo", "NO_DETERMINABLE", "",
                             f"{f['descripcion']}: no hay corpus jurisprudencial verificado", zona="interpretativa", base="Sin corpus jurisprudencial"))
    return out


# ---------------------------------------------------------------------------
# Orquestación y salida
# ---------------------------------------------------------------------------

GENERICO = "generico"


def cargar_reglas(dir_reglas: Path, tipo: str) -> tuple[dict | None, bool]:
    """Carga las reglas del tipo, resolviendo 'incluye' (reglas heredadas) y 'excluye'.

    Si no hay archivo para el tipo, usa las reglas generales y lo indica (segundo valor True).
    """
    def leer(nombre: str, pila: tuple[str, ...]) -> dict:
        if nombre in pila:
            raise ValueError(f"Inclusión circular de reglas: {' → '.join(pila + (nombre,))}")
        datos = json.loads((dir_reglas / f"{nombre}.json").read_text(encoding="utf-8"))
        reglas, params, nombres = [], {}, []
        for incluido in datos.get("incluye", []):
            base = leer(incluido, pila + (nombre,))
            reglas += base["reglas"]
            params.update(base.get("parametros", {}))
        excluir = set(datos.get("excluye", []))
        reglas = [r for r in reglas if r["id"] not in excluir]
        ids = {r["id"] for r in datos.get("reglas", [])}
        reglas = [r for r in reglas if r["id"] not in ids] + datos.get("reglas", [])
        params.update(datos.get("parametros", {}))
        return {"nombre": datos.get("nombre", nombre), "reglas": reglas, "parametros": params}

    if (dir_reglas / f"{tipo}.json").is_file():
        return leer(tipo, ()), False
    if (dir_reglas / f"{GENERICO}.json").is_file():
        return leer(GENERICO, ()), True
    return None, True


def verificar(rep: dict, dir_reglas: Path, dir_corpus: Path, archivo_cal: Path) -> dict:
    validar_estructura(rep)
    tipo = rep["escrito"]["tipo"]
    reglas, generico = cargar_reglas(dir_reglas, tipo)
    params = (reglas or {}).get("parametros", {})
    cal = Calendario(json.loads(archivo_cal.read_text(encoding="utf-8")) if archivo_cal.is_file() else {})

    resultados = coherencia(rep) + congruencia(rep, params.get("concepto_min_palabras", 25))
    if generico and tipo != GENERICO:
        resultados.append(Resultado("REQ-00", "C-09", "Requisitos formales propios del tipo de escrito", "NO_DETERMINABLE", "",
                                    f"No hay reglas específicas para '{tipo}'; se aplicaron solo las reglas generales. "
                                    "Los requisitos propios de esta vía los verifica el asistente", zona="interpretativa"))
    if reglas is not None:
        for regla in reglas["reglas"]:
            resultados += evaluar_regla(rep, regla, params, cal)
    resultados += cotejar_corpus(rep, dir_corpus)

    orden = lambda r: (RESULTADOS.index(r.resultado), SEVERIDADES.index(r.severidad) if r.severidad in SEVERIDADES else 9, r.regla)
    resultados.sort(key=orden)
    resumen: dict[str, int] = {}
    for r in resultados:
        k = r.resultado + (f" {r.severidad}" if r.severidad else "")
        resumen[k] = resumen.get(k, 0) + 1
    return {
        "tipo": tipo,
        "reglas_aplicadas": reglas.get("nombre") if reglas else None,
        "formalizacion_confirmada": bool(rep["formalizacion"].get("confirmada_por_apoderado")),
        "resumen": resumen,
        "criticos": sum(1 for r in resultados if r.resultado == "INCUMPLE" and r.severidad == "CRÍTICO"),
        "resultados": [asdict(r) for r in resultados],
    }


def _c(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def a_markdown(inf: dict) -> str:
    rs = inf["resultados"]
    out = ["# Resultado del motor de verificación", "",
           f"**Tipo de escrito:** {inf['tipo']} — {inf['reglas_aplicadas'] or 'sin reglas'}", ""]
    if not inf["formalizacion_confirmada"]:
        out += ["> **ADVERTENCIA:** la representación del escrito **no ha sido confirmada por el apoderado**. "
                "Los resultados valen solo en la medida en que la representación sea fiel al escrito.", ""]
    out += ["**Resumen:** " + " · ".join(f"{k}: {v}" for k, v in inf["resumen"].items()), ""]

    def tabla(filtro, titulo):
        filas = [r for r in rs if filtro(r)]
        out.append(f"## {titulo}")
        out.append("")
        if not filas:
            out.extend(["Sin resultados.", ""])
            return
        out.extend(["| Resultado | Severidad | Regla | Control | Descripción | Detalle | Base (estado) |",
                "|---|---|---|---|---|---|---|"])
        for r in filas:
            ubic = f" [{'; '.join(u for u in r['ubicaciones'] if u)}]" if any(r["ubicaciones"]) else ""
            out.append(f"| {r['resultado']} | {r['severidad'] or '—'} | {r['regla']} | {r['control']} | {_c(r['descripcion'])} | "
                       f"{_c(r['detalle'] + ubic)} | {_c(r['base'])} ({r['estado_base']}) |")
        out.append("")

    tabla(lambda r: r["resultado"] == "INCUMPLE", "1. Zona verificada — incumplimientos")
    tabla(lambda r: r["resultado"] == "PREGUNTA", "2. Zona verificada — preguntas (incumpliría, base normativa sin verificar)")
    tabla(lambda r: r["resultado"] in ("CUMPLE", "CUMPLE_CONDICIONADO"), "3. Zona verificada — cumplimientos")
    tabla(lambda r: r["resultado"] == "NO_DETERMINABLE", "4. Zona interpretativa — no determinable por el motor")
    out += ["---", "",
            "El motor comprueba la representación, no el escrito. Su salida no evalúa la suficiencia de los "
            "argumentos ni el contenido de los fallos. Un CUMPLE sobre una regla C-2 está confirmado contra fuente "
            "secundaria, no contra la Gaceta Oficial."]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("representacion", type=Path)
    ap.add_argument("--formato", choices=("md", "json"), default="md")
    ap.add_argument("--reglas", type=Path, default=BASE / "reglas")
    ap.add_argument("--corpus", type=Path, default=BASE / "corpus")
    ap.add_argument("--calendario", type=Path, default=BASE / "calendario" / "feriados_pa.json")
    args = ap.parse_args(argv)
    try:
        rep = json.loads(args.representacion.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"No se pudo leer la representación: {e}", file=sys.stderr)
        return 2
    try:
        inf = verificar(rep, args.reglas, args.corpus, args.calendario)
    except ErrorEsquema as e:
        print("La representación no respeta el esquema:\n- " + "\n- ".join(e.errores), file=sys.stderr)
        return 3
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"Error al aplicar reglas, corpus o calendario: {e}", file=sys.stderr)
        return 2
    print(json.dumps(inf, ensure_ascii=False, indent=2) if args.formato == "json" else a_markdown(inf))
    return 1 if inf["criticos"] else 0


if __name__ == "__main__":
    sys.exit(main())
