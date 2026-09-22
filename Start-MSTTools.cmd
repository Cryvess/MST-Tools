@echo off
setlocal
cd /d "%~dp0"
title MSTTools v1.2 - Developer Command Center
python -m msttools
if errorlevel 1 (
  echo.
  echo If dependencies are missing, run: python -m pip install .
  pause
)
