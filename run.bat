@echo off
echo ====== Starting Installation and Test Process ======
echo [%date% %time%]

echo.
echo [Step 1/4] Checking Python installation...
python --version
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH!
    pause
    exit /b 1
)

echo.
echo [Step 2/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo [Step 3/4] Running tests...
python -m pytest tests --verbose
if errorlevel 1 (
    echo Error: Tests failed!
    pause
    exit /b 1
) else (
    echo Success: All tests passed!
)

echo.
echo [Step 4/4] Starting main application...
echo Press Ctrl+C to exit the application
python -m chate2e.main
if errorlevel 1 (
    echo Error: Application failed to start!
    pause
    exit /b 1
)

echo.
echo ====== All steps completed successfully ======
echo [%date% %time%]
pause