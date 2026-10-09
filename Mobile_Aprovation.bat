@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo uv nao foi encontrado. Instale uv e adicione-o ao PATH.
    pause
    exit /b 1
)

uv run --link-mode=copy --with-requirements requirements.txt streamlit run streamlit_app.py
if errorlevel 1 (
    echo Nao foi possivel iniciar a aplicacao Streamlit.
    pause
    exit /b 1
)

endlocal
