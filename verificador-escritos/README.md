# Verificador de Escritos Jurídicos — República de Panamá

Asistente de IA dedicado a una sola tarea: **verificar la veracidad, la coherencia y la
congruencia** de un escrito jurídico antes de su presentación, conforme al derecho panameño y
a los tratados y convenios aplicables a Panamá. No redacta ni reescribe el escrito: emite un
informe de hallazgos graduados, con una lista de verificación auditable.

## Arquitectura: quien propone y quien comprueba

Siguiendo la lógica de los asistentes de demostración (Lean), el sistema separa a quien
**propone** de quien **comprueba**:

```
 Escrito ──► [ASISTENTE] formaliza ──► representación JSON ──► [APODERADO] confirma
                                                │
                                                ▼
                               [MOTOR] verificar_escrito.py  (determinista, sin IA)
                                 ├─ zona verificada: CUMPLE / INCUMPLE / PREGUNTA
                                 └─ zona interpretativa: NO_DETERMINABLE
                                                │
                                                ▼
             [ASISTENTE] informe: hallazgos [MOTOR · regla] + análisis [ASISTENTE]
```

- **Zona verificada.** Fechas y cronología; identidad del acto, de las partes y de los
  montos; numeración; grafo pretensión → hecho → prueba y norma → hecho/pretensión;
  existencia del concepto de la infracción; requisitos formales; plazos; existencia del
  artículo y literalidad de las citas (cuando la norma está en el corpus). El resultado es
  exacto **respecto de la representación**.
- **Zona interpretativa.** Suficiencia de los argumentos, contenido de los fallos,
  interpretación, normas fuera del corpus. Sigue a cargo del asistente con el régimen de
  certeza, y del apoderado.
- **Brecha de formalización.** Si la representación es infiel al escrito, el motor verifica
  con exactitud un escrito que no existe. Por eso la representación se elabora según
  `referencias/guia-formalizacion.md` y la confirma el apoderado.

## Componentes

| Archivo | Función |
|---|---|
| `SKILL.md` | Protocolo del asistente (fuente única). Pasos 1 a 7, incluidos el 2-bis (formalización) y el 5-bis (motor). |
| `instrucciones-proyecto.md` | El mismo protocolo sin encabezado, listo para pegar en las instrucciones de un proyecto de Claude. **Generado**: no se edita a mano. |
| `referencias/` | Fuentes y jerarquía, requisitos por tipo de escrito, tratados, matriz de 34 controles, plantilla del informe, guía de formalización. |
| `motor/esquema_escrito.json` | Esquema de la representación estructurada del escrito. |
| `motor/verificar_escrito.py` | Motor determinista. Solo biblioteca estándar de Python 3.10+. |
| `motor/reglas/*.json` | Requisitos formales por tipo de escrito, cada uno con base, estado (C-1 / C-2 / SV) y severidad. Hoy: `contencioso_plena_jurisdiccion`. |
| `motor/calendario/feriados_pa.json` | Días inhábiles confirmados por el despacho (vacío: hay que poblarlo). |
| `motor/corpus/` | Textos de normas confirmados contra la Gaceta (vacío: hay que poblarlo; ver su README). |
| `herramientas/extraer_citas.py` | Inventario mecánico de citas y alertas sobre el texto bruto (previo a la formalización). |
| `herramientas/generar_instrucciones.py` | Regenera `instrucciones-proyecto.md` desde `SKILL.md`. |
| `pruebas/` | Escrito ficticio con 17 defectos sembrados, su representación JSON y la lista de hallazgos esperados. |

## Instalación y articulación

`SKILL.md` es la fuente única. Si lo modifica, ejecute
`python3 herramientas/generar_instrucciones.py` y vuelva a pegar
`instrucciones-proyecto.md` donde corresponda.

### Opción 1 — Proyecto de Claude con las instrucciones pegadas (la configuración actual)

1. **Reemplace** las instrucciones del proyecto por el contenido de
   `instrucciones-proyecto.md`. La versión anterior no tiene los Pasos 2-bis y 5-bis: sin
   ellos, el asistente no formaliza ni sabe articularse con el motor.
2. Cargue como conocimiento del proyecto los seis archivos de `referencias/` y
   `motor/esquema_escrito.json` (el asistente lo necesita para formalizar).
3. Active la búsqueda web.
4. **Ejecución del motor:**
   - Si el proyecto tiene habilitada la **ejecución de código** (análisis / creación de
     archivos), adjunte en la conversación `verificar_escrito.py`, el archivo de reglas, y el
     calendario y el corpus si los tiene. El asistente ejecutará el motor (modo A). No he
     podido confirmar si los archivos de conocimiento del proyecto son accesibles desde el
     entorno de ejecución; adjuntarlos en la conversación evita la duda.
   - Si no, el asistente le entregará el JSON y le pedirá que ejecute en su computadora
     (modo B):
     ```bash
     python3 motor/verificar_escrito.py representacion.json > resultado.md
     ```
     y que pegue `resultado.md` en la conversación. El asistente no emite el informe
     definitivo hasta recibirlo.

### Opción 2 — Skill (recomendada a mediano plazo)

Una skill puede llevar consigo los scripts y ejecutarlos, de modo que el motor viaja con el
protocolo y no hay que adjuntarlo cada vez. Comprima la carpeta `verificador-escritos/`
completa y cárguela como skill personalizada en la configuración de Claude (requiere
ejecución de código habilitada), o cópiela a `~/.claude/skills/` para Claude Code. El
nombre de la skill es `verificador-escritos-pa`.

### Flujo de trabajo

1. (Opcional) `python3 herramientas/extraer_citas.py ESCRITO.docx > inventario.md`.
2. Entregue al asistente el escrito, los anexos y la fecha de presentación prevista.
3. El asistente entrega la representación JSON y la lista de decisiones dudosas. Revísela,
   corrija lo necesario y confirme (`"confirmada_por_apoderado": true`).
4. Se ejecuta el motor (modo A o B).
5. El asistente emite el informe: hallazgos `[MOTOR · regla]` y `[ASISTENTE]`
   diferenciados, la salida del motor íntegra, y la zona interpretativa con su certeza.

Código de salida del motor: `0` sin incumplimientos críticos, `1` con incumplimientos
críticos, `2` error de lectura, `3` representación fuera del esquema.

## Pruebas

```bash
cd herramientas && python3 -m unittest -v   # extractor (21 pruebas)
cd ../motor && python3 -m unittest -v       # motor (22 pruebas)
```

## Mantenimiento por el despacho (donde está el rendimiento)

1. **Corpus.** Cargue en `motor/corpus/` las normas que más cita, con su texto literal y su
   Gaceta (estado C-1). Cada norma cargada convierte en exactos la existencia del artículo y
   la literalidad de las citas.
2. **Reglas.** Al confirmar contra la Gaceta un requisito marcado SV o C-2 en
   `motor/reglas/*.json`, cambie su `estado` a `C-1`. Las reglas SV producen PREGUNTA, no
   INCUMPLE. Para otros tipos de escrito (amparo, inconstitucionalidad, advertencia), copie
   el archivo de reglas existente y adáptelo.
3. **Calendario.** Agregue cada año a `feriados_pa.json` solo cuando haya confirmado todos
   sus días inhábiles. Sin el año, los plazos con margen menor de 10 días quedan
   NO_DETERMINABLE.

## Límites

- El motor comprueba la representación, no el escrito: su certeza depende de la
  confirmación del apoderado.
- Las referencias **C-2** fueron confirmadas contra fuentes secundarias, no contra la
  Gaceta Oficial; las **SV** provienen de memoria del modelo.
- Las reglas de cómputo de plazos (meses, prórroga al día hábil siguiente) están marcadas
  SIN VERIFICAR en el archivo de reglas.
- Ninguna capa sustituye la revisión final del apoderado contra fuente primaria.
