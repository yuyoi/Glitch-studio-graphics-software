@echo off
rem Glitch Lab: drag one or more PNG layers onto this file. Each gets a textured copy (name_glitch.png) next to it.
rem Change the numbers below to taste: amount (how much is eaten), clump (patch size), grain, edge (protect lines).
for %%F in (%*) do python "%~dp0glitch_tex.py" "%%~F" --amount 0.4 --clump 5 --grain 0.5 --edge 0.6
pause
