@echo off
setlocal
cd /d %~dp0
python pdcomp.py "%1"
start excel "%1" > nul