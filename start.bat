@echo off

python -V >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python not found, exit
    pause
    exit /b 1
)

python -c "import venv" >NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python venv module not found, exit
    pause
    exit /b 1
)

cd /d "%~dp0"

if not exist .\venv\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment, exit
        pause
        exit /b 1
    )
)

call .\venv\Scripts\activate.bat

python launch.py %*
set EXIT_CODE=%ERRORLEVEL%

pause
exit /b %EXIT_CODE%
