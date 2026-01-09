@echo off
echo Удаление сохраненного ключа...
del "%APPDATA%\RentalDesktop\key.enc"
if %errorlevel% == 0 (
    echo Ключ успешно удален!
) else (
    echo Файл ключа не найден или уже удален.
)
pause

