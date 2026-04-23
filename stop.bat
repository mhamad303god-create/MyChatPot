@echo off
echo Finding process on port 8005...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8005') do (
    taskkill /F /PID %%a
)

echo Server stopped.
pause