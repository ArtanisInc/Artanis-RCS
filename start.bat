@echo off
setlocal enabledelayedexpansion

:: --- Configuration ---
set "PYTHON_MIN_VERSION=3.9"
set "REQUIRED_FILE=requirements.txt"
set "MAIN_SCRIPT=main.py"

echo ===========================================
echo ARTANIS'S RCS - Recoil Compensation System
echo ===========================================

:: --- Main Execution Flow ---
call :check_prerequisites
if !errorlevel! neq 0 (
    echo FATAL ERROR: Prerequisites not met. Exiting.
    goto :end
)

call :check_python_version
if !errorlevel! neq 0 (
    echo FATAL ERROR: Python version check failed. Exiting.
    goto :end
)

call :install_dependencies
if !errorlevel! neq 0 (
    echo FATAL ERROR: Dependency installation failed. Exiting.
    goto :end
)

call :launch_application
set "EXIT_CODE=!errorlevel!"

goto :exit_handler

:: --- Subroutines ---

:check_prerequisites
echo.
echo :: Checking for prerequisites...
where /q python
if !errorlevel! neq 0 (
    echo ERROR: 'python' command not found. Please ensure Python is installed and in your system PATH.
    exit /b 1
)
where /q pip
if !errorlevel! neq 0 (
    echo WARNING: 'pip' command not found. Cannot install dependencies automatically.
    exit /b 2
)
echo Prerequisites met.
exit /b 0

:check_python_version
echo.
echo :: Verifying Python version...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo Detected Python version: %PYTHON_VERSION%

for /f "tokens=1,2,3 delims=." %%a in ("%PYTHON_VERSION%") do (
    set "MAJOR=%%a"
    set "MINOR=%%b"
    set "PATCH=%%c"
)

for /f "tokens=1,2,3 delims=." %%x in ("%PYTHON_MIN_VERSION%") do (
    set "MIN_MAJOR=%%x"
    set "MIN_MINOR=%%y"
)

if !MAJOR! lss !MIN_MAJOR! (
    echo WARNING: Python !PYTHON_VERSION! is older than the required minimum !PYTHON_MIN_VERSION!.
    echo Please upgrade Python to ensure full compatibility.
) else if !MAJOR! equ !MIN_MAJOR! (
    if !MINOR! lss !MIN_MINOR! (
        echo WARNING: Python !PYTHON_VERSION! is older than the required minimum !PYTHON_MIN_VERSION!.
        echo Please upgrade Python to ensure full compatibility.
    ) else (
        echo Python version is compatible.
    )
) else (
    echo Python version is compatible.
)
exit /b 0

:install_dependencies
echo.
echo :: Checking Python dependencies...
if not exist "%REQUIRED_FILE%" (
    echo WARNING: "%REQUIRED_FILE%" not found. Skipping dependency installation.
    exit /b 0
)

pip install -r "%REQUIRED_FILE%" --upgrade --quiet
if !errorlevel! neq 0 (
    echo ERROR: Dependency installation failed. Please check the above errors.
    exit /b 1
)

echo Dependencies installed successfully.
exit /b 0

:launch_application
echo.
echo :: Starting application...
if not exist "%MAIN_SCRIPT%" (
    echo ERROR: Main script "%MAIN_SCRIPT%" not found.
    exit /b 1
)

python "%MAIN_SCRIPT%"
exit /b !errorlevel!

:: --- Exit ---

:exit_handler
echo.
if %EXIT_CODE% neq 0 (
    echo ERROR: Program terminated abnormally (Code: %EXIT_CODE%)
) else (
    echo Program terminated normally.
)

:end
echo.
echo Press any key to close this window...
pause > nul
endlocal
exit /b %EXIT_CODE%