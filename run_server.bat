@echo off
call venv\Scripts\activate
cd Backend
..\venv\Scripts\uvicorn app:app --reload
pause
