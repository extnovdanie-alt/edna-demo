@echo off
setlocal
cd /d "%~dp0"
title E.D.N.A. - Demonstracao local
if exist ".venv\Scripts\python.exe" goto venv
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" goto bundled
where py >nul 2>nul
if not errorlevel 1 goto pylauncher
where python >nul 2>nul
if not errorlevel 1 goto python
echo Python nao encontrado. Instale Python 3.11 ou superior e siga README.md.
goto end
:venv
".venv\Scripts\python.exe" -u iniciar_demo.py
goto end
:bundled
"%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -u iniciar_demo.py
goto end
:pylauncher
py -3 -u iniciar_demo.py
goto end
:python
python -u iniciar_demo.py
:end
echo.
echo O aplicativo foi encerrado. Se houve um erro, consulte a mensagem acima.
pause
