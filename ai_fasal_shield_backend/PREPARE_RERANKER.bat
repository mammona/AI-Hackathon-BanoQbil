@echo off
setlocal
cd /d %~dp0
python -m scripts.prepare_qwen_reranker
if errorlevel 1 (
  echo.
  echo Reranker setup failed. Keep this window open and share the error.
  pause
  exit /b 1
)
echo.
echo Qwen3-Reranker-0.6B is ready.
pause
