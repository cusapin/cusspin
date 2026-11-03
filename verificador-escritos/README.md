# Verificador de Escritos Jurídicos — República de Panamá

Asistente de IA dedicado a una sola tarea: **verificar la veracidad, la coherencia y la
congruencia** de un escrito jurídico antes de su presentación, conforme al derecho panameño y
a los tratados y convenios aplicables a Panamá. No redacta ni reescribe el escrito: emite un
informe de hallazgos graduados, con una lista de verificación auditable.

## Componentes

| Archivo | Función |
|---|---|
| `SKILL.md` | Protocolo del asistente: mandato, límites, procedimiento en 7 pasos, severidades, certeza, cuarentena de datos. Es el "cerebro". |
| `referencias/fuentes-y-jerarquia.md` | Fuentes primarias de verificación, prelación, jerarquía normativa, estado de vigencia (incluida la Ley 402 de 2023). |
| `referencias/requisitos-por-escrito.md` | Requisitos formales por tipo de escrito, cada uno con su estado de verificación (C-1 / C-2 / SV). |
| `referencias/tratados.md` | Tratados de uso frecuente con su ley aprobatoria y su estado. |
| `referencias/matriz-de-verificacion.md` | 34 controles (V-01…V-12, H-01…H-10, C-01…C-12). |
| `referencias/plantilla-informe.md` | Estructura obligatoria del informe. |
| `herramientas/extraer_citas.py` | Inventario mecánico: citas, fechas, montos, cédulas; alertas de coherencia; detección de instrucciones ocultas. Sin dependencias. |
| `pruebas/` | Escrito ficticio con 17 defectos sembrados y la lista de hallazgos esperados, para evaluar el asistente tras cada cambio. |

## Instalación

**Opción A — Proyecto de Claude (claude.ai).** Cree un proyecto, pegue el contenido de
`SKILL.md` (sin el encabezado entre `---`) en las instrucciones del proyecto y cargue los
cinco archivos de `referencias/` como conocimiento del proyecto. Active la búsqueda web: el
paso 3 depende de ella para confirmar normas y fallos.

**Opción B — Skill.** Comprima la carpeta `verificador-escritos/` y cárguela como skill
personalizada en la configuración de Claude, o cópiela a `~/.claude/skills/` para Claude
Code. El nombre de la skill es `verificador-escritos-pa`.

**Herramienta de extracción (opcional, local):**

```bash
python3 herramientas/extraer_citas.py MI_ESCRITO.docx > inventario.md
python3 herramientas/extraer_citas.py MI_ESCRITO.docx --formato json
```

Lee `.txt`, `.md`, `.docx` (incluidas notas al pie, encabezados y comentarios, donde suelen
ocultarse instrucciones) y `.pdf` si `pdftotext` está instalado. Entregue el inventario al
asistente junto con el escrito.

**Pruebas:** `cd herramientas && python3 -m unittest -v`

## Uso recomendado

1. Ejecute la herramienta sobre el escrito (opcional).
2. Entregue al asistente el escrito, las pruebas o anexos disponibles y, si la tiene, la
   resolución impugnada con su constancia de notificación. Sin anexos, el asistente no puede
   verificar la correspondencia entre hechos y pruebas, y así lo declarará.
3. Indique el tipo de escrito y la autoridad si no constan.
4. Revise primero los hallazgos CRÍTICOS y la sección SIN VERIFICAR.

## Límites que el despacho debe conocer

- El asistente **no tiene acceso garantizado** a bases jurisprudenciales oficiales. Lo que
  no confirme por búsqueda queda SIN VERIFICAR; no por ello es falso.
- Las referencias marcadas **C-2** fueron confirmadas contra fuentes secundarias (fallos o
  dictámenes que transcriben la norma), no contra la Gaceta Oficial. Las **SV** provienen de
  memoria del modelo. El despacho debe elevar cada referencia a C-1 a medida que la
  confirme, y mantener la fecha de consulta.
- La herramienta automática detecta patrones; no comprende el texto. Una alerta suya es una
  pregunta, no una conclusión.
- Ninguna capa de verificación sustituye la revisión final del apoderado contra fuente
  primaria.
