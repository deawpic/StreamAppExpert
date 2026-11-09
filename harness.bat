@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%~dp0;%PYTHONPATH%
python -m harness.cli %*
