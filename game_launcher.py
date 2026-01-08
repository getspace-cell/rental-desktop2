"""
Модуль для запуска игр
Управляет процессом запуска игры через различные лаунчеры
"""
import time
import subprocess
import psutil
import pyautogui
from typing import Optional, Dict, Any
from api_client import APIClient
from steam_manager import SteamManager
from config import Config

class GameLauncher:
    """Класс для запуска игр"""
    
    def __init__(self, api_client: APIClient, config: Config):
        self.api_client = api_client
        self.config = config
        self.current_session: Optional[Dict[str, Any]] = None
        self.steam_manager: Optional[SteamManager] = None
        self.game_process: Optional[psutil.Process] = None
    
    def launch_game(self, game: Dict[str, Any], duration_hours: int = 1):
        """Запускает игру"""
        try:
            # 1. Начинаем аренду через API
            print(f"Начинаем аренду игры {game['title']}...")
            rental_response = self.api_client.start_rental(game['id'], duration_hours)
            
            if not rental_response.get('success'):
                raise Exception("Не удалось начать аренду")
            
            session = rental_response['session']
            self.current_session = session
            
            # 2. Получаем информацию об активной аренде для получения platform
            rental_info = self.api_client.get_active_rental()
            platform = 'steam'  # По умолчанию
            if rental_info.get('hasActiveRental') and rental_info.get('rental'):
                # Platform может быть в данных аккаунта, но обычно это steam для большинства игр
                # Определяем платформу по наличию steam_url в игре
                platform = 'steam'  # Пока поддерживаем только Steam
            
            # 3. Определяем платформу и запускаем соответствующий лаунчер
            platform = platform.lower()
            
            if platform == 'steam':
                self._launch_steam_game(session, game)
            elif platform == 'epic':
                self._launch_epic_game(session, game)
            elif platform == 'riot':
                self._launch_riot_game(session, game)
            else:
                raise Exception(f"Неподдерживаемая платформа: {platform}")
            
            return True
            
        except Exception as e:
            print(f"Ошибка при запуске игры: {e}")
            # Завершаем сессию при ошибке
            if self.current_session:
                try:
                    self.api_client.end_rental(self.current_session['id'])
                except:
                    pass
            return False
    
    def _launch_steam_game(self, session: Dict[str, Any], game: Dict[str, Any]):
        """Запускает игру через Steam"""
        steam_path = self.config.get_setting('steam_path')
        if not steam_path:
            raise Exception("Путь к Steam не указан в настройках")
        
        self.steam_manager = SteamManager(steam_path)
        
        # Запускаем Steam
        self.steam_manager.start_steam()
        time.sleep(3)
        
        # Шаг 1: Входим в Steam с логином и паролем (без 2FA)
        print("Входим в Steam...")
        self.steam_manager.login_to_steam(
            session['email'],
            session['password']
        )
        
        # Шаг 2: После нажатия "Войти" Steam запросит код 2FA
        # Теперь получаем код 2FA
        print("Получаем код двухфакторной авторизации...")
        time.sleep(3)  # Даем время на отправку письма после попытки входа
        
        max_retries = 10
        two_factor_code = None
        
        for attempt in range(max_retries):
            try:
                response = self.api_client.get_2fa_code(self.current_session['id'])
                if response.get('success') and response.get('code'):
                    two_factor_code = response['code']
                    print(f"Получен код 2FA: {two_factor_code}")
                    break
            except Exception as e:
                print(f"Попытка {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(3)
        
        if not two_factor_code:
            raise Exception("Не удалось получить код 2FA")
        
        # Шаг 3: Вводим код 2FA
        print("Вводим код 2FA...")
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'a')  # Очищаем поле ввода
        time.sleep(0.2)
        pyautogui.write(two_factor_code, interval=0.1)
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(5)  # Ждем завершения входа
        
        time.sleep(5)
        
        # Блокируем Steam UI
        print("Блокируем доступ к Steam UI...")
        self.steam_manager.block_steam_ui()
        
        # Запускаем игру
        # Для CS2 нужно использовать правильный App ID
        # Обычно это можно получить из steam_url игры
        steam_url = game.get('steamUrl', '')
        app_id = None
        
        if steam_url:
            # Извлекаем App ID из URL
            import re
            match = re.search(r'/app/(\d+)', steam_url)
            if match:
                app_id = int(match.group(1))
            else:
                # Пробуем найти в других форматах URL
                match = re.search(r'appid[=:](\d+)', steam_url, re.IGNORECASE)
                if match:
                    app_id = int(match.group(1))
        
        if not app_id:
            # Для CS2 используем известный App ID (730 для CS:GO/CS2)
            # Можно добавить маппинг известных игр
            game_title_lower = game.get('title', '').lower()
            if 'counter-strike' in game_title_lower or 'cs2' in game_title_lower or 'cs:go' in game_title_lower:
                app_id = 730
            else:
                raise Exception("Не удалось определить App ID игры. Укажите Steam URL в настройках игры.")
        
        print(f"Запускаем игру с App ID: {app_id}")
        self.steam_manager.launch_game(app_id)
        
        # Ждем запуска игры
        time.sleep(10)
        
        # Находим процесс игры
        # Ждем немного больше времени для запуска игры
        time.sleep(10)
        
        game_title = game['title'].lower()
        self.game_process = None
        
        # Пробуем найти по известным именам процессов (более надежно)
        # Можно расширить список для других игр
        process_names = []
        
        if 'counter-strike' in game_title or 'cs2' in game_title or 'cs:go' in game_title:
            process_names = ['cs2.exe', 'csgo.exe', 'hl.exe']
        elif 'dota' in game_title:
            process_names = ['dota2.exe']
        elif 'half-life' in game_title:
            process_names = ['hl.exe', 'hl2.exe']
        else:
            # Пробуем найти по названию игры
            process_names = [f"{game_title.replace(' ', '').replace(':', '').lower()}.exe"]
        
        for name in process_names:
            self.game_process = self.steam_manager.find_game_process(name)
            if self.game_process:
                print(f"Найден процесс игры: {name}")
                break
        
        if not self.game_process:
            print("Предупреждение: процесс игры не найден, но игра может быть запущена")
    
    def _launch_epic_game(self, session: Dict[str, Any], game: Dict[str, Any]):
        """Запускает игру через Epic Games"""
        # TODO: Реализовать запуск через Epic Games
        raise NotImplementedError("Epic Games лаунчер пока не реализован")
    
    def _launch_riot_game(self, session: Dict[str, Any], game: Dict[str, Any]):
        """Запускает игру через Riot Games"""
        # TODO: Реализовать запуск через Riot Games
        raise NotImplementedError("Riot Games лаунчер пока не реализован")
    
    def monitor_game(self):
        """Мониторит процесс игры и программы"""
        if not self.current_session:
            return False
        
        # Если процесс игры не был найден при запуске, все равно проверяем наличие активной аренды
        if self.game_process:
            try:
                # Проверяем, запущена ли игра
                if not self.game_process.is_running():
                    print("Игра была закрыта")
                    self.end_session()
                    return False
                
                return True
            except psutil.NoSuchProcess:
                print("Процесс игры не найден")
                self.end_session()
                return False
        else:
            # Если процесс не был найден, проверяем активную аренду через API
            # Если аренда все еще активна, продолжаем мониторинг
            try:
                rental_info = self.api_client.get_active_rental()
                if not rental_info.get('hasActiveRental'):
                    print("Аренда завершена")
                    self.end_session()
                    return False
                return True
            except:
                # В случае ошибки API продолжаем мониторинг
                return True
    
    def end_session(self):
        """Завершает сессию аренды"""
        if not self.current_session:
            return
        
        try:
            # Закрываем Steam
            if self.steam_manager:
                print("Закрываем Steam...")
                self.steam_manager.close_steam()
            
            # Завершаем сессию через API
            print("Завершаем сессию аренды...")
            self.api_client.end_rental(self.current_session['id'])
            
            self.current_session = None
            self.steam_manager = None
            self.game_process = None
            
        except Exception as e:
            print(f"Ошибка при завершении сессии: {e}")

