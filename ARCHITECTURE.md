# Smash Remix — Mapa Técnico del Proyecto

Documento de referencia para futuras modificaciones. Describe la arquitectura, el flujo de
compilación y los sistemas principales tal como están en el estado actual del repositorio
(rama `master`, versión 2.0.1).

---

## 1. Arquitectura general

Smash Remix **no es una aplicación convencional**: es un *ROM hack* de Super Smash Bros. (N64)
escrito íntegramente en **ensamblador MIPS (R4300i)**, ensamblado con **bass** (`assembler/bass.exe`).

El modelo mental correcto es:

1. Se parte de una ROM base de Smash 64 ya preparada (`roms/original.z64`).
2. `main.asm` copia esa ROM completa a la salida.
3. Sobre esa copia se aplican **parches en sitio** (sobrescritura de instrucciones en offsets
   concretos de la ROM original) y se **añade código nuevo** en una región libre al final.
4. El resultado es una ROM `.z64` jugable.

Existen por tanto dos categorías de código, y la distinción es fundamental:

| Categoría | Mecanismo | Dónde vive |
|---|---|---|
| **Parches** (hooks) | `OS.patch_start(rom_offset, ram_address)` … `OS.patch_end()` | Sobrescriben instrucciones del juego original |
| **Código nuevo** | `scope nombre_: { ... }` normal | Región nueva, ROM `0x02C00000` / RAM `0x80400000` |

Un parche típico reemplaza 1–2 instrucciones del juego original por un `jal` a una rutina nueva,
que ejecuta lógica extra, restaura las "original lines" y vuelve.

**Regiones de memoria clave** (definidas en `main.asm`):

- `0x0` → inserción de la ROM original completa.
- `0x20` → nombre interno de la ROM (`"SMASH REMIX"`).
- ROM `0x02C00000` / RAM `0x80400000` → **todo el código y datos nuevos** (todos los `include`).
- ROM `0x3000000` → **banco de MIDIs** (`MIDI.MIDI_BANK`, ver §7).
- `midi_memory_block` → buffer en RAM donde se cargan los MIDIs; su tamaño es
  `MIDI.largest_midi`, calculado en tiempo de ensamblado.
- `file_table` → tabla de archivos reubicada (`0x620` bytes) para permitir más archivos.
- `custom_heap` → heap ampliado.
- ROM se rellena hasta `0x3E7FFFF` (64 MB).

---

## 2. Flujo de compilación

### 2.1 Preparación de la ROM base (una sola vez)

```
ROM legal "Super Smash Bros. (U) [!].z64"
        │
        ├── (a) xdelta.exe + original.xdelta        ← "xdelta - apply original.bat"
        │       genera roms/original.z64
        │
        └── (b) build/SSBFileInjector.exe + master.csv
                genera build/original.z64
```

- `roms/` debe contener la ROM legalmente adquirida como `ssb.rom` (ver
  `roms/Place legally acquired rom titled ssb.rom here.txt`).
- **No sirve una ROM vanilla**: muchas ediciones están dentro de los archivos comprimidos internos.
  La ROM base ya viene con esos archivos inyectados.
- `build/master.csv` — lista completa de archivos a inyectar (`MODIFY`/`APPEND`, ruta, compresión,
  offsets de tabla interna). Regenera la base desde cero.
- `build/incremental.csv` — aplica solo los archivos nuevos sobre una base ya generada
  (actualmente vacío, solo la fila `END`).
- `build/utils/` — appenders en Java (`SSB64FileAppender`, `SSB64ImageFileAppender`) para añadir
  iconos de escenario, retratos de personaje y datos binarios genéricos a los archivos del juego.

### 2.2 Ensamblado (el paso habitual)

`patch.bat` (NTSC):
```
assembler\bass.exe -o "ssb64asm.z64" main.asm -sym logfile.log
assembler\chksum64.exe "ssb64asm.z64"
assembler\rn64crc.exe -u
```

`patch-pal.bat` (PAL): idéntico pero con `-d MAKE_PAL` y salida `ssb64asm-pal.z64`.

Pasos:
1. **bass** ensambla `main.asm` → ROM de salida + `logfile.log` (mapa de símbolos, muy útil para
   depurar en Project64).
2. **chksum64 / rn64crc** recalculan el CRC de la cabecera N64 (obligatorio, si no la consola/emulador
   rechaza la ROM).

`src/PAL.asm` se incluye siempre pero solo actúa cuando `MAKE_PAL` está definido; ajusta timings y
diferencias de la versión PAL.

### 2.3 CI y scripts de verificación

`.github/workflows/run_tests.yml` se dispara con cambios en `src/**` y ejecuta:

- `scripts/test/sequential_branches.py` — detecta branches consecutivos mal formados.
- `scripts/test/check_duplicate_action_edit.py` — detecta ediciones duplicadas de acciones.
- `scripts/test/overlapping_patches.py` — detecta parches que se solapan en ROM (**el error más
  peligroso del proyecto**: dos `OS.patch_start` sobre el mismo offset se pisan silenciosamente).

Otros scripts: `scripts/SSB.py`, `scripts/attributes_dump.py`, `scripts/gen_editable_rom.py`,
`scripts/Project64/get_move_ranges.js`.

---

## 3. Organización de carpetas

```
main.asm                  Punto de entrada del ensamblado: define regiones e incluye TODO
assembler/                bass.exe, chksum64.exe, rn64crc.exe, N64.inc (definiciones CPU N64)
roms/                     ROM base (no versionada) + filename_overrides.txt
build/                    Herramientas y CSVs para regenerar la ROM base
scripts/                  Utilidades Python/JS y tests de CI
src/                      TODO el código fuente
```

Dentro de `src/`:

| Ruta | Contenido |
|---|---|
| `src/*.asm` (raíz) | Módulos de sistema y de gameplay (uno por sistema) |
| `src/<Personaje>/` | Un directorio por personaje añadido (`Falco/`, `Marth/`, `Sonic/`, …) |
| `src/costumes/` | Definiciones y datos de trajes alternativos por personaje |
| `src/css/` | Módulos del *Character Select Screen* (paneles, toggles por jugador) |
| `src/stages/` | Escenarios personalizados: `.asm` (lógica/colisión) + `.bin` (datos) |
| `src/music/` | **330 archivos `.bin`** — MIDIs en formato GE, uno por pista |
| `src/music/profiles/` | Playlists preseteadas (un `.asm` por playlist) — ver §7.4 |
| `src/stages/profiles/` | Perfiles de escenarios preseteados (un `.asm` por perfil) |
| `src/sounds/` | Efectos de sonido (`.aifc`) |
| `src/gfx/` | Texturas (`.rgba5551`, `.rgba8888`, `.ia8`) e instrucciones de animación |
| `src/items/` | Datos de objetos |
| `src/Moveset/` | Movesets binarios compartidos (items, cliff, etc.) |
| `src/Req/` | Archivos `.req` — listas de requisitos/dependencias de modelos por personaje |
| `src/1p/` | Datos del modo un jugador (llamadas del narrador, escalas, texturas de nombres) |

Convención de nombres de personajes: prefijo `J` = versión japonesa, `E` = versión "E",
`N` = versión Polygon/clon, `G` = Giant. Ej.: `JFalcon/`, `NWario/`, `GBowser/`.

---

## 4. Módulos núcleo (infraestructura)

Estos son los que hay que entender antes de tocar cualquier otra cosa.

### `src/os.asm` — `scope OS`
La base de todo. Solo macros de ensamblado, sin código ejecutable propio.

- `OS.patch_start(rom_offset, ram_address)` / `OS.patch_end()` — abre/cierra un parche. Guarda y
  restaura `origin`/`base` con `pushvar`/`pullvar`.
- `OS.align(n)`, `OS.copy_segment`, `OS.move_segment`.
- `OS.routine_begin` / `OS.routine_end` — prólogo/epílogo de función.
- `OS.save_registers` / `OS.restore_registers` — guarda los 26 registros en 0x70 bytes de pila.
  Usado en hooks donde no se sabe qué registros están vivos.
- `OS.read_word`, `OS.UPPER` — helpers de carga.
- `OS.print_hex` — depuración en tiempo de ensamblado.

### `src/Global.asm` — `scope Global`
Direcciones RAM y constantes del juego original. Es el "diccionario" del motor:

- `Global.screen` — IDs de pantalla (`VS_CSS 0x10`, `VS_BATTLE 0x16`, `OPTION 0x39`,
  `CONGRATULATIONS 0x37`, `REMIX_MODES 0x77`, …).
- `Global.screen_interrupt` (`0x800465D0`) — escribir aquí provoca cambio de pantalla.
- `Global.GAMEMODE` — `DEMO 0`, `VS 1`, `BONUS 2`, `CLASSIC 5`, `TRAINING 7`. Es el **byte 0x00 de
  `match_info`**.
- `Global.match_info`, `Global.vs`, `Global.files_loaded` (`0x800D6300`),
  `Global.p_struct_head` (`0x80130D84`, `P_STRUCT_LENGTH 0x0B50`).
- `Global.stage_clipping` — punteros de colisión en runtime.

### `src/File.asm` — `scope File`
Solo constantes: ID numérico de cada archivo del juego. Los vanilla llegan hasta ~`0x853`; a partir
de `0x854` son archivos añadidos por Remix (modelos, animaciones, escenarios). **Añadir un archivo
nuevo implica añadir su constante aquí y su fila en `build/master.csv`.**

### `src/Render.asm` — `scope Render`
Capa de dibujado. Macros que crean objetos de render del motor:

- `draw_string`, `draw_string_pointer` (string dinámico vía puntero), `draw_number`,
  `draw_number_adjusted`, `draw_number_signed_with_prefix`.
- `draw_texture`, `draw_texture_at_offset`, `draw_texture_grid`.
- `draw_rectangle_`, `draw_stage_texture_`.
- Parámetros comunes: `room`, `group`, `ulx`/`uly` (floats en hex), `color` RGBA, `scale`
  (`FONTSIZE_DEFAULT = 0x3F800000` = 1.0), `alignment`, `blur`.

### `src/String.asm`, `src/Color.asm`, `src/Joypad.asm`, `src/Action.asm`, `src/Boot.asm`
- `String.asm` — inserción y manipulación de cadenas.
- `Color.asm` — paleta de colores nombrados.
- `Joypad.asm` — lectura de mandos, detección de combinaciones.
- `Action.asm` — sistema de acciones/estados de personaje.
- `Boot.asm` — arranque: parchea la secuencia del logo N64 e intro, carga datos de Remix en RAM,
  dispara la carga de SRAM.

### `src/SRAM.asm` — `scope SRAM`
Guardado persistente.

- El juego original solo usaba `0x0BDC` de `0x8000` bytes, y en realidad era `0x5EC` repetido dos
  veces. Remix parchea las rutinas de guardado/carga para usar **solo el primer bloque** y reclama
  el resto desde `SRAM.ADDRESS = 0x05F0`.
- `SRAM.block(size)` — reserva un bloque; cada bloque es una estructura
  `{dirección SRAM, puntero a datos, tamaño, padding}` alineada a 16 bytes.
- `SRAM.REVISION` (actualmente `0x00F7`) — **debe incrementarse** al añadir un escenario, un MIDI,
  un toggle nuevo o al cambiar el orden de los toggles. Si no, los datos guardados previamente se
  leerán desalineados.
- `mark_saved_`, `check_saved_`, `load_`, `save_`, `initialize_`.

---

## 5. Sistema de menús e interfaz

### 5.1 `src/Menu.asm` — `scope Menu` (motor genérico de menús)

Define dos estructuras de datos, ambas construidas con macros en tiempo de ensamblado:

**`Menu.info(...)`** — cabecera de un menú (0x38 bytes):
```
0x0000 puntero a la primera entrada (head)
0x0004 ulx / 0x0006 uly
0x0008 referencia al objeto cursor
0x000C selección actual
0x0010 room / 0x0012 group
0x0014 ancho en caracteres
0x0018 primera entrada visible / 0x001C última visible
0x0020 color cursor / 0x0024 color etiqueta / 0x0028 color valor
0x002C escala / 0x0030 alto de fila / 0x0032 filas por página
0x0034 blur / 0x0036 control con dpad
```

**`Menu.entry(title, type, default, min, max, a_function, extra, string_table, copy_address, next)`**
— una fila (lista enlazada vía el campo `next`):
```
0x0000 tipo    0x0004 valor actual   0x0008 min      0x000C max
0x0010 función a ejecutar al pulsar A
0x0014 tabla de strings (si el valor no es numérico)
0x0018 dirección a la que copiar el valor
0x001C siguiente entrada
0x0020 referencia al objeto string de la etiqueta
0x0024 campo extra (argumento para a_function)
0x0028 título (texto)
```

`Menu.type` va de `TITLE` (sin valor) a `MAX1023`, más `INPUT` (con modo edición, para teclado) e
`INT` (genérico — el macro elige el ancho de bits real según `max`, lo que determina cuánto ocupa
en SRAM).

Otras piezas: `Menu.change_screen_` (escribe en `Global.screen_interrupt`), `Menu.update_`
(lógica de navegación por frame), teclado en pantalla (`keyboard_sets`, `align_keyboard_chars_`).

### 5.2 `src/Toggles.asm` — `scope Toggles` (la pantalla de ajustes de Remix)

Es el módulo de UI más importante. Reemplaza la pantalla OPTION vanilla
(`Global.screen.OPTION = 0x39`).

- `disable_options_functionality_` — desactiva la pantalla de opciones original.
  El flag `normal_options` decide si se muestra la vanilla o los toggles de Remix.
- `add_mode_select_remix_button_` — añade un 5º botón al Mode Select reposicionando todos los
  botones y etiquetas existentes (una tanda de parches de coordenadas).
- `Toggles.run_` — bucle por frame: llama a `Menu.update_` y dibuja el perfil actual y la leyenda.
- `menu_index` — submenú activo:
  `0` Super Menu · `1` Remix Settings · `2` Gameplay · **`3` Music** · `4` Stage ·
  `5` Pokemon · `6` Player Tags · `7` Other Screens.

**Árbol de menús** (`head_super_menu`, línea ~2366):
```
Load Profile:        → load_profile_ (string_table_profile)
Remix Settings       → head_remix_settings
Gameplay Settings    → head_gameplay_settings
Music Settings       → head_music_settings      ← §7
Stage Settings       → head_stage_settings
Pokemon Settings     → head_pokemon_settings
Player Tags          → head_player_tags
Other Screens        → show_other_screens_
```

**Macros de guardia** — así consume el resto del código un toggle:
- `Toggles.guard(entry_address, exit_address)` — lee `entry + 0x04` (el valor actual) y salta
  a `exit_address` (o `jr ra`) si está desactivado.
- `Toggles.single_player_guard(...)` — igual, pero ignora el toggle en modos
  `CLASSIC` / `BONUS` (usa el valor por defecto).

Cualquier módulo puede además leer directamente `li at, Toggles.entry_<nombre>` + `lw at, 0x0004(at)`.

### 5.3 Otras pantallas

| Archivo | Pantalla |
|---|---|
| `src/CharacterSelect.asm` (7.2k líneas) | CSS: grid de personajes, cursores, paneles |
| `src/css/*.asm` | Toggles por jugador dentro del CSS (Handicap, Size, Shield, Kirby Hat, Player Tag, Stock Mode, Damage, Knockback, Input Delay/Display, Model Display, Visibility, Dpad…) |
| `src/CharacterSelectDebugMenu.asm` | Menú de depuración del CSS |
| `src/VsRemixMenu.asm` | Menú de modos VS Remix (Tag Team, KotH, Smashketball, Tug of War…) |
| `src/SinglePlayerMenus.asm` | Menús de un jugador |
| `src/Stages.asm` | Stage Select Screen (además de la tabla de escenarios) |
| `src/ResultsScreen.asm` | Pantalla de resultados |
| `src/CharacterDataScreen.asm` | Pantalla de datos de personaje |
| `src/Gallery.asm` | Galería de personajes (reutiliza la pantalla `CONGRATULATIONS 0x37`) |
| `src/Credits.asm` | Créditos |
| `src/Pause.asm`, `src/Training.asm`, `src/Practice.asm` | Overlays in-game |

---

## 6. Datos: dónde se define cada cosa

| Dato | Archivo | Mecanismo |
|---|---|---|
| **Personajes** | `src/Character.asm` | `define_character(...)` |
| **IDs de personaje** | `src/Character.asm`, `scope id` | `constant` (vanilla `0x00`–`0x1A`) |
| **Escenarios** | `src/Stages.asm` (~línea 5054+) | `add_stage(...)` |
| **Música / MIDIs** | `src/midi.asm` (~línea 200+) | `add_game(...)` + `insert_midi(...)` |
| **IDs de BGM** | `src/BGM.asm` | `scope stage` / `win` / `menu` / `special` |
| **Archivos ROM** | `src/File.asm` + `build/master.csv` | `constant` + fila CSV |
| **Trajes** | `src/costumes/<Personaje>.asm` | — |
| **Toggles / opciones** | `src/Toggles.asm` | `Menu.entry` / `entry_bool` |
| **Perfiles globales** | `src/Toggles.asm` | `write_defaults_for(...)` (defaults CE/TE/NE/JP de cada entry) |
| **Playlists de música** | `src/music/profiles/*.asm` | `add_music_profile` + `add_to_music_profile` |
| **Perfiles de escenario** | `src/stages/profiles/*.asm` | `add_stage_profile` + `add_to_stage_profile` |
| **Items** | `src/Item.asm`, `src/items/` | — |
| **Efectos de sonido** | `src/FGM.asm`, `src/sounds/` | — |
| **Peligros de escenario** | `src/Hazards.asm` (9.7k líneas, el mayor) | `Hazards.type` |

### 6.1 `define_character` — `src/Character.asm`

Dos sobrecargas:

- `define_character(name)` — solo para **personajes vanilla**: lee de la ROM original los punteros
  del struct, del array de parámetros, del array de menú y del array de acciones, y los expone como
  constantes.
- `define_character(name, parent, file_1..file_9, attrib_offset, add_actions, bool_jab_3,
  bool_inhale_copy, btt_stage_id, btp_stage_id, remix_btt_stage_id, remix_btp_stage_id,
  sound_type, variant_type)` — **crea un personaje nuevo** clonando un `parent`. El parent debe ser
  un ID ≤ `0xB` (los 12 originales); si no, se imprime error y no se crea.

Constantes de control: `ADD_CHARACTERS(68)`, `NUM_VANILLA_CHARACTERS(27)`,
`NUM_CHARACTERS = 27 + 2 + 68`, `STRUCT_TABLE(0x92610)`, `ACTION_ARRAY_TABLE_ORIGINAL(0xA6F40)`,
`SHARED_ACTION_ARRAY(0xA45D8)`.

Cada personaje añadido tiene además su propio directorio `src/<Nombre>/` con `<Nombre>.asm`
(acciones, moveset, tablas) y a menudo `<Nombre>Special.asm` (especiales B). Los archivos
`*shared.asm` en `src/` (`linkshared`, `foxshared`, `marioshared`, `nessshared`,
`jigglypuffkirbyshared`, …) contienen lógica común a un "linaje" de personajes.

### 6.2 `add_stage` — `src/Stages.asm`

```
add_stage(name, display_name,
          bgm, bgm_occasional, bgm_rare, bgm_rare2,      ← 4 pistas (ver §7.2)
          tournament_legal, tournament_hazard_mode, netplay_legal, can_toggle,
          class,
          btx_word_1..3,                                  ← texto del anuncio de batalla
          variant_for_stage_id, variant_type,             ← DL / OMEGA / REMIX / REMIX2
          cloaking_device_rate, super_mushroom_rate, poison_mushroom_rate,
          blue_shell_rate, lightning_rate, deku_nut_rate, franklin_badge_rate,
          series_logo, hazard_type, order)
```

Las pistas se referencian como `{MIDI.id.NOMBRE}`; `-1` significa "sin pista alternativa".
Los datos binarios del escenario viven en `src/stages/<nombre>.bin` y su lógica en
`src/stages/<nombre>.asm`; los archivos se registran en `src/File.asm` como tripletas
`STG_X_HEADER` / `STG_X` / `STG_X_BG`.

---

## 7. Sistema de música

Tres capas: **almacenamiento** (MIDI), **reproducción** (BGM) y **configuración** (Toggles).

### 7.1 `src/midi.asm` — `scope MIDI` (almacenamiento y registro)

Extiende la tabla de música del juego original.

- `MUSIC_TABLE` se lee de la ROM original en el offset `0x3D768`. Cada entrada son 8 bytes
  (offset relativo + tamaño). `MUSIC_TABLE_END` avanza a medida que se añaden pistas.
- `MIDI_BANK = 0x3000000` — banco nuevo donde se insertan los archivos MIDI; `MIDI_BANK_END` avanza.
- `move_dream_land_midi()` — mueve el MIDI de Dream Land al banco nuevo para liberar espacio
  contiguo tras `MUSIC_TABLE` y poder expandirla.
- `midi_count` arranca en `0x2F` (47 pistas vanilla) — **por eso todos los bucles sobre pistas
  personalizadas empiezan en `0x2F`**.
- `largest_midi` — el mayor tamaño encontrado; determina el tamaño de `midi_memory_block` en
  `main.asm`.

**Registro de una pista:**
```
insert_midi(file_name, random_te, random_ne, can_toggle, has_title,
            track_title, track_game, order)
```
- `file_name` → carga `src/music/<file_name>.bin`.
- `random_te` / `random_ne` → valor por defecto del toggle en los perfiles Tournament / Netplay.
- `can_toggle` → si aparece en la lista de Random Music Toggles.
- `has_title` / `track_title` → nombre mostrado.
- `track_game` → juego de origen, registrado antes con `add_game(name, title)`.
- `order` → **orden de aparición en el menú** (las entradas se ordenan por este campo, no
  alfabéticamente por nombre; ver §7.3).

El macro genera, entre otros, `MIDI.id.<file_name>` (usado por `add_stage`) y un conjunto de
defines globales `MIDI_<id>_TE`, `_NE`, `_TOGGLE`, `_TITLE`, `_NAME`, `_GAME`, `_ORDER`.
Variantes: `insert_external_midi` (ruta externa), sobrecargas cortas para pistas sin título o sin
toggle. Hay ~282 llamadas a `insert_midi` y 330 archivos en `src/music/`.

### 7.2 `src/BGM.asm` — `scope BGM` (reproducción)

Funciones del motor original: `play_(0x80020AB4)`, `stop_(0x80020A74)`,
`set_volume_(0x80020B38)` (volumen máximo `0x7800`).

Rutinas clave:

- **`master_bgm_volume`** — parchea `set_volume_` para multiplicar el volumen por
  `Toggles.entry_bgm_volume / 10.0`.
- **`apply_alt_or_random_music_`** — hook en `0x800FC314`, justo tras cargar el archivo del
  escenario (donde vive el `bgm_id` por defecto, en `0x007C` del struct de escenario). Es el
  **punto de entrada de toda la selección de música de combate**. Inicializa el flag
  `random_disabled`, llama a `alternate_music_` y, si sigue permitido, a `random_music_`.
  También contiene un caso especial: en VS Demo, si la pista es la intro de Final Destination,
  la sustituye por la música principal de FD.
- **`alternate_music_`** — elige entre las 4 pistas declaradas en `add_stage` con estas
  probabilidades: `CHANCE_MAIN 65`, `CHANCE_OCCASIONAL 16`, `CHANCE_RARE 10`, `CHANCE_RARE_2 9`.
- **`random_music_`** / **`add_song_to_random_list_`** — construyen la lista de candidatas a partir
  de los toggles de Random Music y eligen una.
- **`alt_menu_music_`**, **`handle_sss_shortcut`** (atajos con botones C en el Stage Select),
  **`show_music_title_`** (título de la pista al empezar el combate),
  **`thirty_second_music_swap`**, **`remix_1P_ending_song`**,
  **`prevent_results_bgm_on_css_`**, **`set_safe_id_on_play_`/`_stop_`**.

Scopes de IDs: `BGM.stage.*` (`DREAM_LAND`, `FINAL_DESTINATION`, …), `BGM.win.*`,
`BGM.menu.*` (`MAIN`, `MAIN_MELEE`, `MAIN_BRAWL`, `BONUS`, `CREDITS`, `DATA`, …), `BGM.special.*`.
`vanilla_current_track = 0x8013139C`.

### 7.3 Music Settings — `src/Toggles.asm`, `head_music_settings` (~línea 2457)

Entradas fijas, en orden:

```
Play Music                     bool
Random Music                   bool
Salty Runback Preserves Song   bool
Menu Music                     INT 0..menu_music.MAX_VALUE(22)  → play_menu_music_
Music Title at Match Start     bool
BGM Volume                     INT 0..10                        → update_bgm_volume
SFX  Volume                    INT 0..10                        → update_fgm_volume
Load Profile:                  INT                              → load_sub_profile_
Random Music Toggles:          TITLE                            → toggle_all_
  ├─ 16 toggles vanilla (Bonus, Congo Jungle, Credits, Data, Dream Land, Duel Zone,
  │  Final Destination, How To Play, Hyrule Castle, Meta Crystal, Mushroom Kingdom,
  │  Peach's Castle, Planet Zebes, Saffron City, Sector Z, Yoshi's Island)
  └─ toggles personalizados generados en bucle desde MIDI.midi_count
```

Cada toggle usa `entry_bool_with_a(..., preview_bgm_, <BGM id>, siguiente)`: pulsar **A** sobre la
fila reproduce la pista (`preview_bgm_`).

**Generación de los toggles personalizados** (bloque tras `entry_random_music_first_custom`):
en tiempo de ensamblado se construye un array `sorted_midi_<n>` de `0x2F` a `MIDI.midi_count`, se
ordena con un *bubble sort* por el campo `_ORDER` de cada pista, y se emite una entrada por cada
pista con `_TOGGLE == TRUE`. Por eso el parámetro `order` de `insert_midi` es lo que controla la
posición en el menú.

`play_menu_music_` mapea el valor de `Menu Music` a un `BGM.menu.*`
(`0` DEFAULT/aleatorio entre temas Smash, `1` 64, `2` Melee, `3` Menu 2, `4` Brawl, `5` GoldenEye,
`6` Mario Tennis, `7` File Select SM64, `8` Blast Corps, … hasta 22, incluyendo un modo
"RANDOM ALL" que usa el flag `menu_randomizing_all`). Contiene un easter egg: el contador
`itsatrap` cuenta selecciones consecutivas de File Select SM64.

### 7.4 Load Profile — dos mecanismos distintos

Es importante no confundirlos.

**(a) Perfil global** — entrada `Load Profile:` del Super Menu, función **`load_profile_`**.

- Tabla `string_table_profile`: `Community` (CE), `Tournament` (TE), `Netplay` (NE),
  `Japanese` (JP), `Custom`. También existen los strings `Semi-Competitive` y
  `Current Profile: `.
- Los valores por defecto se emiten con el macro `write_defaults_for(profile)`, que recorre todos
  los toggles y escribe `TOGGLE_<n>_DEFAULT_<profile>` — es decir, **los 4 valores por defecto de
  cada toggle son los 4 argumentos CE/TE/NE/JP de cada `Menu.entry`/`entry_bool`**.
- Se materializan como `profile_defaults_CE/TE/NE/JP` y la tabla de punteros `profiles`.
- `get_current_profile_` compara los valores actuales con cada perfil; si no coincide con ninguno,
  muestra `Custom`. `Toggles.run_` dibuja el resultado en `profile_pointer`.

**(b) Sub-perfiles de música y escenarios** — entradas `Load Profile:` dentro de Music Settings y
Stage Settings, función **`load_sub_profile_`** (~línea 2069).

- Según `menu_index` elige la tabla `music_profiles` o `stage_profiles`, indexa por el valor de la
  entrada, obtiene el puntero a los defaults y los copia a las entradas del bloque.
- Se declaran con `add_music_profile(profile, display_text)` / `add_stage_profile(profile, display_text)`,
  que reservan un array de `OS.FALSE` (una palabra por toggle del bloque) y **reescriben el campo
  `max` de la entrada `Load Profile:`** usando los orígenes guardados
  `LOAD_PROFILE_MUSIC_ENTRY_ORIGIN` / `LOAD_PROFILE_STAGE_ENTRY_ORIGIN` (+`0x000C`).
- Se rellenan con `add_to_music_profile(profile, track)` / equivalente para escenarios, que
  escriben `OS.TRUE` en la posición del track usando los índices
  `music_toggle_<NOMBRE>` (`BONUS 0` … `YOSHIS_ISLAND 15`) y `stage_toggle_<nombre>`.
- Los perfiles de música parten de "todo desactivado"; los de escenario asumen que Community,
  Tournament y Netplay ya existen (de ahí el `+3` en el cálculo del `max`).

#### Dónde viven las playlists

Cada perfil es **un archivo propio**, no una entrada en `Toggles.asm`:

```
src/music/profiles/     vanilla · classics · intobattle · positivevibes
                        slappers · freshjams · staff
src/stages/profiles/    competitive · vanilla · dreamlandonly
                        no_omega · no_variant · staff
```

Se registran con un `include` en `src/Toggles.asm:3027` (música) y `:3036` (escenarios). Ese punto
del archivo es deliberado: está **después** del bucle que genera los toggles personalizados
(~línea 2525), que es donde se crean los defines `music_toggle_*`.

Contenido típico de un perfil (`src/music/profiles/positivevibes.asm`):
```asm
add_music_profile(happy, "Positive Vibes")   // primero: crea el perfil
add_to_music_profile(happy, SKYWORLD)        // luego: una línea por pista
add_to_music_profile(happy, SPIRAL_MOUNTAIN)
```

**El identificador de pista es el `file_name` de `insert_midi`** (= nombre del `.bin` en
`src/music/`), **no el título mostrado**. El bucle de generación emite:
```asm
evaluate music_toggle_{MIDI.MIDI_{id}_FILE_NAME}(num_toggles - {first_music_toggle})
```
Y lo hace **solo si `can_toggle == OS.TRUE`**: una pista insertada con `insert_midi_no_toggle` no
tiene define `music_toggle_` y referenciarla rompe el ensamblado.

El desplegable del menú se construye solo: `music_profiles` (línea 3043) y
`string_table_music_profile` (línea 3051) iteran sobre `num_music_profiles`. La primera entrada
siempre es Community (`profile_defaults_CE + first_music_toggle * 4`).

> **Añadir una playlist NO requiere incrementar `SRAM.REVISION`.** `update_block_size_based_on_max()`
> se ejecuta al declarar la entrada `Load Profile:` con su `max` literal (`0`); `add_music_profile`
> solo reescribe el campo en ROM y no recalcula el tamaño del bloque. El layout de SRAM no cambia.
> Esto **sí** contrasta con añadir un MIDI toggleable, que altera `block_music` (ver §7.5).

### 7.5 Persistencia de la música

`src/Toggles.asm` (~línea 2845+) define un bloque SRAM por sección:

```
block_remix, block_gameplay, block_music, block_stages, block_pokemon, block_tags
        ↑ tabla sram_block_table (terminada en 0)
        ↑ tabla block_head_table  → head_remix_settings, head_gameplay_settings,
                                    head_music_settings, head_stage_settings, ...
```

El tamaño de cada bloque se calcula como `((block_size / 32) + 1) * 4` — los toggles se empaquetan
**bit a bit**, y el ancho en bits lo determina el `Menu.type` derivado de `max`. `block_tags` es
distinto: `MAX_TAGS * 20` bytes de texto.

> **Consecuencia práctica:** añadir un MIDI toggleable cambia el tamaño de `block_music` y por
> tanto la disposición de todos los bloques siguientes. Hay que incrementar `SRAM.REVISION`.

---

## 8. Flujo de ejecución

```
Encendido
   │
   ├─ Boot.asm: parches de arranque; carga de datos Remix a RAM; SRAM.load_
   │
   ├─ Logo N64 (screen 0x1B)
   │     Boot.splash_ lo redirige a CONGRATULATIONS (0x37) con VICTOR_ID = Character.id.NONE,
   │     lo que SinglePlayer.replace_victory_image_ detecta para mostrar la splash de Remix.
   │     Incluye temporizador (TIMER 0x801322F8) y fix del glitch de frame buffer.
   │
   ├─ Intro / Título (0x01)
   │
   ├─ MODE_SELECT (0x07)  ← Toggles.add_mode_select_remix_button_ añade el 5º botón
   │     ├─ 1P            → _1P_GAME_MODE_MENU (0x08) → SinglePlayer*.asm
   │     ├─ VS            → VS_GAME_MODE_MENU (0x09) → VS_CSS (0x10)
   │     ├─ DATA          → DATA_MENU (0x3A)
   │     ├─ OPTION (0x39) → Toggles.asm  ← el menú de Remix
   │     └─ REMIX_MODES (0x77) → VsRemixMenu.asm
   │
   ├─ CSS (0x10) — CharacterSelect.asm + src/css/*
   ├─ STAGE_SELECT (0x15) — Stages.asm (+ atajos de música: BGM.handle_sss_shortcut)
   │
   ├─ VS_BATTLE (0x16)
   │     · Carga del archivo de escenario
   │         └─ hook BGM.apply_alt_or_random_music_ → alternate_music_ → random_music_
   │     · Spawn.asm coloca a los jugadores
   │     · Bucle por frame: sistemas de gameplay (§9) leen sus toggles vía Toggles.guard
   │     · BGM.show_music_title_ muestra el título si el toggle está activo
   │
   └─ RESULTS (0x18) — ResultsScreen.asm / VsStats.asm
```

Los cambios de pantalla se hacen siempre escribiendo el ID en `Global.screen_interrupt`, vía
`Menu.change_screen_`.

---

## 9. Sistemas de gameplay y sus relaciones

Cada archivo de `src/` raíz es un sistema autocontenido que se engancha al motor con parches. La
mayoría sigue el mismo patrón: definir una `Menu.entry` en `Toggles.asm` y consultarla con
`Toggles.guard`.

**Combate y física:** `Damage.asm`, `Knockback.asm`, `Hitstun.asm`, `Hitbox.asm`, `DI.asm`,
`Shield.asm`, `Parry.asm`, `PerfectShield.asm`, `AirDodge.asm`, `SpotDodge.asm`, `ZCancel.asm`,
`JabLock.asm`, `LedgeJump.asm`, `LedgeTrump.asm`, `Walljump.asm`, `WallTeching.asm`,
`FootStool.asm`, `Tripping.asm`, `Rage.asm`, `StaleMoves.asm`, `ChargeSmashAttacks.asm`,
`AerialAttackFastFall.asm`, `Reflect.asm`, `OnHit.asm`, `Poison.asm`, `Stamina.asm`, `Speed.asm`.

**Presentación:** `GFX.asm`, `GFXRoutine.asm`, `Camera.asm`, `Widescreen.asm`, `AA.asm`,
`FPS.asm`, `Transitions.asm`, `SwordTrail.asm`, `CharEnvColor.asm`, `Size.asm`,
`MagnifyingGlass.asm`, `SpecialZoom.asm`, `ComboMeter.asm`, `InputDisplay.asm`,
`PlayerTag.asm`, `DragonKingHUD.asm`, `BlastZone.asm`, `Accessibility.asm`.

**Modos de juego:** `SinglePlayer.asm`, `SinglePlayerModes.asm`, `SinglePlayerMenus.asm`,
`SinglePlayerEnemy.asm`, `HRC.asm`, `Bonus.asm`, `TwelveCharBattle.asm`, `TagTeam.asm`,
`KingOfTheHill.asm`, `Smashketball.asm`, `TugOfWar.asm`, `DKMode.asm`, `TimedStock.asm`,
`StockMode.asm`, `Teams.asm`, `VsDemo.asm`, `Training.asm`, `Practice.asm`, `Practice_1P.asm`.

**Infraestructura auxiliar:** `Crash.asm` (pantalla de crash — no confundir con `src/Crash/`,
el personaje), `Timeouts.asm`, `Command.asm`, `Moveset.asm`, `Skeleton.asm`, `Surface.asm`,
`Spawn.asm`, `Item.asm`, `Projectile.asm`, `Fireball.asm`, `Hazards.asm`, `AI.asm`,
`VanillaLv10Attacks.asm`, `KirbyHats.asm`, `Costumes.asm`, `SFXReplace.asm`, `Stereo.asm`,
`PokemonAnnouncer.asm`, `InputDelay.asm`, `SingleButtonMode.asm`, `Cheats.asm`, `Handicap.asm`,
`GameEnd.asm`, `Japan.asm`, `FD.asm`, `Combo.asm`, `Gallery.asm`.

---

## 10. Dependencias entre módulos

Las dependencias se declaran con `include` al principio de cada archivo, protegidas con el patrón
de guarda:
```
if !{defined __NOMBRE__} {
define __NOMBRE__()
...
}
```
Esto permite includes redundantes sin duplicar código.

**Grafo de dependencias del núcleo:**

```
                        OS.asm  (sin dependencias — base de todo)
                          │
        ┌─────────────────┼─────────────────┬──────────────┐
     Global.asm       String.asm        Color.asm      Joypad.asm
        │                 │                 │              │
        └────────┬────────┴────────┬────────┴──────────────┘
                 │                 │
             Render.asm        Menu.asm ──── FGM.asm
                 │                 │
                 └────────┬────────┘
                          │
                     Toggles.asm ──── SRAM.asm
                       │    │
                       │    └──── Stages.asm ──┐
                       │                       │
                       └──── MIDI.asm ─────────┤
                                │              │
                             BGM.asm ──────────┘
                                              (Stages referencia MIDI.id.*
                                               BGM referencia Toggles.entry_* y MIDI)
```

**Reglas prácticas:**

1. **`OS.asm` primero, siempre.** Todo lo demás lo asume.
2. **`Toggles.asm` es el hub de configuración.** Casi todos los sistemas de gameplay dependen de él
   (`Toggles.entry_*` o `Toggles.guard`), pero él solo depende de `Color`, `Menu`, `MIDI`, `OS`,
   `SRAM` y `Stages`.
3. **`MIDI` → `Stages` → `Toggles` → `BGM`** es la cadena de la música. `Stages.add_stage` consume
   `MIDI.id.*`, y `Toggles` genera sus entradas iterando `MIDI.midi_count`. `BGM` lee de los tres.
4. **El orden en `main.asm` importa** para los símbolos evaluados en tiempo de ensamblado
   (`variable`, `evaluate`, `global define`). `OS`, `String`, `Render`, `Action`, `File`, `Boot`,
   `Settings` van primero; `Character.asm` antes que cualquier directorio de personaje;
   `MIDI.asm` casi al final (porque `midi_memory_block` en `main.asm` necesita
   `MIDI.largest_midi` ya calculado); `PAL.asm` el último.
5. **Los personajes dependen de `Character.asm`** y a menudo de un `*shared.asm` de su linaje.

---

## 11. Notas para modificar con seguridad

- **`OS.patch_start` con un offset ya parcheado se pisa en silencio.** Ejecutar
  `scripts/test/overlapping_patches.py` antes de dar por buena una modificación.
- **Incrementar `SRAM.REVISION`** (`src/SRAM.asm`) al añadir escenario, MIDI o toggle, o al
  reordenar toggles.
- **Delay slots**: es MIPS. La instrucción tras un branch/jump siempre se ejecuta. Los tests de CI
  (`sequential_branches.py`) atrapan algunos errores, no todos.
- **"original line N"**: los comentarios que marcan las instrucciones del juego original que un
  parche debe restaurar. No eliminarlas.
- **`logfile.log`** (generado por `bass -sym`) contiene el mapa de símbolos; es la herramienta
  principal para depurar en Project64.
- Los `print` en tiempo de ensamblado (`OS.print_hex`, mensajes de `insert_midi`, avisos de SRAM)
  salen por consola durante `patch.bat` y son la vía de diagnóstico del propio ensamblado.
- El repositorio usa nombres de archivo con mayúsculas inconsistentes (`src/OS.asm` en `main.asm`
  vs. `src/os.asm` en disco). **El build asume un sistema de archivos insensible a mayúsculas
  (Windows).** En Linux/WSL sobre ext4 el ensamblado fallará sin ajustes.
