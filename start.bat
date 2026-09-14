@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

title Semantic Search - Full Auto Start

echo ============================================================
echo    SEMANTIC SEARCH - FULL AUTO START
echo ============================================================
echo.

REM --- 0. Ensure Python is available --------------------------
set "PYTHON_CMD="
set "PYTHON_DIR=%~dp0python-embed"
set "PY_VERSION=3.12.9"

REM 0.1. Проверяем системный py
where py >nul 2>&1
if not errorlevel 1 (
    py --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py"
        goto :python_ready
    )
)

REM 0.2. Проверяем системный python
where python >nul 2>&1
if not errorlevel 1 (
    python --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        goto :python_ready
    )
)

REM 0.3. Проверяем уже распакованную embeddable-версию
if exist "%PYTHON_DIR%\python.exe" (
    "%PYTHON_DIR%\python.exe" --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=%PYTHON_DIR%\python.exe"
        goto :python_ready
    )
)

REM 0.4. Ничего нет — скачиваем embeddable Python
echo [0/7] No Python found. Downloading embeddable Python %PY_VERSION%...
echo.

set "EMBED_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-embed-amd64.zip"

REM Пробуем curl (есть в Windows 10 1803+)
where curl >nul 2>&1
if not errorlevel 1 (
    curl -L -o "python-embed.zip" "%EMBED_URL%"
)

REM Если curl не справился — PowerShell
if not exist "python-embed.zip" (
    powershell -NoProfile -Command ^
        "try { Invoke-WebRequest -Uri '%EMBED_URL%' -OutFile 'python-embed.zip' -UseBasicParsing } catch { exit 1 }"
)

if not exist "python-embed.zip" (
    echo       [ERROR] Download failed.
    echo       Install Python manually from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo       Download OK. Extracting...
powershell -NoProfile -Command ^
    "Expand-Archive -Path 'python-embed.zip' -DestinationPath '%PYTHON_DIR%' -Force"

del "python-embed.zip" >nul 2>&1

if not exist "%PYTHON_DIR%\python.exe" (
    echo       [ERROR] Extraction failed.
    pause
    exit /b 1
)

REM 0.5. Включаем pip в embeddable-версии
REM В _pth-файле нужно раскомментировать "import site"
for %%f in ("%PYTHON_DIR%\python*._pth") do (
    powershell -NoProfile -Command ^
        "(Get-Content '%%f') -replace '#import site','import site' | Set-Content '%%f'"
)

REM 0.6. Скачиваем get-pip.py и ставим pip
echo       Setting up pip...
curl -L -o "%PYTHON_DIR%\get-pip.py" "https://bootstrap.pypa.io/get-pip.py" 2>nul
if not exist "%PYTHON_DIR%\get-pip.py" (
    powershell -NoProfile -Command ^
        "try { Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py' -UseBasicParsing } catch { exit 1 }"
)

if exist "%PYTHON_DIR%\get-pip.py" (
    "%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location
    del "%PYTHON_DIR%\get-pip.py" >nul 2>&1
)

set "PYTHON_CMD=%PYTHON_DIR%\python.exe"
echo       OK. Python ready.
echo.

:python_ready
echo Using interpreter: %PYTHON_CMD%
echo.

REM --- 1. Create venv if missing -----------------------------
if not exist "venv\Scripts\activate.bat" (
    echo [1/7] Creating venv...
    "%PYTHON_CMD%" -m venv venv
    if errorlevel 1 (
        echo       [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
    echo       OK
) else (
    echo [1/7] venv already exists.
)
echo.

REM --- 2. Activate venv --------------------------------------
echo [2/7] Activating venv...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo       [ERROR] Failed to activate venv!
    pause
    exit /b 1
)
echo       OK
echo.

REM --- 3. Install dependencies -------------------------------
if exist "requirements.txt" (
    echo [3/7] Installing PyTorch ^(CPU^) with progress...
    echo       Size: ~150 MB, may take 2-5 minutes.
    echo.
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    if errorlevel 1 (
        echo       [WARNING] PyTorch install failed.
    ) else (
        echo       OK
    )
    echo.

    echo       Installing other dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo       [WARNING] Some dependencies failed to install.
    ) else (
        echo       OK
    )
) else (
    echo [3/7] [WARNING] requirements.txt not found.
)
echo.

REM --- 4. Download corpus if missing -------------------------
if not exist "wikipedia_docs" (
    echo [4/7] wikipedia_docs not found. Running parsing.py...
    python parsing.py
    if errorlevel 1 (
        echo       [ERROR] parsing.py failed!
        pause
        exit /b 1
    )
    echo       OK
) else (
    dir /b /a-d "wikipedia_docs\*.txt" >nul 2>&1
    if errorlevel 1 (
        echo [4/7] wikipedia_docs is empty. Running parsing.py...
        python parsing.py
        if errorlevel 1 (
            echo       [ERROR] parsing.py failed!
            pause
            exit /b 1
        )
        echo       OK
    ) else (
        echo [4/7] wikipedia_docs already populated.
    )
)
echo.

REM --- 5. Build tfidf.exe if missing -------------------------
if not exist "tfidf.exe" (
    echo [5/7] tfidf.exe not found. Building from tfidf.cpp...
    where g++ >nul 2>&1
    if errorlevel 1 (
        echo       [ERROR] g++ not found. Install MinGW or place tfidf.exe manually.
        pause
        exit /b 1
    )
    g++ -std=c++17 tfidf.cpp -o tfidf.exe
    if errorlevel 1 (
        echo       [ERROR] Compilation failed!
        pause
        exit /b 1
    )
    echo       OK
) else (
    echo [5/7] tfidf.exe already exists.
)
echo.

REM --- 6. Build vectors.json if missing ----------------------
if not exist "vectors.json" (
    echo [6/7] vectors.json not found. Running tfidf.exe...
    tfidf.exe
    if errorlevel 1 (
        echo       [ERROR] tfidf.exe failed!
        pause
        exit /b 1
    )
    echo       OK
) else (
    echo [6/7] vectors.json already exists.
)
echo.

REM --- 7. Start server ---------------------------------------
echo [7/7] Starting FastAPI server...
echo.
echo ============================================================
echo    SERVER STARTED
echo ============================================================
echo    Open:    http://127.0.0.1:8000
echo    Docs:    http://127.0.0.1:8000/docs
echo.
echo    Modes:
echo      - TF-IDF   (lexical)
echo      - SBERT    (semantic)
echo      - Hybrid   (RRF)
echo.
echo    Stop server: Ctrl+C
echo ============================================================
echo.

python search_api.py
