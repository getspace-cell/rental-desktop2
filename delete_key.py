"""
Скрипт для удаления сохраненного ключа
"""
import os
from pathlib import Path

config_dir = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "RentalDesktop"
key_file = config_dir / "key.enc"

if key_file.exists():
    key_file.unlink()
    print(f"Ключ успешно удален: {key_file}")
else:
    print(f"Файл ключа не найден: {key_file}")


