# Contexto del proyecto — para retomar en nuevas sesiones

Documento de traspaso. Leer esto da todo el contexto necesario para seguir trabajando sin
re-derivar lo aprendido. Última actualización: 2026-07-25.

---

## Qué es este proyecto

**Build Impecable — Edición Team CL**: un fork de Super Smash Bros. 64 construido sobre
**Smash Remix** (el mod de The_Smashfather). El motor, personajes y escenarios vienen de Remix.
**Lo que se trabaja acá es música**: importar pistas MIDI propias al juego y curarlas en el
perfil "Impecable".

- Repo local: `/home/meraki/smashremix`, rama `main` (la principal para PRs es `master`).
- Usuario: `merakissb`. Trabaja en español chileno, informal. Habla con capturas de SynthFont /
  GE Editor.
- Documentación completa del flujo: **`readme.md`**. Tabla de instrumentos y volúmenes:
  **`MUSICA.md`**.

---

## Lo más importante que aprendimos (no re-derivar)

### El banco de instrumentos NO es General MIDI
- El número de MIDI Program es un **índice directo** al banco del juego. Rango válido: **1-70**.
- **Programa 0 o 71+ = corta el audio del juego entero** en el instante en que entra ese canal.
  Síntoma clásico: "suena bien un rato y de golpe se corta todo". Fue el bug #1 de la sesión.
- **Programa 18 = percusión** (la batería). Los tutoriales lo llaman "Rock Organ" porque leen
  nombres GM.
- **El canal MIDI da igual** — no hay canal de batería reservado como en GM. El instrumento
  sale solo del programa.
- **Los nombres que muestra el editor son GM y mienten.** Ej: prog 55 se llama "Orchestra Hit"
  en GM pero suena a "Synth (Alt)"; el orchestra hit real es el 54. Guiarse por la tabla del
  `readme.md`, no por el editor.
- La tabla completa 1-70 está en `readme.md` y `MUSICA.md`. Salió del
  `src/music/sf2/Smash64MidiInstruments.sf2` (presets 1-42) + los `add_instrument()` de
  `src/midi.asm` (43-70).

### Formato del .bin (MIDI comprimido de libultra)
- Cabecera: 16 punteros u32 big-endian (0x00-0x3F), uno por pista; división en 0x40; datos en
  0x44+.
- **Loop**: cada pista lleva `FF 2E 00 FF` al inicio (ancla) y `FF 2D rrrr bbbbbbbb` antes del
  fin. Los últimos 4 bytes del `FF 2D` son un offset de retorno **relativo hacia atrás**:
  `destino = (pos_FF2D + 8) − offset`, que cae justo después del `FF 2E`.
- **Sin `FF 2E`/`FF 2D` la pista no loopea** (suena una vez y para). Chequeo: `grep` de bytes
  `ff2e` en el archivo; 0 = sin loop.
- **Volumen**: CC7 (Channel Volume) inicial de cada pista, 0-127. **Mediana del juego = 117**
  (p25=100, p75=124). Debajo de ~100 suena apagado; en 127 satura/aplasta la mezcla.
- El evento `FE` es de **longitud variable no descifrada** — por eso el parser de análisis se
  desincroniza al medir ticks o al leer notas en medio de una pista. Lee bien: cabeceras,
  programas, CC7 del bloque inicial, y presencia de loops. NO lee bien: duración en ticks,
  polifonía, program changes en medio de la canción.

### Reglas de nombres y registro
- **El nombre del `.bin` es también el identificador del ensamblador.** Solo letras, números y
  guion bajo. `KEN_STAGE.bin` sí, `ken-stage.bin` NO (rompe el ensamblado).
- Registrar una canción toca **3 archivos**:
  1. `src/midi.asm` — `insert_midi(...)` al **final** de la lista (el id sale de la posición;
     insertar al medio corre los ids de abajo). Si el juego de origen no existe, `add_game()`
     antes.
  2. `src/Toggles.asm` — `add_to_impecable_music(FILE_NAME)` para que el perfil la encienda.
  3. `src/SRAM.asm` — incrementar `REVISION` en uno (si no, la SRAM guardada queda
     desincronizada y el juego ignora los defaults del perfil).
- **Order 900+** para las pistas propias → quedan siempre al final del menú, por encima de lo
  que agregue Remix (su máximo es 289).

### Dos "Impecable" distintos (trampa que nos costó tiempo)
- **`profile_impecable` en `Toggles.asm`** (LOAD PROFILE): el que usa el usuario. Apaga TODAS
  las pistas y enciende solo las de `add_to_impecable_music`. **Este es el correcto.**
- **`src/music/profiles/impecable.asm`** (music profile, sistema aparte): lo **eliminamos**.
- Si una canción no aparece en el juego con Impecable cargado, casi siempre falta su
  `add_to_impecable_music`.
- **Random Music debe estar en ON** en el perfil (verificado por el usuario): con OFF, la lista
  de pistas no se respeta en las peleas.

### Otros mecanismos del motor
- **Polifonía**: la N64 tiene pocas voces. `add_priority_override({MIDI.id.X}, instrumento,
  0x7F)` en `midi.asm` protege lo que no debe cortarse. Es **por instrumento, no por pista** —
  dos pistas con el mismo programa no se diferencian.
- **Volumen global de una pista**: `add_master_volume_override({MIDI.id.X}, valor)` baja/sube
  la canción entera (no un canal). Para ajustar UN canal, editar su CC7 en el `.bin`.
- **Menú music**: se puede cambiar la canción del menú, pero requiere tocar `BGM.asm` y
  `Toggles.asm` con ids hardcodeados. Lo probamos con Frosty Village y lo revertimos; el menú
  quedó en Mario Party.

---

## Estado actual

**16 canciones propias**, registradas (order 900-915) y en el perfil Impecable. Última tanda:
2026-07-25 (7 reemplazos + split de Trunks en V1/V2 + Top Gear nuevo + 4 borradas).

| Canción | file_name | Juego | order | Notas |
|---|---|---|---|---|
| Cammy's Stage | CAMMY_STAGE | SSF2 | 900 | export de 1 pista fusionada |
| Ken's Stage | KEN_STAGE | SSF2 | 901 | tiene priority_override; usuario reportó que **no loopea** (pendiente, ver abajo) |
| Trunks Battle V1 | TRUNKS_BATTLE_V1 | Butouden 3 | 902 | batería reparada (prog 0→18 en 0x22cb); mediana vol 95 |
| Trunks Battle V2 | TRUNKS_BATTLE_V2 | Butouden 3 | 903 | ex-`TRUNKS_BATTLE` (variable2); mediana vol 82 |
| Rhythmical Bustle | RHYTMICAL_BUSTLE | Melty Blood | 904 | **sin batería a propósito**: t10 ch9 en prog 16 (Pan Flute), no 18 — decisión del usuario, NO parchear |
| Dan Dan Kokoro Hikareteku | DAN_DAN | DBGT | 905 | ok |
| Butouden 3 Credits | DBZ_SB3_CREDITS_ROLL | Butouden 3 | 906 | v. ending; mediana vol 127 (usuario pidió no tocar) |
| Mega Man 3 Title | MEGAMAN3_TITLE | Mega Man 3 | 907 | ok |
| Mega Man 7 Intro | MEGAMAN7_INTRO | Mega Man 7 | 908 | bajo restaurado (Slap + Acoustic Bass), vol 114 |
| Guile's Stage | GUILE_STAGE | SSF2 | 909 | trae percusión (t6/t7 ch9 prog 18); mediana vol 100 |
| Gundam Wing Intro | GUNDAM_INTRO | Gundam Wing | 910 | mediana vol 83 |
| Balrog's Stage | BALROG_STAGE | SSF2 | 911 | 1 pista fusionada |
| Ryu's Stage | RYU_STAGE | SSF2 | 912 | todo en vol 127 |
| Littleroot Town | LITTLEROOT_TOWN | Pokemon Ruby & Sapphire | 913 | mediana vol 80 |
| Pegasus Fantasy | PEGASUS_FANTASY | Saint Seiya | 914 | corta (2.3 KB), vol 127 |
| Top Gear | TOPGEAR_TRACK1 | Top Gear | 915 | **nueva** 2026-07-25; 1 pista fusionada |

> **Borradas el 2026-07-25** (desregistradas de midi.asm + Toggles + `.bin` eliminados):
> We Gotta Power (DBZ_WEGOTTAPOWER), El Tiempo (megaweathertheme), Prologue II (dbz_prologueII),
> Sabre Wulf (SABRE_WULF). Con esto quedaron **huérfanos y removidos** los juegos `dbz`,
> `megavision` y `killerinstinct`.
>
> Nota: el usuario pidió **NO normalizar volúmenes** y **dejar los `.bin` tal cual** salvo bugs
> que rompan la canción (ej. prog 0/fuera de rango, que sí se parchea). Respetar salvo aviso.

**Juegos custom activos** en `midi.asm`: `butouden3`, `dbgt`, `megaman3`, `megaman7`,
`meltyblood`, `ssf2`, `gundamwing`, `saintseiya`, `topgear` (+ `pokemonruby` que ya existía).

**Perfil Impecable** (Random Music ON, Menu Music Mario Party, Skip Results ON, SSS Tournament):
las 16 de arriba + ROCKSOLID, CLOCKTOWER, GANGPLANK, TOWEROFHEAVEN (Luna Ascension), OLE,
SMB2OVERWORLD, MORRIGAN (23 en total).

**SRAM REVISION**: `0x010F`. Incrementar en cada cambio de contenido/toggles.

---

## Pendientes / cosas a revisar

- **Ken's Stage no loopea** (reportado por el usuario). Investigado: el `.bin` tiene los
  marcadores de loop correctos en las 7 pistas, idéntico a Cammy que sí loopea. NO se encontró
  defecto en el archivo. Hipótesis: (1) probó un build viejo → rebuild limpio; (2) las pistas
  del MIDI tienen largos distintos y se desincronizan → revisar en el MIDI que todas terminen
  en el mismo compás. No confirmado por límite del parser (no mide ticks).
- **Guile sin percusión** — confirmar con el usuario si el arreglo debía tener batería.
- **Trunks desbalanceado** — un amigo bajó 5 pistas en el MIDI pero dejó el bajo (Acoustic Bass)
  en 127 y el Sawtooth en 120, sobre un fondo bajo. Se puede emparejar subiendo el fondo.
- **Parches que se pierden al reexportar**: cada vez que el usuario reexporta un MIDI desde el
  editor, se pierden los parches de byte (batería a prog 18, ajustes de volumen). Solución
  permanente: que se editen en el MIDI mismo. Mientras tanto hay que re-parchear tras cada
  reexport.

---

## Herramientas de análisis (scratchpad de la sesión)

Hay scripts Python en el scratchpad que escanean los `.bin`: programas por pista, detección de
loops, volúmenes CC7. Si se necesitan de nuevo, se reescriben rápido — la lógica clave:
- Leer 16 punteros u32 BE en 0x00-0x3F, división en 0x40.
- Para cada pista: parsear el bloque inicial (delta + eventos) hasta la 1a nota para sacar
  program change (`Cn`) y CC7 (`Bn 07 vv`).
- Loop presente = el archivo contiene bytes `ff 2e` y `ff 2d`.
- Recordar: el parser se rompe al pasar el evento `FE`, así que solo confiar en lo que se lee
  ANTES de la primera nota, más el conteo global de marcadores de loop.

---

## Flujo típico cuando el usuario sube una canción

1. Escanear el `.bin`: programas en rango (1-70), batería en 18, loops presentes, volúmenes.
2. Si hay programas fuera de rango o batería en 0 → traducir por nombre GM a la tabla y
   parchear los bytes, o pedir que ajuste en el editor.
3. Si el volumen está muy alto (127) o bajo (<100) → normalizar CC7 hacia ~117.
4. Registrar en los 3 archivos (midi.asm, Toggles.asm, SRAM.asm) con order 900+.
5. Confirmar con el usuario antes de dar por listo. Avisar de parches que se pierden al
   reexportar.
