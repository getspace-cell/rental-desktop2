"""
Модуль для запуска игр
Управляет процессом запуска игры через различные лаунчеры
"""
import os
import time
import subprocess
import psutil
import pyautogui
from pathlib import Path
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
        self.monitor_process: Optional[subprocess.Popen] = None
    
    def launch_game(self, game: Dict[str, Any], duration_hours: int = 1):
        """Запускает игру"""
        try:
            # 1. Начинаем аренду через API
            print(f"Начинаем аренду игры {game['title']}...")
            
            try:
                rental_response = self.api_client.start_rental(game['id'], duration_hours, auto_end_active=True)
            except Exception as e:
                # Проверяем, это ли ошибка об активной аренде
                from api_client import ActiveRentalError
                error_str = str(e).lower()
                
                is_active_rental = (
                    isinstance(e, ActiveRentalError) or
                    ("400" in str(e) and ("активная аренда" in error_str or 
                                         "уже есть активная" in error_str or
                                         "завершите текущую" in error_str or
                                         "active rental" in error_str))
                )
                
                if is_active_rental:
                    print(f"Обнаружена активная аренда: {e}")
                    print("Автоматически завершаем активную аренду и пробуем снова...")
                    self._end_active_rental_and_retry(game, duration_hours)
                    return True
                else:
                    # Другая ошибка - пробрасываем дальше
                    raise e
            
            print(f"Ответ start_rental: {rental_response}")
            
            if not rental_response.get('success'):
                raise Exception("Не удалось начать аренду")
            
            session = rental_response['session']
            self.current_session = session
            print(f"Данные сессии: {session}")
            
            # 2. Получаем информацию об активной аренде для получения platform
            rental_info = self.api_client.get_active_rental()
            print(f"Информация об активной аренде: {rental_info}")
            
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
    
    def _end_active_rental_and_retry(self, game: Dict[str, Any], duration_hours: int):
        """Завершает активную аренду и пытается начать новую"""
        try:
            # Получаем информацию об активной аренде
            print("Получаем информацию об активной аренде...")
            rental_info = self.api_client.get_active_rental()
            
            if rental_info.get('hasActiveRental') and rental_info.get('rental'):
                active_rental = rental_info['rental']
                session_id = active_rental.get('id')
                
                if session_id:
                    print(f"Завершаем активную аренду (session_id: {session_id})...")
                    
                    # Завершаем активную аренду
                    try:
                        self.api_client.end_rental(session_id)
                        print("Активная аренда успешно завершена")
                    except Exception as e:
                        print(f"Ошибка при завершении активной аренды: {e}")
                        # Пробуем завершить без session_id
                        try:
                            self.api_client.end_rental()
                            print("Активная аренда завершена (без session_id)")
                        except Exception as e2:
                            print(f"Не удалось завершить активную аренду: {e2}")
                            raise Exception("Не удалось завершить активную аренду")
                else:
                    print("Не удалось определить session_id активной аренды")
                    # Пробуем завершить без session_id
                    try:
                        self.api_client.end_rental()
                        print("Активная аренда завершена (без session_id)")
                    except Exception as e:
                        print(f"Не удалось завершить активную аренду: {e}")
                        raise Exception("Не удалось завершить активную аренду")
            else:
                print("Активная аренда не найдена (возможно, уже завершена)")
            
            # Небольшая задержка перед повторной попыткой
            import time
            time.sleep(1)
            
            # Пытаемся начать новую аренду
            print("Повторная попытка начать аренду...")
            rental_response = self.api_client.start_rental(game['id'], duration_hours, auto_end_active=False)
            
            print(f"Ответ start_rental (повторная попытка): {rental_response}")
            
            if not rental_response.get('success'):
                raise Exception("Не удалось начать аренду после завершения предыдущей")
            
            session = rental_response['session']
            self.current_session = session
            print(f"Данные сессии (повторная попытка): {session}")
            
            # Получаем информацию об активной аренде для получения platform
            rental_info = self.api_client.get_active_rental()
            print(f"Информация об активной аренде: {rental_info}")
            
            platform = 'steam'  # По умолчанию
            if rental_info.get('hasActiveRental') and rental_info.get('rental'):
                platform = 'steam'  # Пока поддерживаем только Steam
            
            # Определяем платформу и запускаем соответствующий лаунчер
            platform = platform.lower()
            
            if platform == 'steam':
                self._launch_steam_game(session, game)
            elif platform == 'epic':
                self._launch_epic_game(session, game)
            elif platform == 'riot':
                self._launch_riot_game(session, game)
            else:
                raise Exception(f"Неподдерживаемая платформа: {platform}")
            
        except Exception as e:
            print(f"Ошибка при завершении активной аренды и повторной попытке: {e}")
            raise Exception(f"Не удалось завершить активную аренду и начать новую: {e}")
    
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
        # Ждем, пока Steam обработает логин/пароль и отправит письмо с кодом
        print("Ожидание запроса кода 2FA от Steam...")
        time.sleep(5)  # Даем больше времени на отправку письма после попытки входа
        
        # Теперь получаем код 2FA
        print("Получаем код двухфакторной авторизации...")
        
        max_retries = 15  # Увеличиваем количество попыток
        two_factor_code = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Бэкенд ожидает sessionId (ID сессии аренды)
                # Если sessionId не указан, бэкенд сам найдет активную сессию по pcKey
                session_id = self.current_session.get('id')
                
                print(f"Запрос 2FA (попытка {attempt + 1}): sessionId={session_id}")
                
                # Передаем sessionId, если он есть (опционально - бэкенд может найти сам)
                response = self.api_client.get_2fa_code(session_id=session_id)
                
                # Проверяем ответ
                if response.get('success'):
                    code = response.get('code')
                    if code:
                        two_factor_code = code
                        print(f"Получен код 2FA: {two_factor_code}")
                        break
                    else:
                        message = response.get('message', 'Код не найден')
                        print(f"Попытка {attempt + 1}: {message}")
                        last_error = message
                else:
                    message = response.get('message', 'Неизвестная ошибка')
                    print(f"Попытка {attempt + 1}: {message}")
                    last_error = message
                    
            except Exception as e:
                error_msg = str(e)
                print(f"Попытка {attempt + 1}: {error_msg}")
                last_error = error_msg
                
                # Если это не ошибка "код не найден", продолжаем попытки
                if "500" in error_msg or "Server Error" in error_msg:
                    # Серверная ошибка - возможно, письмо еще не пришло
                    pass
                elif "404" in error_msg or "403" in error_msg or "401" in error_msg:
                    # Критическая ошибка - прекращаем попытки
                    raise
            
            # Увеличиваем интервал между попытками
            if attempt < max_retries - 1:
                wait_time = 3 + (attempt * 0.5)  # Постепенно увеличиваем время ожидания
                print(f"Ожидание {wait_time:.1f} секунд перед следующей попыткой...")
                time.sleep(wait_time)
        
        if not two_factor_code:
            error_message = f"Не удалось получить код 2FA после {max_retries} попыток"
            if last_error:
                error_message += f". Последняя ошибка: {last_error}"
            raise Exception(error_message)
        
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
        
        # Запускаем процесс мониторинга после запуска игры
        print("Запускаем процесс мониторинга...")
        self._start_monitor_process()
    
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
    
    def _start_monitor_process(self):
        """Запускает процесс мониторинга"""
        if not self.current_session:
            return
        
        try:
            import os
            import sys
            
            # Получаем PID текущего процесса (главного)
            main_pid = os.getpid()
            
            # Путь к скрипту мониторинга
            script_dir = Path(__file__).parent
            monitor_script = script_dir / "process_monitor.py"
            
            if not monitor_script.exists():
                print(f"Предупреждение: скрипт мониторинга не найден: {monitor_script}")
                return
            
            # Запускаем процесс мониторинга
            pc_key = self.api_client.pc_key
            if not pc_key:
                print("Предупреждение: ключ ПК не установлен, невозможно запустить мониторинг")
                return
            
            # Сначала запускаем один процесс мониторинга
            # Он будет отслеживать главный процесс и игру
            monitor_pid = main_pid  # Пока используем тот же PID
            
            args = [
                sys.executable,
                str(monitor_script),
                str(main_pid),
                str(monitor_pid),
                str(self.current_session['id']),
                pc_key
            ]
            
            print(f"Запуск процесса мониторинга: {args}")
            self.monitor_process = subprocess.Popen(
                args,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            print(f"Процесс мониторинга запущен с PID: {self.monitor_process.pid}")
            
            # Теперь запускаем второй процесс мониторинга, который будет следить за первым
            args2 = [
                sys.executable,
                str(monitor_script),
                str(main_pid),
                str(self.monitor_process.pid),
                str(self.current_session['id']),
                pc_key
            ]
            
            monitor_process2 = subprocess.Popen(
                args2,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            print(f"Второй процесс мониторинга запущен с PID: {monitor_process2.pid}")
            
        except Exception as e:
            print(f"Ошибка при запуске процесса мониторинга: {e}")
            import traceback
            traceback.print_exc()
    
    def end_session(self):
        """Завершает сессию аренды"""
        if not self.current_session:
            return
        
        try:
            # Останавливаем процесс мониторинга
            if self.monitor_process:
                try:
                    print("Останавливаем процесс мониторинга...")
                    self.monitor_process.terminate()
                    self.monitor_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Принудительное завершение процесса мониторинга...")
                    self.monitor_process.kill()
                except Exception as e:
                    print(f"Ошибка при остановке процесса мониторинга: {e}")
                finally:
                    self.monitor_process = None
            
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
            import traceback
            traceback.print_exc()

