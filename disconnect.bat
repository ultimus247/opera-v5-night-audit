@echo off
REM ============================================================
REM Disconnect RDP without logging off
REM
REM Keeps the desktop session alive so scheduled tasks (night audit)
REM can still capture screenshots and interact with the screen.
REM
REM DO NOT close the RDP window with X or use Start > Log off.
REM Only use this script to disconnect.
REM ============================================================

tscon %sessionname% /dest:console
