@echo off
cd /d "%~dp0..\.."
"%~dp0..\..\.venv-gpu\Scripts\python.exe" -B "%~dp0launch.py"
if errorlevel 1 pause
