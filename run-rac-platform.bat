@echo off
setlocal
cd /d "%~dp0"
python -m ruthless_pipeline.platform_runtime --open
if errorlevel 1 (
  echo.
  echo RAC Research Workbench could not start.
  echo Install the project first with: python -m pip install -e .
  pause
)
