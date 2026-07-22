assembler\bass.exe -d MAKE_PAL -o "Impecable Edition v2.0.1 (PAL).z64" main.asm -sym logfile-pal.log
assembler\chksum64.exe "Impecable Edition v2.0.1 (PAL).z64" > nul
assembler\rn64crc.exe -u > nul
@echo %cmdcmdline%|find /i """%~f0""">nul && pause