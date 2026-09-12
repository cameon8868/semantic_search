@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM   ЗАПУСК СЕРВЕРА СЕМАНТИЧЕСКОГО ПОИСКА
REM   Проект: semantic_search1
REM ============================================================

title Семантический поиск - запуск сервера

echo ============================================================
echo    ЗАПУСК СЕРВЕРА СЕМАНТИЧЕСКОГО ПОИСКА
echo ============================================================
echo.

REM --- 1. Проверка виртуального окружения ---
if not exist "venv\Scripts\activate.bat" (
    echo [ОШИБКА] Виртуальное окружение venv не найдено!
    echo.
    echo Создайте его командой:
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [1/5] Активация виртуального окружения...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ОШИБКА] Не удалось активировать venv!
    pause
    exit /b 1
)
echo       OK
echo.

REM --- 2. Проверка requirements.txt ---
if not exist "requirements.txt" (
    echo [ПРЕДУПРЕЖДЕНИЕ] Файл requirements.txt не найден.
    echo Пропускаю проверку зависимостей.
) else (
    echo [2/5] Проверка зависимостей...
    pip install -q -r requirements.txt
    if errorlevel 1 (
        echo [ПРЕДУПРЕЖДЕНИЕ] Не все зависимости установлены.
    ) else (
        echo       OK
    )
)
echo.

REM --- 3. Проверка vectors.json ---
if not exist "vectors.json" (
    echo [ОШИБКА] Файл vectors.json не найден!
    echo.
    echo Сначала запустите индексацию:
    echo    tfidf.exe
    echo.
    pause
    exit /b 1
)
echo [3/5] Проверка vectors.json... OK
echo.

REM --- 4. Проверка SBERT-модели (кеш HuggingFace) ---
echo [4/5] Проверка кеша SBERT...
if exist "%USERPROFILE%\.cache\huggingface\hub" (
    echo       Кеш найден
) else (
    echo       Кеш не найден - модель будет скачана при первом запуске
    echo       ^(объём ~470 МБ, требует интернет^)
)
echo.

REM --- 5. Запуск сервера ---
echo [5/5] Запуск сервера...
echo.
echo ============================================================
echo    СЕРВЕР ЗАПУЩЕН
echo ============================================================
echo    Запуск, перейдите по ссылке:    http://127.0.0.1:8000
echo.
echo    Режимы поиска:
echo      - TF-IDF  (лексический)
echo      - SBERT   (семантический)
echo      - Гибрид  (RRF)
echo.
echo    Для остановки нажмите Ctrl+C
echo ============================================================
echo.

python search_api.py

REM --- Если сервер упал ---
echo.
echo ============================================================
echo    СЕРВЕР ОСТАНОВЛЕН
echo ============================================================
pause
endlocal