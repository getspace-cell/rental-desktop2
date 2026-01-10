"""
Модуль для двухпроцессного мониторинга
Оба процесса следят друг за другом и за игрой
"""
import os
import sys
import time
import json
import psutil
import subprocess
from pathlib import Path
from typing import Optional
import sys
from pathlib import Path

# Добавляем путь к модулям в sys.path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from api_client import APIClient
    from config import Config
    from steam_manager import SteamManager
except ImportError:
    # Если импорт не удался, пробуем из текущей директории
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_client", script_dir / "api_client.py")
    api_client_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_client_module)
    
    spec = importlib.util.spec_from_file_location("config", script_dir / "config.py")
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    spec = importlib.util.spec_from_file_location("steam_manager", script_dir / "steam_manager.py")
    steam_manager_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(steam_manager_module)
    
    APIClient = api_client_module.APIClient
    Config = config_module.Config
    SteamManager = steam_manager_module.SteamManager

class ProcessMonitor:
    """Класс для мониторинга процессов"""
    
    def __init__(self, main_pid: int, monitor_pid: int, session_id: int, pc_key: str):
        self.main_pid = main_pid
        self.monitor_pid = monitor_pid
        self.session_id = session_id
        self.pc_key = pc_key
        self.config = Config()
        self.api_client = APIClient()
        self.api_client.set_key(pc_key)
        self.running = True
        
        # Файл для обмена информацией между процессами
        self.heartbeat_file = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "RentalDesktop" / "heartbeat.json"
        self.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        
        # PID файлы для идентификации процессов
        self.pid_file = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "RentalDesktop" / f"pid_{os.getpid()}.json"
        
        # Сохраняем информацию о процессе
        self._save_process_info()
    
    def _save_process_info(self):
        """Сохраняет информацию о процессе"""
        info = {
            "pid": os.getpid(),
            "main_pid": self.main_pid,
            "monitor_pid": self.monitor_pid,
            "session_id": self.session_id,
            "start_time": time.time()
        }
        with open(self.pid_file, 'w') as f:
            json.dump(info, f)
    
    def _load_heartbeat(self) -> Optional[dict]:
        """Загружает heartbeat файл"""
        try:
            if self.heartbeat_file.exists():
                with open(self.heartbeat_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def _update_heartbeat(self):
        """Обновляет heartbeat файл"""
        try:
            heartbeat = {
                "pid": os.getpid(),
                "timestamp": time.time(),
                "session_id": self.session_id
            }
            with open(self.heartbeat_file, 'w') as f:
                json.dump(heartbeat, f)
        except Exception as e:
            print(f"Ошибка обновления heartbeat: {e}")
    
    def is_process_running(self, pid: int) -> bool:
        """Проверяет, запущен ли процесс"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            # Процесс существует, но нет доступа - считаем что работает
            return True
        except:
            return False
    
    def check_heartbeat(self, pid: int) -> bool:
        """Проверяет heartbeat другого процесса"""
        heartbeat = self._load_heartbeat()
        if not heartbeat:
            return False
        
        # Проверяем, что heartbeat от нужного процесса
        if heartbeat.get('pid') != pid:
            return False
        
        # Проверяем, что heartbeat свежий (не старше 10 секунд)
        timestamp = heartbeat.get('timestamp', 0)
        if time.time() - timestamp > 10:
            return False
        
        return True
    
    def monitor_loop(self):
        """Основной цикл мониторинга"""
        last_heartbeat_check = time.time()
        
        while self.running:
            try:
                # Обновляем свой heartbeat
                self._update_heartbeat()
                
                # Проверяем процессы каждые 2 секунды
                current_time = time.time()
                if current_time - last_heartbeat_check >= 2:
                    last_heartbeat_check = current_time
                    
                    # Проверяем главный процесс
                    if not self.is_process_running(self.main_pid):
                        print(f"Главный процесс {self.main_pid} не найден!")
                        self.cleanup_and_exit()
                        break
                    
                    # Проверяем мониторинг процесс (если не мы)
                    if self.monitor_pid != os.getpid():
                        if not self.is_process_running(self.monitor_pid):
                            print(f"Процесс мониторинга {self.monitor_pid} не найден!")
                            self.cleanup_and_exit()
                            break
                        
                        # Проверяем heartbeat мониторинг процесса
                        if not self.check_heartbeat(self.monitor_pid):
                            print(f"Heartbeat процесса мониторинга {self.monitor_pid} не обновляется!")
                            self.cleanup_and_exit()
                            break
                    
                    # Проверяем активную аренду
                    try:
                        rental_info = self.api_client.get_active_rental()
                        if not rental_info.get('hasActiveRental'):
                            print("Аренда завершена!")
                            self.cleanup_and_exit()
                            break
                    except Exception as e:
                        print(f"Ошибка при проверке аренды: {e}")
                        # Продолжаем мониторинг даже при ошибке API
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Ошибка в цикле мониторинга: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(2)
    
    def cleanup_and_exit(self):
        """Очищает ресурсы и завершает аренду"""
        print("Очистка ресурсов и завершение аренды...")
        try:
            # Закрываем Steam процессы
            try:
                steam_path = self.config.get_setting('steam_path', '')
                if steam_path:
                    steam_manager = SteamManager(steam_path)
                    steam_manager.close_steam()
            except Exception as e:
                print(f"Ошибка при закрытии Steam: {e}")
            
            # Завершаем аренду через API
            try:
                print(f"Завершение аренды через API: session_id={self.session_id}")
                result = self.api_client.end_rental(self.session_id)
                print(f"Результат завершения аренды: {result}")
            except Exception as e:
                print(f"Ошибка при завершении аренды через API: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"Ошибка при очистке: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Удаляем файлы
            try:
                if self.pid_file.exists():
                    self.pid_file.unlink()
                # Не удаляем heartbeat_file - он может использоваться другим процессом
            except Exception as e:
                print(f"Ошибка при удалении файлов: {e}")
            
            self.running = False
            print("Процесс мониторинга завершен")
            sys.exit(0)

def start_monitor_process(main_pid: int, monitor_pid: int, session_id: int, pc_key: str):
    """Запускает процесс мониторинга"""
    monitor = ProcessMonitor(main_pid, monitor_pid, session_id, pc_key)
    monitor.monitor_loop()

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python process_monitor.py <main_pid> <monitor_pid> <session_id> <pc_key>")
        sys.exit(1)
    
    main_pid = int(sys.argv[1])
    monitor_pid = int(sys.argv[2])
    session_id = int(sys.argv[3])
    pc_key = sys.argv[4]
    
    start_monitor_process(main_pid, monitor_pid, session_id, pc_key)

