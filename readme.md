# Build Impecable — Edición Team CL

Build de Super Smash Bros. 64 mantenida por la comunidad chilena de Smash 64. El foco de este
repositorio es la música: se agregan pistas propias y se documenta el proceso de importarlas.

> Construida sobre **Smash Remix**, el mod de Super Smash Bros. 64 organizado por
> The_Smashfather. El motor, los personajes y los escenarios provienen de ahí; este repositorio
> solo agrega música y ajustes de configuración.

Requiere el **Expansion Pak de 8 MB**.

---

## El preset Impecable

La build incluye un perfil de configuración llamado **"Impecable"** que deja el juego listo
para partidas: reglas de torneo, resultados rápidos, y una lista curada de música con
reproducción aleatoria activada.

**Para cargarlo:** `OPTION` → `Music Settings` → `Load Profile:` → `Impecable` → botón A.

Ajustes que aplica el perfil:

| Ajuste | Valor |
|---|---|
| Random Music | ON |
| Menu Music | Mario Party |
| Skip Results Screen | ON |
| Stage Select Layout | Tournament |

Música incluida en el perfil (además de las vanilla que se activen):

| Pista | Origen |
|---|---|
| Rock Solid | Conker's Bad Fur Day |
| Clock Tower | Marvel vs. Capcom 2 |
| Gang-Plank Galleon | Donkey Kong Country |
| Luna Ascension | Tower of Heaven |
| Ole! | Conker's Bad Fur Day |
| SMB2 Overworld | Super Mario Bros. 2 |
| Theme of Morrigan | Marvel vs. Capcom |
| Cammy's Stage | Super Street Fighter II |
| Ken's Stage | Super Street Fighter II |
| Trunks Battle | DBZ: Super Butōden 3 |
| Rhythmical Bustle | Melty Blood |
| We Gotta Power | Dragon Ball Z |
| Dan Dan Kokoro Hikareteku | Dragon Ball GT |
| Butouden 3 Credits | DBZ: Super Butōden 3 |
| Mega Man 3 Title | Mega Man 3 |
| Mega Man 7 Intro | Mega Man 7 |

El detalle de instrumentos y volumen de cada pista está en **[MUSICA.md](MUSICA.md)**.

Créditos a **Dannyssb**, **alpha**, **diego**, **merakissb**, **Afro** y a la comunidad que
mantiene esto vivo.

---

## Compilar

> Solo para trabajar con el código fuente. Para jugar, usá la release.

1. Conseguí un ROM de Smash 64 legalmente y aplicale el xdelta incluido (`original.xdelta`).
   Un ROM vanilla **no funciona**: buena parte de las ediciones ocurren dentro de los archivos
   comprimidos del ROM, y el parche los deja en el estado que espera el código ASM.
2. Poné el ROM parcheado en `roms/` con el nombre `ssb.rom`.
3. Ejecutá el ensamblador (`assembler/`).

---

## Formato de música

Las pistas viven en `src/music/*.bin`, en el **formato de secuencia MIDI comprimido de
libultra** (el runtime de audio de la N64). No son archivos MIDI estándar: son la
representación que el reproductor del juego consume directamente. Entender el formato es lo
que permite diagnosticar por qué una pista falla.

### Estructura del archivo

```
offset 0x00 .. 0x3F   16 punteros u32 (big-endian), uno por pista.
                      Cada uno apunta al inicio de esa pista dentro del archivo.
                      Un puntero en 0x00000000 = pista no usada.
offset 0x40 .. 0x43   división (ticks por negra), u32.
offset 0x44 ..        datos de las pistas, concatenados.
```

Hay 16 slots de pista, uno por canal MIDI. Un `.mid` con más de 16 pistas se trunca al
convertir (el GE Editor avisa con "Too many tracks, truncated to 16"); en la práctica las
pistas que sobran suelen ser metadatos vacíos.

### Eventos de una pista

Cada pista es un flujo de `delta-time` (longitud variable, big-endian, bit alto = continúa)
seguido de un evento. Los eventos relevantes:

| Bytes | Evento | Notas |
|---|---|---|
| `9n nota vel <dur>` | Note-on | `n` = canal. La duración va **empaquetada** como varlen tras la velocidad; no hay note-off separado. |
| `Bn cc val` | Control Change | Volumen (`cc`=7), paneo (`cc`=10), expresión (`cc`=11), bank select (`cc`=0). |
| `Cn prog` | Program Change | `prog` = instrumento. Ver más abajo. |
| `En lo hi` | Pitch Bend | |
| `FF 51 tt tt tt` | Tempo | microsegundos por negra. |
| `FF 2E 00 FF` | Inicio de loop | ancla de retorno. |
| `FF 2D rr rr bb bb bb bb` | Fin de loop | `bb..` = offset de retorno (ver abajo). |
| `FF 2F 00` | Fin de pista | |
| `FE ..` | Evento interno del runtime | longitud variable; usado para timing/streaming. |

### Cómo se codifica el loop

El loop se marca por pista con un par `FF 2E` / `FF 2D`:

- **`FF 2E 00 FF`** va casi al inicio de la pista. Es solo un ancla: marca el punto al que se
  volverá.
- **`FF 2D`** va antes del fin de pista y lleva un puntero de retorno de 4 bytes (u32
  big-endian). Son los 2 bytes intermedios un contador de repeticiones (`FF FF` = infinito en
  todas las pistas observadas).

El offset de retorno es **relativo hacia atrás**. Al alcanzar el `FF 2D`, el reproductor salta a:

```
destino = (posición_del_FF2D + 8) − offset_de_retorno
```

que está construido para caer justo después del `FF 2E`. Como el ancla está al principio de la
pista, el resultado es un loop de la pista completa. Al convertir con el GE Editor, el diálogo
"loop point" pide el tick de retorno: **0** = volver al inicio (loop completo).

Una pista **sin** los marcadores `FF 2E`/`FF 2D` no loopea: al llegar al `FF 2F 00` la música
se detiene. Verificar su presencia es el chequeo más importante tras convertir.

### Volumen

El volumen de cada canal es el **CC7** (Channel Volume, 0-127) fijado en el bloque de
inicialización de la pista. La referencia útil es la mediana del proyecto: **117** (p25=100,
p75=124). Una pista muy por debajo de ~100 se oirá apagada frente al resto del juego; una en
127 puede dominar la mezcla.

Para reajustar el volumen sin reexportar, el CC7 es un único byte por pista y se puede editar
en el `.bin`. Para bajar/subir toda la canción de forma uniforme desde el juego existe
`add_master_volume_override({MIDI.id.PISTA}, valor)` en `src/midi.asm` (afecta la pista entera,
no un canal individual).

Los valores actuales de todas las pistas están en **[MUSICA.md](MUSICA.md)**.

---

## Agregar una canción

### 1. Preparar el MIDI

El banco de instrumentos del juego **no es General MIDI**. Tiene 70 entradas, y el número de
programa es un índice directo a ese banco.

- **Todo programa debe estar entre 1 y 70.** Un programa fuera de rango (0, o 71+) **corta el
  audio del juego entero** en el momento en que entra ese canal. No falla al empezar la
  canción: suena bien un rato y de golpe se apaga todo. Es el fallo más común y el más difícil
  de diagnosticar.
- **El programa 18 es la percusión.** Los tutoriales suelen llamarlo "Rock Organ" porque leen
  nombres GM. La pista de batería va con programa 18.
- **El canal es indiferente.** No hay canal de batería reservado como en GM; el instrumento
  depende solo del número de programa.
- **Bank select en 0.** Las pistas del proyecto usan bank 0. Fuera de eso es territorio no
  probado.
- **El editor muestra el nombre GM del programa, no el instrumento real.** "055 = Orchestra
  Hit" no suena a orchestra hit: en este banco el 55 es "Synth (Alt)" y el orchestra hit real
  es el 54 (están corridos en uno). Guiarse por la tabla de abajo, no por el nombre del editor.
- **Las columnas de SoundFont son solo monitoreo.** Al ROM viaja únicamente el número de
  programa; el `.sf2` no se inyecta. Sirve para escuchar en el editor algo parecido a lo que
  dará el juego. Copias de referencia en `src/music/sf2/`.

### 2. Convertir

Usar el **Goldeneye Setup Editor**: `Tools > Extra Tools > MIDI Tools > Convert Midi to GE
Format and Loop`. En el diálogo de "loop point", **0** para loop completo.

Verificar que el `.bin` salga **con marcadores de loop** (ver arriba). Sin ellos la pista suena
una vez y se queda muda.

El resultado va en `src/music/`. **El nombre no puede llevar guiones medios**: es también el
identificador del ensamblador, así que solo letras, números y guion bajo (`KEN_STAGE.bin`, no
`ken-stage.bin`).

### 3. Registrar (tres archivos)

**`src/midi.asm`** — al final de la lista de `insert_midi`, nunca en el medio (el id sale de la
posición; insertar al medio corre los ids de todas las de abajo):

```asm
insert_midi(KEN_STAGE, OS.TRUE, OS.TRUE, "Ken's Stage", ssf2, 901)
```

El último parámetro es el orden en el menú. Las pistas propias usan **900+** para quedar al
final, por encima de lo que agregue el proyecto original. Si el juego de origen no existe,
agregarlo antes con `add_game(ssf2, "Super Street Fighter II")`.

**`src/Toggles.asm`** — para que el perfil Impecable la active al cargarse:

```asm
add_to_impecable_music(KEN_STAGE)
```

Va el `file_name`, no el título. El perfil apaga **todas** las pistas y luego enciende solo las
listadas: si una canción no aparece en el juego, casi siempre falta esta línea.

**`src/SRAM.asm`** — incrementar `REVISION` en uno. Obligatorio al agregar una pista, un
escenario o un toggle; si no, los datos guardados quedan desincronizados.

### 4. Diagnóstico

| Síntoma | Causa probable |
|---|---|
| Se corta todo el audio | Programa fuera de rango (0 o 71+). Revisar los `Cn`. |
| La batería no suena | Programa 0 en vez de 18. |
| Instrumento equivocado | Se está leyendo el nombre GM. Usar la tabla. |
| Suena una vez y para | Falta el loop (`FF 2E`/`FF 2D`). Reconvertir con loop. |
| Se pierden notas en pasajes densos | Polifonía. Ver abajo. |
| Un pasaje suena mal también en el editor | El sample se rompe en ese registro; cambiar de instrumento. |
| Una pista domina o desaparece | Desbalance de CC7. Ver sección de volumen. |

**Polifonía:** la N64 tiene pocas voces simultáneas. Cuando faltan, el motor corta notas por
prioridad. Se ajusta con `add_priority_override({MIDI.id.PISTA}, <instrumento>, 0x7F)` en
`src/midi.asm`, marcando lo que no debe caerse (batería, bajo, melodía). La prioridad es **por
instrumento, no por pista**: dos pistas con el mismo programa no se pueden diferenciar; darles
programas distintos de timbre similar si hace falta separarlas.

---

## Tabla de instrumentos

Índice → instrumento real en el juego. Los 1-42 son del ROM original; los 43-70 los agrega
Smash Remix vía `add_instrument()` en `src/midi.asm`. **Del 71 en adelante no hay nada, y el 0
no existe.**

| # | Instrumento | # | Instrumento | # | Instrumento |
|---|---|---|---|---|---|
| 1 | Flute | 25 | TR-808 Synth Drum | 49 | Distortion Guitar 2 |
| 2 | Organ | 26 | Bass-S.Chord-Piano | 50 | Tenor Sax |
| 3 | Synth Tuba | 27 | Drums+Tubular Bells | 51 | Overdriven Guitar 2 |
| 4 | Synth Wave | 28 | Pan Flute 2 | 52 | Acoustic Grand Piano |
| 5 | Brass | 29 | Synth Accordion | 53 | Slap Bass 1 |
| 6 | Lead Synth | 30 | Trombone | 54 | Orchestra Hit |
| 7 | Strings | 31 | Drum w/ Cowbell | 55 | Synth (Alt) |
| 8 | Electric Piano | 32 | Acoustic Bass | 56 | Missing NES Wave |
| 9 | Kalimba | 33 | Steel Drums | 57 | Nylon Guitar (Alt) |
| 10 | Glockenspiel | 34 | Trumpet | 58 | Sawtooth (K64) |
| 11 | Slap Bass | 35 | Accordion | 59 | Shogo Sakai Slide |
| 12 | Synth Bass | 36 | Bassoon | 60 | OOT Acoustic |
| 13 | Electric Bass | 37 | Clarinet | 61 | Pizzicato (FFXI) |
| 14 | Banjo | 38 | Nylon Guitar | 62 | Shamisen |
| 15 | Choir Aahs | 39 | Muted Gt. | 63 | DK Rap |
| 16 | Pan Flute | 40 | Muted Trumpet | 64 | Roll |
| 17 | Timpani | 41 | Overdriven Guitar | 65 | Yoshis |
| 18 | **Main Percussion** | 42 | Distortion Guitar | 66 | Marimba |
| 19 | Square Wave (NES) | 43 | Rock Organ | 67 | DF Chants |
| 20 | Triangle (NES) | 44 | Choir Ahhs 2 | 68 | Monkeys |
| 21 | White Noise (NES) | 45 | Choir Oohs | 69 | Sine Wave |
| 22 | Orchestral Hit | 46 | Slap Bass (Alt) | 70 | Harp |
| 23 | Drum Roll | 47 | Church Organ | | |
| 24 | Picked Bass-Clav-O. | 48 | Steel Drum 2 | | |

---

## Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `src/music/*.bin` | Pistas, en formato MIDI comprimido de libultra |
| `src/music/sf2/` | SoundFonts de referencia para componer |
| `src/music/profiles/` | Music profiles del proyecto original (Impecable no los usa) |
| `src/music/instruments/` | Samples `.aifc` de los instrumentos 43-70 |
| `src/midi.asm` | Registro de pistas, banco de instrumentos, overrides de prioridad y volumen |
| `src/Toggles.asm` | Perfiles de configuración, incluido Impecable |
| `src/SRAM.asm` | `REVISION` — incrementar al agregar contenido |
| `MUSICA.md` | Instrumentos y volumen de cada pista del proyecto |
| `roms/` | ROM `ssb.rom` parcheado (no versionado) |

Para el detalle del motor, los personajes y los escenarios, consultar la documentación de
Smash Remix.
