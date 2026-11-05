# Guía rápida: instalar y usar el Verificador de Escritos

No necesita saber programar. Solo hará clics y subirá **un archivo**. La instalación se hace
**una sola vez**; luego, para cada escrito, solo adjunta el documento y escribe una frase.

Para instalarlo, use Claude en una computadora (navegador o aplicación de escritorio), no
el teléfono.

Los nombres de los menús pueden variar un poco según la versión de Claude o si está en
español o en inglés. Abajo pongo ambos.

---

## Instalación (una sola vez, unos 5 minutos)

### Paso 1. Descargue el archivo

Descargue **`verificador-escritos-pa.zip`** (se lo envié junto con esta guía) y guárdelo,
por ejemplo, en el Escritorio. **No lo descomprima**: se sube tal cual.

### Paso 2. Active la "ejecución de código"

Esto permite que Claude ejecute el motor de verificación por dentro. Usted no verá código.

1. En Claude, haga clic en su nombre o en sus iniciales (esquina inferior izquierda) y
   abra **Configuración** (*Settings*).
2. Entre en **Capacidades** (*Capabilities*).
3. Active el interruptor **"Ejecución de código y creación de archivos"**. En versiones
   nuevas puede llamarse **"Crear y editar archivos"** (*Code execution and file creation*
   o *Create and edit files*).

### Paso 3. Suba el verificador

1. En la **barra lateral izquierda** de Claude (la columna donde aparecen "Nueva
   conversación", los proyectos y el historial), haga clic en **Personalizar**
   (*Customize*) y luego en **Habilidades** (*Skills*). Si no ve la barra, pulse el ícono
   de panel de la esquina superior izquierda para desplegarla. En algunas cuentas el
   apartado puede llamarse **Plugins**. En diseños anteriores, la opción está en
   **Configuración → Capacidades**, más abajo, en la sección **Habilidades**.
2. Haga clic en **"+"** y luego en **"Crear habilidad"** (*+ Create skill*).
3. Elija **"Subir una habilidad"** (*Upload a skill*).
4. Seleccione el archivo `verificador-escritos-pa.zip` del Paso 1.
5. Compruebe que aparece **verificador-escritos-pa** en la lista con el interruptor
   **encendido**.

### Paso 4. Retire las instrucciones que pegó antes

Las instrucciones que pegó en su proyecto son una versión anterior y entrarían en conflicto
con la nueva.

1. Abra el proyecto donde las pegó.
2. Abra sus **instrucciones** (*Project instructions*), borre todo el texto y guarde.

Si prefiere conservar ese proyecto para otras tareas, basta con que **no use ese proyecto**
para verificar escritos: use una conversación normal.

**Instalación terminada.**

---

## Uso (cada vez que quiera verificar un escrito)

### 1. Abra una conversación nueva

Fuera de cualquier proyecto (botón **"Nueva conversación"**).

### 2. Adjunte el escrito y sus anexos

Use el clip o arrastre los archivos: el escrito (Word o PDF) y, si los tiene, la
resolución impugnada con su notificación, el poder y las pruebas. Sin anexos, el
verificador no puede comprobar la relación entre hechos y pruebas, y se lo dirá.

### 3. Escriba esta frase (puede copiarla)

> Usa mi habilidad verificador-escritos-pa para verificar este escrito. Pienso presentarlo
> el [fecha].

### 4. Responda las preguntas de Claude

Antes del informe, Claude le mostrará un **resumen de su escrito** en tablas (partes, acto
impugnado, pretensiones, hechos, pruebas, normas) y unas pocas **preguntas de sí o no**
sobre puntos dudosos. Revise que el resumen refleje fielmente su escrito y responda, por
ejemplo:

> Confirmo. Pregunta 1: sí. Pregunta 2: no, el hecho tercero también sostiene la pretensión
> de reintegro.

Este paso es **su control de calidad**: la verificación automática es exacta respecto de
ese resumen, así que el resumen debe ser fiel.

### 5. Lea el informe en este orden

1. **Hallazgos CRÍTICOS**: lo que puede provocar la inadmisión o el rechazo.
2. **PREGUNTAS**: requisitos cuya base legal no está confirmada. No son errores: son
   puntos que usted debe confirmar.
3. **SIN VERIFICAR**: normas y fallos que debe cotejar en la Gaceta Oficial o en el
   Registro Judicial.
4. El resto, por severidad.

Cada hallazgo indica su origen:
- **[MOTOR · …]**: comprobado mecánicamente, sin IA (fechas, montos, numeración, hechos
  sin prueba, requisitos formales). Alta fiabilidad.
- **[ASISTENTE]**: análisis jurídico de la IA. Léalo con el grado de certeza que indica.

---

## Si algo no funciona

| Lo que ve | Qué hacer |
|---|---|
| No encuentra "Habilidades" (*Skills*) | Revise el Paso 2: sin la ejecución de código, las habilidades no aparecen o salen en gris. Si su cuenta es de una organización (plan Team o Enterprise), el administrador debe habilitarlas en *Organization settings → Plugins & skills*. |
| Error al subir el archivo | Compruebe que subió el **.zip sin descomprimir**. Si persiste, envíeme el texto del error. |
| Claude no usa el verificador | Escriba el nombre exacto, como en el punto 3: *"Usa mi habilidad verificador-escritos-pa"*. |
| El informe dice "PRELIMINAR — el motor no se ejecutó" | La ejecución de código está apagada: repita el Paso 2 y abra una conversación nueva. |
| Claude le muestra código o le pide ejecutar programas | No es necesario. Responda: *"No soy programador; ejecútalo tú"*. |

---

## Qué quedará pendiente (para más adelante, sin urgencia)

El verificador ya funciona. Dos mejoras, que puedo prepararle cuando quiera, aumentarán su
precisión:

1. **Textos oficiales de las normas que más cita** (copiados de la Gaceta Oficial): con
   ellos, el verificador comprobará palabra por palabra que sus citas sean exactas.
2. **El calendario de días feriados** de cada año: con él, calculará los plazos al día.
