@echo off
chcp 65001 > nul
echo [*] Đang khởi động cụm Agent SA (8004) và PO (8005)...
python scripts\run_local.py up
pause
