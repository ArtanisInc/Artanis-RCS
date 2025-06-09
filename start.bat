@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo ARTANIS'S RCS - Recoil Compensation System
echo ===========================================

:: Configuration
set PYTHON_MIN_VERSION=3.8
set LOG_FILE=startup.log

:: Logging function
echo [%date% %time%] Starting RCS system >> %LOG_FILE%

:: Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Detected Python version: %PYTHON_VERSION%

:: Conditional dependencies installation
if exist "requirements.txt" (
    echo Checking Python dependencies...
    
    :: Check if packages are already installed
    pip list --format=freeze > installed_packages.tmp
    
    :: Install only if necessary
    pip install -r requirements.txt --upgrade --quiet
    
    if !errorlevel! equ 0 (
        echo [%date% %time%] Dependencies installed successfully >> %LOG_FILE%
    ) else (
        echo [%date% %time%] ERROR: Dependencies installation failed >> %LOG_FILE%
        echo WARNING: Dependencies installation issue
    )
    
    del installed_packages.tmp 2>nul
) else (
    echo WARNING: requirements.txt file not found
    echo [%date% %time%] requirements.txt missing >> %LOG_FILE%
)

:: Application launch
echo.
echo Starting system...
echo [%date% %time%] Launching main.py >> %LOG_FILE%

python main.py

:: Exit code handling
set EXIT_CODE=%errorlevel%
echo [%date% %time%] Application terminated with code: %EXIT_CODE% >> %LOG_FILE%

if %EXIT_CODE% neq 0 (
    echo.
    echo ERROR: Program terminated abnormally (Code: %EXIT_CODE%)
    echo Check %LOG_FILE% file for more details
    pause
) else (
    echo.
    echo Program terminated normally
)

endlocal
exit /b %EXIT_CODE%