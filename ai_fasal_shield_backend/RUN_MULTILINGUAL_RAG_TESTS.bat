@echo off
setlocal

echo ================================================================
echo AI Fasal Shield V11 - Language-Selected Multilingual RAG Tests
echo ================================================================

echo.
echo [1/5] Fast unit tests
python -m pytest -q tests\test_language_selected_rag.py tests\test_qwen_focused_questions.py tests\test_plant_part_validator.py tests\test_symptom_rag.py tests\test_embedding_backend.py
if errorlevel 1 goto :fail

echo.
echo [2/5] Urdu RAG - 10 cases
python scripts\evaluate_language_selected_rag.py --language urdu
if errorlevel 1 echo NOTE: Review Urdu Top-3 scores before tuning thresholds.

echo.
echo [3/5] Punjabi/Shahmukhi RAG - 10 cases
python scripts\evaluate_language_selected_rag.py --language punjabi
if errorlevel 1 echo NOTE: Review Punjabi Top-3 scores before tuning thresholds.

echo.
echo [4/5] English RAG - 10 cases
python scripts\evaluate_language_selected_rag.py --language english
if errorlevel 1 echo NOTE: Review English Top-3 scores before tuning thresholds.

echo.
echo [5/5] Complete farmer-language pipeline
python scripts\evaluate_multilingual_pipeline.py
if errorlevel 1 echo NOTE: Check Qwen extraction separately from RAG mapping.

echo.
echo Finished.
goto :eof

:fail
echo Unit tests failed. Fix code before live model evaluation.
exit /b 1
