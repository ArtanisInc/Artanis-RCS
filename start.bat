@echo off
setlocal enabledelayedexpansion

echo ===========================================
echo ARTANIS'S RCS - Recoil Compensation System
echo ===========================================

:: Configuration
set PYTHON_MIN_VERSION=3.9

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
        echo Dependencies installed successfully
    ) else (
        echo WARNING: Dependencies installation issue
        pause
    )

    del installed_packages.tmp 2>nul
) else (
    echo WARNING: requirements.txt file not found
    pause
)

:: Application launch
echo.
echo Starting system...

python main.py

:: Exit code handling
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo.
    echo ERROR: Program terminated abnormally (Code: %EXIT_CODE%)
    pause
) else (
    echo.
    echo Program terminated normally
)

endlocal
exit /b %EXIT_CODE%