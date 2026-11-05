# Corpus verificado de normas

Aquí el despacho guarda los textos de normas **confirmados contra fuente primaria**. Con
ellos, el motor deja de opinar sobre dos cosas y pasa a comprobarlas de forma exacta:

1. que el artículo citado **existe** en esa norma en la versión vigente a la fecha relevante;
2. que la cita textual del escrito es **literal** (cotejo carácter por carácter, tolerando
   solo diferencias de espacios y de tipo de comillas).

El corpus se entrega vacío a propósito: un texto normativo transcrito de memoria sería
exactamente el tipo de dato que este sistema existe para evitar.

## Formato: un archivo por norma, `<cuerpo_id>.json`

```json
{
  "cuerpo_id": "ley-135-1943",
  "titulo": "Ley 135 de 1943, orgánica de la jurisdicción contencioso-administrativa",
  "versiones": [
    {
      "vigente_desde": "1946-00-00",
      "vigente_hasta": null,
      "estado": "C-1",
      "fuente": "Gaceta Oficial N.º ____ de __ de ____ de ____, consultada el AAAA-MM-DD",
      "articulos": {
        "43": "Texto íntegro y literal del artículo tal como aparece en la Gaceta.",
        "43-A": "…"
      }
    }
  ]
}
```

- `vigente_desde` / `vigente_hasta`: fechas AAAA-MM-DD (use la fecha exacta; el ejemplo
  muestra la estructura, no un dato). `null` en `vigente_hasta` = vigente.
- `estado`: `C-1` (Gaceta) o `C-2` (fuente secundaria). Solo `C-1` permite al motor
  informar CONFIRMADO; `C-2` se informa como "coincide con fuente secundaria".
- Cada reforma es una versión nueva; no se sobrescribe la anterior.
- El `cuerpo_id` debe coincidir con el campo `cuerpo_id` de la norma en la representación
  del escrito.
