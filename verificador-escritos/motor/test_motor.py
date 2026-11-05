"""Pruebas del motor determinista. Ejecutar: python3 -m unittest -v (desde esta carpeta)."""

import copy
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import verificar_escrito as ve  # noqa: E402

FIXTURE = AQUI.parent / "pruebas" / "escrito_con_defectos.representacion.json"
REGLAS = AQUI / "reglas"
CAL_VACIO = AQUI / "calendario" / "feriados_pa.json"


def cargar():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def correr(rep, corpus=None, cal=CAL_VACIO):
    with tempfile.TemporaryDirectory() as d:
        return ve.verificar(rep, REGLAS, Path(corpus or d), cal)


def por_regla(inf, regla):
    return [r for r in inf["resultados"] if r["regla"] == regla]


def escrito_limpio():
    """Versión corregida del escrito de prueba: debe pasar sin incumplimientos."""
    rep = cargar()
    rep["partes"][3]["cedula"] = [{"valor": "4-111-222", "ubicacion": "hecho quinto"}]
    rep["poder"] = {"consta": True, "anexo": "A2"}
    rep["acto_impugnado"]["fecha"] = [{"valor": "2026-03-03", "ubicacion": "introducción"}]
    rep["agotamiento"] = {"consta": True, "recursos": [{
        "tipo": "reconsideración",
        "fecha_interposicion": [{"valor": "2026-03-20", "ubicacion": "hecho tercero"}],
        "fecha_resolucion": [{"valor": "2026-07-20", "ubicacion": "hecho cuarto"}],
        "fecha_notificacion": [{"valor": "2026-08-10", "ubicacion": "hecho cuarto"}]}]}
    rep["pretensiones"][1]["monto"] = [{"valor": "50300.00", "ubicacion": "introducción"},
                                       {"valor": "50300.00", "ubicacion": "lo que se demanda"}]
    rep["pretensiones"][2]["hechos"] = ["H1", "H2"]
    rep["cuantia_total"] = [{"valor": "50300.00", "ubicacion": "cuantía"}]
    rep["hechos"][2]["numero_en_escrito"] = "TERCERO"
    rep["hechos"][2]["fecha"] = [{"valor": "2026-03-15", "ubicacion": "hecho tercero"}]
    rep["hechos"][3]["numero_en_escrito"] = "CUARTO"
    rep["pruebas"] = [{"id": "PB1", "descripcion": "Certificación laboral", "estado": "aportada", "anexo": "A3"},
                      {"id": "PB2", "descripcion": "Copia de la resolución con constancia", "estado": "aportada", "anexo": "A1"}]
    for h in rep["hechos"][:3]:
        h["pruebas"] = ["PB1"] if h["id"] == "H1" else ["PB2"]
    rep["anexos"] = [{"id": "A1", "clase": "copia_acto_con_notificacion"}, {"id": "A2", "clase": "poder"},
                     {"id": "A3", "clase": "documental"}]
    concepto = {"modalidad": "violacion_directa_por_omision",
                "explicacion": " ".join(["palabra"] * 30)}
    rep["normas_invocadas"] = [n for n in rep["normas_invocadas"] if n["rol"] == "infringida"][:2]
    for n in rep["normas_invocadas"]:
        n.update(hechos=["H2", "H3"], pretensiones=["PR1", "PR2", "PR3"], concepto=concepto)
    rep["escrito"]["fecha_escrito"] = [{"valor": "2026-10-01", "ubicacion": "cierre"}]
    rep["escrito"]["fecha_presentacion"] = "2026-10-02"
    return rep


class TestEscritoConDefectos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inf = correr(cargar())
        cls.incumple = {(r["regla"], r["control"]) for r in cls.inf["resultados"] if r["resultado"] == "INCUMPLE"}

    def test_detecta_los_defectos_decidibles(self):
        esperados = {
            ("COH-01", "H-01"),   # E-02 fecha inexistente
            ("COH-03", "H-09"),   # E-03 acto con dos fechas
            ("COH-06", "H-03"),   # E-04 montos distintos
            ("COH-08", "H-05"),   # E-05 numeración
            ("COH-05", "H-02"),   # E-06 cédula compartida
            ("COH-02", "H-01"),   # E-07 cronología imposible
            ("CA-07", "C-04"),    # E-09 sin concepto de la infracción
            ("CON-01", "C-01"),   # E-10 pretensión sin hechos
            ("CON-02", "C-02"),   # E-11 hechos sin prueba
            ("CON-04", "C-03"),   # E-08 normas sin conexión
            ("CA-09", "C-08"),    # agotamiento no acreditado
        }
        self.assertEqual(esperados - self.incumple, set())

    def test_reglas_sin_verificar_son_preguntas(self):
        self.assertEqual(por_regla(self.inf, "CA-10")[0]["resultado"], "PREGUNTA")   # E-12
        self.assertEqual(por_regla(self.inf, "CA-11")[0]["resultado"], "PREGUNTA")   # E-13

    def test_lo_no_decidible_va_a_zona_interpretativa(self):
        nd = [r for r in self.inf["resultados"] if r["resultado"] == "NO_DETERMINABLE"]
        self.assertTrue(nd)
        self.assertTrue(all(r["zona"] == "interpretativa" for r in nd))
        self.assertTrue(por_regla(self.inf, "INT-02"))  # E-15 fallo: nunca se confirma
        self.assertEqual(por_regla(self.inf, "CA-12")[0]["resultado"], "NO_DETERMINABLE")

    def test_cuenta_criticos(self):
        self.assertGreater(self.inf["criticos"], 0)
        self.assertFalse(self.inf["formalizacion_confirmada"])


class TestEscritoLimpio(unittest.TestCase):
    def test_sin_incumplimientos(self):
        inf = correr(escrito_limpio())
        malos = [r for r in inf["resultados"] if r["resultado"] in ("INCUMPLE", "PREGUNTA")]
        self.assertEqual(malos, [], json.dumps(malos, ensure_ascii=False, indent=1))
        self.assertEqual(inf["criticos"], 0)


class TestPlazos(unittest.TestCase):
    def regla(self, **extra):
        r = {"id": "T", "control": "C-08", "descripcion": "plazo", "base": "x", "estado": "C-1", "severidad": "CRÍTICO",
             "comprobacion": {"tipo": "plazo", "desde": "@notificacion_acto_que_agota_via",
                              "hasta": "@fecha_presentacion_o_escrito", "cantidad": 2, "unidad": "meses",
                              "computo": {"dia_inexistente": "ultimo_del_mes", "prorroga_si_inhabil": True}}}
        r["comprobacion"].update(extra)
        return r

    def evaluar(self, rep, regla, cal=None):
        return ve.evaluar_regla(rep, regla, {}, cal or ve.Calendario({}))[0]

    def test_meses_dentro_y_fuera(self):
        rep = escrito_limpio()  # notificación 2026-08-10 → vence 2026-10-10 (sábado) → lunes 12
        self.assertEqual(self.evaluar(rep, self.regla()).resultado, "NO_DETERMINABLE")  # margen corto, 2026 sin calendario
        cal = ve.Calendario({"anios": {"2026": []}})
        r = self.evaluar(rep, self.regla(), cal)
        self.assertEqual(r.resultado, "CUMPLE")
        self.assertIn("2026-10-12", r.detalle)
        rep["escrito"]["fecha_presentacion"] = "2026-10-13"
        self.assertEqual(self.evaluar(rep, self.regla(), cal).resultado, "INCUMPLE")

    def test_margen_amplio_no_requiere_calendario(self):
        rep = escrito_limpio()
        rep["escrito"]["fecha_presentacion"] = "2026-08-20"
        self.assertEqual(self.evaluar(rep, self.regla()).resultado, "CUMPLE")

    def test_feriado_prorroga(self):
        rep = escrito_limpio()
        rep["escrito"]["fecha_presentacion"] = "2026-10-13"
        cal = ve.Calendario({"anios": {"2026": ["2026-10-12"]}})  # día ficticio inhábil
        r = self.evaluar(rep, self.regla(), cal)
        self.assertEqual(r.resultado, "CUMPLE")
        self.assertIn("2026-10-13", r.detalle)

    def test_ultimo_dia_del_mes(self):
        self.assertEqual(ve.sumar_meses(dt.date(2026, 12, 31), 2, "ultimo_del_mes"), dt.date(2027, 2, 28))
        self.assertIsNone(ve.sumar_meses(dt.date(2026, 12, 31), 2, "error"))

    def test_dias_habiles_exigen_calendario(self):
        rep = escrito_limpio()
        regla = self.regla(cantidad=5, unidad="dias_habiles")
        self.assertEqual(self.evaluar(rep, regla).resultado, "NO_DETERMINABLE")
        cal = ve.Calendario({"anios": {"2026": []}})
        r = self.evaluar(rep, regla, cal)  # 2026-08-10 (lunes) + 5 hábiles = 2026-08-17
        self.assertIn("2026-08-17", r.detalle)

    def test_regla_sv_degrada_incumplimiento(self):
        rep = escrito_limpio()
        rep["escrito"]["fecha_presentacion"] = "2027-01-15"
        regla = self.regla()
        regla["estado"] = "SV"
        self.assertEqual(self.evaluar(rep, regla).resultado, "PREGUNTA")


class TestCorpus(unittest.TestCase):
    def preparar(self, estado="C-1"):
        d = tempfile.TemporaryDirectory()
        datos = {"cuerpo_id": "ley-x", "versiones": [
            {"vigente_desde": "2000-01-01", "vigente_hasta": "2019-12-31", "estado": estado, "fuente": "G.O. antigua",
             "articulos": {"5": "Texto antiguo del artículo cinco."}},
            {"vigente_desde": "2020-01-01", "vigente_hasta": None, "estado": estado, "fuente": "G.O. ficticia",
             "articulos": {"5": "Toda persona tiene derecho a ser oída dentro de un plazo razonable."}}]}
        (Path(d.name) / "ley-x.json").write_text(json.dumps(datos), encoding="utf-8")
        self.addCleanup(d.cleanup)
        return Path(d.name)

    def rep(self, articulo="5", cita=None, fecha_rel=None):
        rep = escrito_limpio()
        n = rep["normas_invocadas"][0]
        n.update(cuerpo_id="ley-x", articulo=articulo, cita_textual=cita, fecha_relevante=fecha_rel)
        return rep

    def cotejo(self, rep, corpus):
        # Solo la primera norma remite a 'ley-x'; las demás quedan fuera del corpus (COR-00).
        return {r.regla: r for r in ve.cotejar_corpus(rep, corpus) if r.regla in ("COR-02", "COR-03")}

    def test_cita_literal(self):
        c = self.cotejo(self.rep(cita="“ser oída  dentro de un plazo razonable”"), self.preparar())
        self.assertEqual(c["COR-02"].resultado, "CUMPLE")
        self.assertEqual(c["COR-03"].resultado, "CUMPLE")

    def test_cita_alterada(self):
        c = self.cotejo(self.rep(cita="ser oída en un plazo breve"), self.preparar())
        self.assertEqual(c["COR-03"].resultado, "INCUMPLE")

    def test_articulo_inexistente(self):
        c = self.cotejo(self.rep(articulo="99"), self.preparar())
        self.assertEqual(c["COR-02"].resultado, "INCUMPLE")

    def test_version_por_fecha(self):
        c = self.cotejo(self.rep(cita="Texto antiguo", fecha_rel="2010-05-05"), self.preparar())
        self.assertEqual(c["COR-03"].resultado, "CUMPLE")

    def test_fuente_secundaria_no_confirma(self):
        c = self.cotejo(self.rep(cita="plazo razonable"), self.preparar("C-2"))
        self.assertEqual(c["COR-03"].resultado, "CUMPLE_CONDICIONADO")
        c = self.cotejo(self.rep(articulo="99"), self.preparar("C-2"))
        self.assertEqual(c["COR-02"].resultado, "PREGUNTA")


class TestEsquemaYCli(unittest.TestCase):
    def test_referencia_rota(self):
        rep = cargar()
        rep["pretensiones"][0]["hechos"] = ["H99"]
        with self.assertRaises(ve.ErrorEsquema) as cm:
            correr(rep)
        self.assertTrue(any("H99" in e for e in cm.exception.errores))

    def test_enumerado_invalido_y_campo_faltante(self):
        rep = cargar()
        rep["pruebas"] = [{"id": "PB1", "descripcion": "x", "estado": "quizas"}]
        del rep["hechos"][0]["texto"]
        with self.assertRaises(ve.ErrorEsquema) as cm:
            correr(rep)
        self.assertEqual(len(cm.exception.errores), 2)

    def test_mencion_mal_formada(self):
        rep = cargar()
        rep["acto_impugnado"]["fecha"] = "2026-03-03"
        with self.assertRaises(ve.ErrorEsquema):
            correr(rep)

    def test_ruta(self):
        rep = cargar()
        self.assertEqual(ve.resolver_ruta(rep, "partes[rol=demandada].nombre")[0][0]["valor"], "Ministerio de Ejemplo")
        self.assertEqual(ve.resolver_ruta(rep, "partes[rol=perito].nombre"), [])

    def test_codigos_de_salida(self):
        with tempfile.TemporaryDirectory() as d:
            limpio = Path(d) / "limpio.json"
            limpio.write_text(json.dumps(escrito_limpio()), encoding="utf-8")
            roto = Path(d) / "roto.json"
            roto.write_text("{", encoding="utf-8")
            invalido = Path(d) / "invalido.json"
            invalido.write_text("{}", encoding="utf-8")
            casos = [(FIXTURE, 1), (limpio, 0), (roto, 2), (invalido, 3)]
            for ruta, esperado in casos:
                with self.subTest(ruta=ruta.name), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    self.assertEqual(ve.main([str(ruta), "--corpus", d]), esperado)

    def test_salida_markdown(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            ve.main([str(FIXTURE)])
        md = buf.getvalue()
        for seccion in ("Zona verificada — incumplimientos", "Zona interpretativa", "ADVERTENCIA"):
            self.assertIn(seccion, md)


class TestReglasPorMateria(unittest.TestCase):
    TIPOS = sorted(p.stem for p in REGLAS.glob("*.json"))

    def test_todas_las_materias_cargan_y_se_ejecutan(self):
        self.assertGreaterEqual(len(self.TIPOS), 9)
        for tipo in self.TIPOS:
            with self.subTest(tipo=tipo):
                rep = cargar()
                rep["escrito"]["tipo"] = tipo
                inf = correr(rep)
                self.assertTrue(inf["reglas_aplicadas"])
                ids = [r["regla"] for r in inf["resultados"]]
                self.assertEqual(len([i for i in ids if i.startswith("REQ-00")]), 0)

    def test_reglas_bien_formadas(self):
        for tipo in self.TIPOS:
            datos = json.loads((REGLAS / f"{tipo}.json").read_text(encoding="utf-8"))
            for r in datos["reglas"]:
                with self.subTest(tipo=tipo, regla=r.get("id")):
                    self.assertTrue({"id", "control", "descripcion", "base", "estado", "comprobacion"} <= r.keys())
                    self.assertIn(r["estado"], {"C-1", "C-2", "SV"})
                    if r["comprobacion"]["tipo"] != "manual":
                        self.assertIn(r["severidad"], ve.SEVERIDADES)

    def test_tipo_desconocido_usa_reglas_generales(self):
        rep = cargar()
        rep["escrito"]["tipo"] = "recurso_de_casacion_inexistente"
        inf = correr(rep)
        self.assertEqual(por_regla(inf, "REQ-00")[0]["resultado"], "NO_DETERMINABLE")
        self.assertTrue(por_regla(inf, "G-05"))

    def test_herencia_y_exclusion(self):
        reglas, generico = ve.cargar_reglas(REGLAS, "laboral_demanda")
        ids = {r["id"] for r in reglas["reglas"]}
        self.assertFalse(generico)
        self.assertIn("G-08", ids)          # heredada
        self.assertNotIn("G-01", ids)       # excluida (la sustituye LAB-01)
        self.assertIn("LAB-04", ids)

    def test_inclusion_circular(self):
        with tempfile.TemporaryDirectory() as d:
            for a, b in (("a", "b"), ("b", "a")):
                (Path(d) / f"{a}.json").write_text(json.dumps({"incluye": [b], "reglas": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                ve.cargar_reglas(Path(d), "a")

    def test_laboral_domicilio_del_demandado(self):
        rep = cargar()
        rep["escrito"]["tipo"] = "laboral_demanda"
        self.assertEqual(por_regla(correr(rep), "LAB-04")[0]["resultado"], "INCUMPLE")
        rep["partes"][2]["domicilio"] = [{"valor": "Ciudad de Panamá", "ubicacion": "introducción"}]
        self.assertEqual(por_regla(correr(rep), "LAB-04")[0]["resultado"], "CUMPLE")

    def test_manual_va_a_zona_interpretativa(self):
        rep = cargar()
        rep["escrito"]["tipo"] = "agrario_demanda"
        r = por_regla(correr(rep), "AGR-01")[0]
        self.assertEqual((r["resultado"], r["zona"]), ("NO_DETERMINABLE", "interpretativa"))
        self.assertIn("actividad agraria", r["detalle"])

    def test_computo_sin_verificar_degrada_plazo(self):
        rep = escrito_limpio()
        rep["escrito"]["tipo"] = "contratacion_impugnacion"
        rep["acto_impugnado"]["fecha_notificacion"] = [{"valor": "2026-08-03", "ubicacion": "hecho"}]
        rep["escrito"]["fecha_presentacion"] = "2026-08-31"
        cal = Path(tempfile.mkdtemp()) / "cal.json"
        cal.write_text(json.dumps({"anios": {"2026": []}}), encoding="utf-8")
        r = por_regla(correr(rep, cal=cal), "CP-01")[0]
        self.assertEqual(r["resultado"], "PREGUNTA")   # vencido, pero el cómputo está SIN VERIFICAR
        self.assertIn("2026-08-10", r["detalle"])


if __name__ == "__main__":
    unittest.main()
