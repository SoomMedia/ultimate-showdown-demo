@echo off
:: ─────────────────────────────────────────────────
::  Ultimate Showdown — Launcher Build Script
::  Requires: pip install pyinstaller customtkinter requests pillow
:: ─────────────────────────────────────────────────

echo Installing dependencies...
pip install pyinstaller customtkinter requests pillow

echo.
echo Building launcher.exe...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "UltimateShowdown Launcher" ^
  --icon "icon.ico" ^
  --add-data "icon.ico;." ^
  launcher.py

echo.
echo ✅ Done! Find your exe in the /dist folder.
pause
