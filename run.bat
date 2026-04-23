
#هذا ينتقل  مباشرة الى المتصفح ثم   اعمل له تحديث  لكي تظهر الصفحة  

::@echo off
::cd /d %~dp0

::call env\Scripts\activate

::echo Starting Django server...

:: ============================================
:: تشغيل السيرفر مع حفظ الـ PID
:: ============================================
::start "DJANGO_SERVER" /B python manage.py runserver 8005

:: انتظار بسيط للتأكد من التشغيل
::timeout /t 2 >nul

:: حفظ PID الخاص بعملية python
::for /f "tokens=2" %%a in ('tasklist ^| find "python.exe"') do (
   :: echo %%a > server.pid
    ::goto done
::)

::done
::echo Server started
::exit  


# هذا بعد ان يتم تشغيل السرفر   يتم  الانتقال الى المتصفح بعد تشغيل السرفر 

@echo off
cd /d %~dp0

call env\Scripts\activate

echo Starting Django server...

:: ============================================
:: تشغيل السيرفر في الخلفية
:: ============================================
start /B python manage.py runserver 8005

echo Waiting for server to start...

:: ============================================
:: انتظار حتى يصبح البورت 8005 شغال فعليًا
:: ============================================
:check
timeout /t 1 >nul

netstat -an | find "8005" | find "LISTENING" >nul

if errorlevel 1 (
    goto check
)

:: ============================================
:: عند نجاح تشغيل السيرفر → افتح المتصفح
:: ============================================
echo Server is READY ✔
start http://127.0.0.1:8005

exit



