#!/usr/bin/env python3
"""Revisa un .bin de musica: programas en rango, loops, volumenes CC7.

Uso: python3 scripts/check_midi.py src/music/ARCHIVO.bin [...]

Limites conocidos: el evento FE es de longitud variable no descifrada, asi que
solo es fiable lo que se lee ANTES de la primera nota de cada pista (program
change y CC7 inicial) mas el conteo global de marcadores de loop.
"""
import struct, sys

BANK = {1:"Flute",2:"Organ",3:"Synth Tuba",4:"Synth Wave",5:"Brass",6:"Lead Synth",
7:"Strings",8:"Electric Piano",9:"Kalimba",10:"Glockenspiel",11:"Slap Bass",
12:"Synth Bass",13:"Electric Bass",14:"Banjo",15:"Choir Aahs",16:"Pan Flute",
17:"Timpani",18:"Main Percussion",19:"Square Wave (NES)",20:"Triangle (NES)",
21:"White Noise (NES)",22:"Orchestral Hit",23:"Drum Roll",24:"Picked Bass-Clav-O.",
25:"TR-808 Synth Drum",26:"Bass-S.Chord-Piano",27:"Drums+Tubular Bells",28:"Pan Flute 2",
29:"Synth Accordion",30:"Trombone",31:"Drum w/ Cowbell",32:"Acoustic Bass",33:"Steel Drums",
34:"Trumpet",35:"Accordion",36:"Bassoon",37:"Clarinet",38:"Nylon Guitar",39:"Muted Gt.",
40:"Muted Trumpet",41:"Overdriven Guitar",42:"Distortion Guitar",43:"Rock Organ",
44:"Choir Ahhs 2",45:"Choir Oohs",46:"Slap Bass (Alt)",47:"Church Organ",48:"Steel Drum 2",
49:"Distortion Guitar 2",50:"Tenor Sax",51:"Overdriven Guitar 2",52:"Acoustic Grand Piano",
53:"Slap Bass 1",54:"Orchestra Hit",55:"Synth (Alt)",56:"Missing NES Wave",
57:"Nylon Guitar (Alt)",58:"Sawtooth (K64)",59:"Shogo Sakai Slide",60:"OOT Acoustic",
61:"Pizzicato (FFXI)",62:"Shamisen",63:"DK Rap",64:"Roll",65:"Yoshis",66:"Marimba",
67:"DF Chants",68:"Monkeys",69:"Sine Wave",70:"Harp"}

MEDIANA_JUEGO = 117

def varlen(d, i):
    v = 0
    while True:
        b = d[i]; i += 1; v = (v << 7) | (b & 0x7f)
        if not b & 0x80: break
    return v, i

def scan_track(d, o, end):
    """Devuelve (canal, program, [(offset_cc7, valor)]) del bloque inicial."""
    i = o; st = None; prog = None; ch = None; cc7 = []
    while i < end:
        try:
            dt, i = varlen(d, i); b = d[i]
            if b == 0xFF:
                m = d[i+1]; n = {0x2F:3, 0x51:5, 0x2E:4, 0x2D:8}.get(m)
                if n is None: break
                i += n
                if m == 0x2F: break
                continue
            if b == 0xFE: i += 3; continue
            if b & 0x80:
                if b >= 0xF0: break
                st = b; i += 1
                if ch is None: ch = st & 15
            if st is None: break
            hi = st & 0xF0
            if hi == 0xB0:
                if d[i] == 7: cc7.append((i+1, d[i+1]))
                i += 2
            elif hi == 0xC0:
                if prog is None: prog = d[i]
                i += 1
            elif hi == 0x90: break          # empiezan las notas
            elif hi in (0x80, 0xA0, 0xE0): i += 2
            elif hi == 0xD0: i += 1
            else: break
        except IndexError: break
    return ch, prog, cc7

def check(path):
    d = open(path, 'rb').read()
    if len(d) < 0x44:
        print("%s: archivo demasiado corto" % path); return
    div = struct.unpack('>I', d[0x40:0x44])[0]
    offs = [o for o in struct.unpack('>16I', d[:0x40]) if o]
    bounds = sorted(offs) + [len(d)]
    loops = d.count(b'\xff\x2e')
    print("=== %s" % path.split('/')[-1])
    print("    %d bytes | division %d | %d pistas | %d loops %s"
          % (len(d), div, len(offs), loops, "OK" if loops else "*** SIN LOOP ***"))
    problemas = []; vols = []
    for t, o in enumerate(struct.unpack('>16I', d[:0x40])):
        if not o or t == 0: continue
        ch, prog, cc7 = scan_track(d, o, bounds[bounds.index(o)+1])
        if prog is None and not cc7: continue
        inst = BANK.get(prog, "???") if prog is not None else "(sin program)"
        vol = cc7[0][1] if cc7 else None
        if vol is not None: vols.append(vol)
        nota = ""
        if prog is not None and not (1 <= prog <= 70):
            nota = "  <-- FUERA DE RANGO (rompe el audio)"
            problemas.append("t%d prog %s" % (t, prog))
        elif prog == 18 and ch != 9:
            nota = "  (percusion)"
        elif ch == 9 and prog != 18:
            nota = "  <-- canal 9 sin prog 18, revisar si es bateria"
            problemas.append("t%d canal 9 con prog %s" % (t, prog))
        print("    t%-2d ch%-3s prog %-4s %-22s vol %-5s%s"
              % (t, ch, prog, inst, vol if vol is not None else "-", nota))
    if vols:
        vs = sorted(vols)
        print("    volumen: mediana %d (juego: %d) | min %d | max %d | %d de %d pistas con CC7"
              % (vs[len(vs)//2], MEDIANA_JUEGO, min(vols), max(vols), len(vols), len(offs)-1))
    print("    %s" % ("PROBLEMAS: " + ", ".join(problemas) if problemas else "sin problemas de rango"))
    print()

for p in sys.argv[1:]:
    check(p)
