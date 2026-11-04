@echo off
chcp 65001 > nul
echo [*] Đang dừng cụm Agent SA và PO...
python scripts\run_local.py down
pause
