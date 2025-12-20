@echo off
echo Starting Dashboard Server...
start "Robin Dashboard" python server.py

echo Waiting 5 seconds...
timeout /t 5

echo Starting Trading Bot...
start "Robin Trading Bot" python bot.py

echo.
echo Both processes started!
echo Dashboard: http://localhost:5000
echo Check the new windows for logs.
pause
