@echo off
echo Starting FluxRoute...
echo.
echo [Backend] http://localhost:8000
echo [Frontend] http://localhost:3000
echo.
echo Press Ctrl+C to stop both servers.
echo.

start "FluxRoute Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload"
timeout /t 3 /nobreak >nul
start "FluxRoute Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
