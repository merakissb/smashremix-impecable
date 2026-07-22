assembler\bass.exe -o "Impecable Edition v2.0.1.z64" main.asm -sym logfile.log
assembler\chksum64.exe "Impecable Edition v2.0.1.z64" > nul
assembler\rn64crc.exe -u > nul
@echo %cmdcmdline%|find /i """%~f0""">nul && pause