"""
Модуль для управления конфигурацией приложения
Обрабатывает сохранение и загрузку настроек, шифрование ключа
"""
import os
import json
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Config:
    """Класс для управления конфигурацией приложения"""
    
    def __init__(self):
        # Путь к директории конфигурации (AppData/Roaming/RentalDesktop)
        self.config_dir = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "RentalDesktop"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / "config.json"
        self.key_file = self.config_dir / "key.enc"
        self.salt_file = self.config_dir / "salt.dat"
        
        # Настройки по умолчанию
        self.default_settings = {
            "steam_path": "",
            "epic_path": "",
            "riot_path": "",
            "battlenet_path": "",
            "vkplay_path": "",
            "ea_path": ""
        }
        
        self._ensure_salt()
    
    def _ensure_salt(self):
        """Создает соль для шифрования, если её нет"""
        if not self.salt_file.exists():
            salt = os.urandom(16)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
    
    def _get_encryption_key(self) -> bytes:
        """Получает ключ шифрования на основе соли и системной информации"""
        with open(self.salt_file, 'rb') as f:
            salt = f.read()
        
        # Используем комбинацию системной информации для генерации ключа
        # Это делает ключ уникальным для каждой машины
        import platform
        machine_id = f"{platform.node()}{platform.processor()}".encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id))
        return key
    
    def save_key(self, pc_key: str) -> bool:
        """Сохраняет ключ ПК в зашифрованном виде"""
        try:
            fernet = Fernet(self._get_encryption_key())
            encrypted_key = fernet.encrypt(pc_key.encode())
            
            with open(self.key_file, 'wb') as f:
                f.write(encrypted_key)
            
            return True
        except Exception as e:
            print(f"Ошибка при сохранении ключа: {e}")
            return False
    
    def load_key(self) -> str | None:
        """Загружает и расшифровывает ключ ПК"""
        try:
            if not self.key_file.exists():
                return None
            
            with open(self.key_file, 'rb') as f:
                encrypted_key = f.read()
            
            fernet = Fernet(self._get_encryption_key())
            decrypted_key = fernet.decrypt(encrypted_key)
            
            return decrypted_key.decode()
        except Exception as e:
            print(f"Ошибка при загрузке ключа: {e}")
            return None
    
    def delete_key(self):
        """Удаляет сохраненный ключ"""
        if self.key_file.exists():
            self.key_file.unlink()
    
    def load_settings(self) -> dict:
        """Загружает настройки приложения"""
        if not self.config_file.exists():
            return self.default_settings.copy()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Объединяем с настройками по умолчанию
            result = self.default_settings.copy()
            result.update(settings)
            return result
        except Exception as e:
            print(f"Ошибка при загрузке настроек: {e}")
            return self.default_settings.copy()
    
    def save_settings(self, settings: dict):
        """Сохраняет настройки приложения"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка при сохранении настроек: {e}")
    
    def get_setting(self, key: str, default=None):
        """Получает значение настройки"""
        settings = self.load_settings()
        return settings.get(key, default)
    
    def set_setting(self, key: str, value):
        """Устанавливает значение настройки"""
        settings = self.load_settings()
        settings[key] = value
        self.save_settings(settings)

