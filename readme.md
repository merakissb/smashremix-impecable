# 🇨🇱 Build Impecable — Edición Team CL

Build de Super Smash Bros. 64 mantenida por la comunidad chilena de Smash 64.

> Construida sobre **Smash Remix**, el mod de Super Smash Bros. 64 organizado por
> The_Smashfather. Todo el motor, los personajes y los escenarios vienen de ahí. Este repo
> solo agrega música y ajustes propios.

Requiere el **Expansion Pak de 8 MB**.

---

## El preset Impecable

Esta build viene con el preset de música **"Impecable"**, decidido democráticamente por el
Team CL y los Impecables tras un debate largo, tenso y absolutamente innecesario.

**Resultado de la votación original:**

| Pista | Votos |
|---|---|
| Rock Solid (Conker's Bad Fur Day) | Todos |
| Cualquier otra cosa | 0 |

La playlist tenía exactamente una canción. Era la correcta.

Desde entonces se agregaron algunas más, con bastante menos ceremonia:

| Pista | Origen |
|---|---|
| Rock Solid | Conker's Bad Fur Day |
| Cammy's Stage | Super Street Fighter II |
| Ken's Stage | Super Street Fighter II |
| Trunks Battle | Dragon Ball Z: Super Butōden 3 |

**Para cargarlo:** `OPTION` → `Music Settings` → `Load Profile:` → `Impecable` → botón A.

Con `Random Music` activado y el perfil Impecable cargado, suena solo esa lista.

Saludos a **Dannyssb**, **alpha**, **diego**, **merakissb**, **Afro** y a toda la comu que
lleva años haciendo que esto siga vivo.

*(Se aceptan PRs para agregar más pistas al preset. Serán revisados. Probablemente
rechazados.)*

---

## Compilar

> Esto es solo para quien quiera tocar el código. Si solo querés jugar, bajá la release.

1. Conseguí un ROM de Smash 64 legalmente y aplicale el xdelta incluido (`original.xdelta`).
   Un ROM vanilla **no funciona** — buena parte de las ediciones ocurren dentro de los
   archivos comprimidos del ROM, y el parche los deja en el estado que espera el código ASM.
2. Poné el ROM parcheado en la carpeta `roms/` con el nombre `ssb.rom`.
3. Ejecutá el ensamblador (`assembler/`).

---

## Agregar una canción

Esta es la parte que más cuesta y donde es fácil perder horas. El resumen de lo aprendido a
los golpes.

### 1. Preparar el MIDI

El banco de instrumentos del juego **no es General MIDI**. Tiene 70 instrumentos y el número
de programa es un índice directo a ese banco.

- **Todo programa debe estar entre 1 y 70.** Un programa fuera de rango (0, o 71+) **mata el
  audio del juego entero** en el instante en que entra ese canal. No falla al empezar la
  canción: suena bien un rato y de golpe se corta todo. Es el error más común y el más
  confuso de diagnosticar.
- **El programa 18 es la percusión.** Los tutoriales de internet lo llaman "Rock Organ"
  porque leen nombres GM. La pista de batería va con programa 18.
- **El canal da igual.** No hay canal de batería reservado como en GM; el instrumento sale
  solo del número de programa. Podés poner la batería en cualquier canal.
- **Bank select en 0.** Las 330 pistas del proyecto usan bank 0. Fuera de eso es territorio
  no probado.
- **El editor te muestra el nombre GM del programa, no el instrumento real.** Que diga
  "055 = Orchestra Hit" no significa que suene a orchestra hit — en este banco el 55 da
  "Synth (Alt)" y el orchestra hit real es el 54. Están corridos en uno. Guiate por la tabla
  de abajo, no por el nombre que muestra el editor.
- **Las columnas de SoundFont son solo monitoreo.** Al ROM viaja únicamente el número de
  programa. El `.sf2` no se inyecta en ningún lado: sirve para escuchar en el editor algo
  parecido a lo que dará el juego. Hay copias de referencia en `src/music/sf2/`.

### 2. Convertir

Se usa el **Goldeneye Setup Editor** (`Tools > Extra Tools > MIDI Tools > Convert Midi to GE
Format and Loop`) para generar el `.bin`.

Verificá que el archivo salga **con marcadores de loop**. Algunas herramientas los borran, y
sin ellos la pista suena una vez y se queda muda.

El resultado va en `src/music/`. **El nombre no puede llevar guiones medios** — es también el
identificador del ensamblador, así que solo letras, números y guion bajo:
`KEN_STAGE.bin`, no `ken-stage.bin`.

### 3. Registrar

Tres archivos:

**`src/midi.asm`** — al final de la lista de `insert_midi`, nunca en el medio (el id sale de
la posición, y meter una al medio corre todas las de abajo):

```asm
insert_midi(KEN_STAGE, OS.TRUE, OS.TRUE, "Ken's Stage", ssf2, 901)
```

El último parámetro es el orden en el menú. Las pistas propias usan **900+** para quedar
siempre al final, por encima de cualquier cosa que agregue el proyecto original.

Si el juego de origen no existe todavía, agregalo antes con
`add_game(ssf2, "Super Street Fighter II")`.

**`src/Toggles.asm`** — para que el perfil Impecable la encienda al cargarlo desde
`LOAD PROFILE`:

```asm
add_to_impecable_music(KEN_STAGE)
```

Ojo: va el `file_name` de `insert_midi`, no el título. El perfil apaga **todas** las pistas
primero y luego enciende solo las que estén listadas ahí, así que si una canción no aparece
en el juego, es casi seguro que falta esta línea.

**`src/SRAM.asm`** — subí `REVISION` en uno. Es obligatorio al agregar una pista, un
escenario o un toggle: si no, los datos guardados quedan desincronizados.

### 4. Si suena mal

- **Se corta todo el audio** → casi seguro un programa fuera de rango. Revisá los `Cn`.
- **La batería no suena** → programa 0 en vez de 18.
- **Suena pero con el instrumento equivocado** → estás leyendo nombres GM. Usá la tabla.
- **Se pierden notas en pasajes densos** → polifonía. La N64 tiene pocas voces. Se ajusta con
  `add_priority_override({MIDI.id.PISTA}, <instrumento>, 0x7F)` en `midi.asm`, marcando lo
  que no debe caerse nunca (batería, bajo, melodía). Cuidado: la prioridad es **por
  instrumento, no por pista**, así que dos pistas con el mismo programa no se pueden
  diferenciar — dales programas distintos de timbre parecido si necesitás separarlas.
- **Un pasaje suena feo también en el editor** → no es la consola. Suele ser que esa pista se
  va a un registro donde el sample se rompe. Cambiá el instrumento por otro de la misma
  familia.

---

## Tabla de instrumentos

Índice → instrumento real en el juego. Los 1-42 son los del ROM original; los 43-70 los
agrega Smash Remix vía `add_instrument()` en `src/midi.asm`. **Del 71 en adelante no hay
nada, y el 0 tampoco existe.**

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

## Estructura

| Ruta | Qué hay |
|---|---|
| `src/music/*.bin` | Las pistas, en formato MIDI comprimido de libultra |
| `src/music/sf2/` | SoundFonts de referencia para componer |
| `src/music/profiles/` | Music profiles del proyecto original (Impecable no usa esto) |
| `src/music/instruments/` | Samples `.aifc` de los instrumentos 43-70 |
| `src/midi.asm` | Registro de pistas, banco de instrumentos, overrides de prioridad |
| `src/Toggles.asm` | Perfiles de toggles, incluido Impecable |
| `src/SRAM.asm` | `REVISION` — subila al agregar contenido |
| `roms/` | Acá va tu `ssb.rom` parcheado (no versionado) |

Para el detalle del motor, los personajes y los escenarios, andá a la documentación de Smash
Remix.
