@echo off
set FECHA=%date:~-4%%date:~3,2%%date:~0,2%
set ORIGEN=data
set DESTINO=backup

if not exist %DESTINO% (
    mkdir %DESTINO%
)

xcopy %ORIGEN% %DESTINO%\backup_%FECHA% /E /I /Y
