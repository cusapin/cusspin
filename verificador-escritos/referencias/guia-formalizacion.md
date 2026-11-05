# Guía de formalización del escrito

La formalización convierte el escrito en la representación estructurada que exige
`motor/esquema_escrito.json`. Es el único punto donde el juicio del asistente entra en la
zona verificada: si la representación es infiel, el motor verificará con exactitud un escrito
que no existe. Por eso rige esta guía y la representación siempre se somete a la
confirmación del apoderado.

## Reglas

1. **Registrar lo que el escrito dice, no lo que debería decir.** No corregir fechas,
   montos, nombres ni numeraciones. Un dato erróneo se registra erróneo.
2. **Cada mención por separado.** Si el escrito menciona un dato varias veces, registrar
   cada mención con su ubicación (`introducción`, `hecho cuarto`, `petitoria`, `pág. 3`).
   Si todas coinciden, basta con registrar las que estén en lugares distintos y relevantes.
   La discrepancia entre menciones es lo que el motor detecta.
3. **Formatos.** Fechas: `AAAA-MM-DD`, aun si la fecha es imposible (`2026-02-30`).
   Montos: número con punto decimal, sin separador de miles (`50300.00`). Si un monto
   aparece en letras y en cifras con valores distintos, son dos menciones.
4. **Lo que no consta no se inventa.** Campo ausente o lista vacía. `poder.consta`,
   `agotamiento.consta` y `formalizacion.confirmada_por_apoderado` solo son `true` si
   hay base en el escrito o en sus anexos (o, en el último caso, si el apoderado lo confirma
   de manera expresa).
5. **Vínculos.** Un hecho se vincula a una pretensión, una prueba a un hecho y una norma a
   hechos y pretensiones **solo si el escrito establece la conexión**, expresamente o por
   referencia inequívoca. Si el asistente infiere un vínculo que el escrito no establece, no
   lo registra: lo anota en `formalizacion.observaciones` y lo propone como corrección del
   escrito. Un vínculo inventado oculta exactamente el defecto de congruencia que se busca.
6. **Hechos esenciales.** `esencial: false` solo para hechos claramente accesorios (p. ej.,
   circunstancias de contexto). Ante la duda, `true`.
7. **Concepto de la infracción.** Copiar en `concepto.explicacion` el texto que el escrito
   dedica a explicar por qué el acto viola esa norma concreta; `modalidad`, la que el
   escrito declara o la que resulta inequívoca. Si el escrito solo enumera la norma,
   `concepto: null`. No redactar el concepto que falta.
8. **Identificadores del corpus (`cuerpo_id`).** Minúsculas y guiones: `ley-135-1943`,
   `ley-38-2000`, `codigo-judicial`, `codigo-procesal-civil`, `constitucion-politica`,
   `cadh` (Convención Americana), `pidcp`. Debe coincidir con el nombre del archivo en
   `motor/corpus/`.
9. **Citas textuales.** `cita_textual` se llena solo con lo que el escrito presenta entre
   comillas o en bloque como transcripción literal.
10. **Tipo de escrito.** `escrito.tipo` debe ser el nombre de un archivo de
    `motor/reglas/` (hoy: `contencioso_plena_jurisdiccion`). Si no existe el tipo, se usa
    el más cercano solo si el apoderado lo autoriza; si no, el motor reportará que no hay
    reglas y los requisitos formales quedan en la zona interpretativa.
11. **Fecha de presentación.** `escrito.fecha_presentacion` la aporta el apoderado (real o
    prevista). Sin ella, el motor usa la fecha del escrito y lo advierte.

## Confirmación

Junto con la representación, el asistente entrega una lista breve de las decisiones de
formalización que admiten duda (vínculos no registrados, hechos tratados como no esenciales,
modalidades asumidas) para que el apoderado las confirme o corrija. Solo después se cambia
`confirmada_por_apoderado` a `true`.
