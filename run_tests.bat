@echo off
call venv\Scripts\activate
pip install requests
python test_utils\create_sample.py
python test_utils\test_api.py
pause
