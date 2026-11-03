# Fuentes de verificación y jerarquía normativa

> **Estado de este archivo.** Cada dato lleva su estado: **CONFIRMADO (fuente)** cuando fue
> contrastado mediante búsqueda con fuente identificada el 3 de noviembre de 2026;
> **SIN VERIFICAR** cuando proviene de la memoria del modelo. Lo confirmado contra fuente
> secundaria (dictámenes, notas institucionales, repositorios privados) no equivale a
> confirmación contra la Gaceta Oficial. Este archivo debe mantenerlo el despacho.

## 1. Fuentes primarias y su prelación para verificar

| Prelación | Fuente | Qué se verifica allí | Observación |
|---|---|---|---|
| 1 | **Gaceta Oficial Digital** — `gacetaoficial.gob.pa` | Existencia, número, fecha y texto publicado de leyes, decretos y resoluciones. | Fuente de validez de la publicación. Verificar también gacetas posteriores por reformas. |
| 2 | **Infojurídica (Procuraduría de la Administración)** — `infojuridica.procuraduria-admon.gob.pa` | Ficha de la norma, vigencia, reformas y fallos vinculados. | CONFIRMADO que registra la Ley 402 de 2023 con su Gaceta (búsqueda del 3-nov-2026). |
| 3 | **Órgano Judicial** — `organojudicial.gob.pa` (incluye CENDOJ y Registro Judicial) | Fallos de la Corte Suprema y tribunales; instrumentos internacionales compilados por el CENDOJ. | El CENDOJ publica leyes aprobatorias de tratados (p. ej., Ley 14 de 1976). |
| 4 | **Asamblea Nacional** — `asamblea.gob.pa` | Textos legislativos, proyectos, actas. | Útil para historia legislativa. |
| 5 | **Corte Interamericana de Derechos Humanos** — `corteidh.or.cr` | Sentencias contra Panamá, opiniones consultivas, estado de ratificación. | |
| 6 | **Colección de Tratados de la ONU** — `treaties.un.org` | Estado de ratificación, reservas y declaraciones de Panamá. | SIN VERIFICAR para cada tratado concreto; consultar caso por caso. |
| — | Repositorios secundarios (vLex Panamá, Justia Panamá, dictámenes de la Procuraduría) | Localizar fallos y textos. | **Nunca** bastan solos para calificar un dato como CONFIRMADO en el informe; se rotulan "confirmado contra fuente secundaria". |

## 2. Jerarquía normativa (orden de contraste)

1. **Constitución Política** (texto único vigente con sus actos reformatorios).
   - Art. 4: *"La República de Panamá acata las normas del Derecho Internacional."* —
     CONFIRMADO contra fuente secundaria (informe de Panamá al Comité de Derechos Humanos
     de la ONU y doctrina universitaria). La redacción de 1972 contenía una cláusula
     restrictiva que fue suprimida por reforma; verificar en el texto único.
   - Art. 17, párrafo segundo, adicionado por el Acto Legislativo N.º 1 de 2004 (derechos y
     garantías como mínimos, no excluyentes de otros que incidan sobre derechos
     fundamentales) — CONFIRMADO contra fuente académica secundaria; texto literal SIN
     VERIFICAR.
2. **Tratados y convenios internacionales** aprobados por ley y ratificados. Su rango
   interno es materia discutida: según el informe de Panamá ante la ONU, la Corte Suprema
   ha sostenido como regla general que no integran el bloque de constitucionalidad, con
   excepción de ciertas normas de derechos humanos (CONFIRMADO contra fuente secundaria;
   los fallos concretos que lo sostienen están SIN VERIFICAR). **Consecuencia operativa:**
   cuando un escrito invoque un tratado como parámetro de constitucionalidad, el verificador
   debe señalar que esa premisa es discutible y exigir el respaldo jurisprudencial concreto.
3. **Leyes** (orgánicas, ordinarias), **decretos-ley** y códigos.
4. **Decretos ejecutivos** reglamentarios.
5. **Resoluciones, acuerdos** y demás actos administrativos de alcance general.
6. **Actos administrativos de alcance particular** (objeto de impugnación, no de contraste).

## 3. Códigos y leyes de uso frecuente — estado

| Norma | Materia | Estado |
|---|---|---|
| Código Judicial | Organización judicial; procedimientos; Libro IV, instituciones de garantía (inconstitucionalidad, advertencia, amparo, hábeas corpus). | Existencia CONFIRMADA. **Vigencia del Libro II (procedimiento civil) afectada por la Ley 402 de 2023.** Numeración de artículos concretos: ver `requisitos-por-escrito.md`. |
| **Ley 402 de 9 de octubre de 2023**, que adopta el Código Procesal Civil | Procedimiento civil. | CONFIRMADO (Infojurídica; Órgano Judicial): Gaceta Oficial 29887-A de 11-oct-2023; regla general de vigencia a los dos años de su promulgación; vigencias anticipadas parciales (Caps. II y VI del Título I del Libro Segundo y arts. 409 y 410 al año; numerales del art. 1 y arts. 803 a 806 desde la promulgación). **Discrepancia sobre el día de vigencia integral:** el Órgano Judicial menciona en una nota el 11-oct-2025 y en otra el 9-oct-2025. Verificar en la Gaceta y en las normas transitorias antes de afirmar una fecha. |
| Ley 135 de 1943, reformada por Ley 33 de 1946 | Jurisdicción contencioso-administrativa. | CONFIRMADO contra fuente secundaria (dictámenes de la Procuraduría de la Administración). |
| Ley 38 de 2000 | Procedimiento administrativo general. | SIN VERIFICAR (memoria). |
| Ley 63 de 2008 | Código Procesal Penal (sistema acusatorio). | SIN VERIFICAR (memoria). |
| Código Civil, Código de Comercio, Código de Trabajo, Código Penal, Código de la Familia | Sustantivos. | Existencia notoria; numeración de artículos SIN VERIFICAR caso por caso. |

## 4. Reglas de verificación de vigencia

1. Buscar la norma en Infojurídica y revisar el campo de reformas y fallos vinculados.
2. Buscar si fue declarada inconstitucional (total o parcialmente) por el Pleno de la CSJ.
3. Si se cita un **texto único**, confirmar que la numeración citada corresponde al texto
   único y no a la ley original.
4. Si la norma es procesal, verificar el **régimen transitorio**: qué procesos se rigen por
   la norma anterior según la fecha de su inicio.
5. Si no puede confirmarse la vigencia, el hallazgo se reporta con certeza moderada o baja y
   la indicación expresa: "vigencia no confirmada".
