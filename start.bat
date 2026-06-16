@echo off
chcp 65001 >nul
echo Проверка зависимостей...
pip install -r requirements.txt
echo Запуск приложения...
python main.py
pause
