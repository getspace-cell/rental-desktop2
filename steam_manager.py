"""
Модуль для управления Steam процессами
Блокирует доступ к Steam UI и управляет процессами
"""
import os
import time
import subprocess
import psutil
try:
    import win32gui
    import win32con
    import win32process
except ImportError:
    print("Предупреждение: pywin32 не установлен. Некоторые функции могут не работать.")
    win32gui = None
    win32con = None
    win32process = None
from typing import Optional, List
import pyautogui

class SteamManager:
    """Класс для управления Steam"""
    
    def __init__(self, steam_path: str):
        self.steam_path = steam_path
        self.steam_process: Optional[psutil.Process] = None
        self.game_process: Optional[psutil.Process] = None
        self.steam_windows: List[int] = []
    
    def is_steam_running(self) -> bool:
        """Проверяет, запущен ли Steam"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'steam' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    
    def start_steam(self):
        """Запускает Steam"""
        if self.is_steam_running():
            print("Steam уже запущен")
            return
        
        if not os.path.exists(self.steam_path):
            raise FileNotFoundError(f"Steam не найден по пути: {self.steam_path}")
        
        subprocess.Popen([self.steam_path], shell=True)
        time.sleep(5)  # Ждем запуска Steam
    
    def login_to_steam(self, username: str, password: str, two_factor_code: str):
        """Автоматически входит в Steam"""
        # Если Steam уже залогинен, выходим
        if self.is_steam_running():
            self.logout_from_steam()
            time.sleep(3)
        
        # Запускаем Steam
        subprocess.Popen([self.steam_path], shell=True)
        time.sleep(5)  # Ждем запуска Steam
        
        # Ищем окно Steam
        steam_window = None
        for _ in range(10):  # Пытаемся найти окно в течение 10 секунд
            steam_window = self._find_steam_window()
            if steam_window:
                break
            time.sleep(1)
        
        if not steam_window:
            raise Exception("Не удалось найти окно Steam")
        
        # Активируем окно Steam
        if win32gui and win32con:
            try:
                win32gui.SetForegroundWindow(steam_window)
                win32gui.ShowWindow(steam_window, win32con.SW_RESTORE)
                time.sleep(1)
            except:
                pass
        
        # Вводим логин
        time.sleep(1)
        pyautogui.write(username, interval=0.05)
        time.sleep(0.5)
        pyautogui.press('tab')
        time.sleep(0.5)
        
        # Вводим пароль
        pyautogui.write(password, interval=0.05)
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(3)
        
        # Вводим код 2FA если требуется
        if two_factor_code:
            time.sleep(2)
            # Очищаем поле ввода (на случай если там что-то есть)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.write(two_factor_code, interval=0.1)
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(5)  # Ждем завершения входа
    
    def launch_game(self, game_id: int):
        """Запускает игру через Steam"""
        # Запускаем игру через Steam
        # Используем правильный формат параметра
        subprocess.Popen([
            self.steam_path,
            f"-applaunch",
            str(game_id)
        ], shell=True)
        
        time.sleep(5)
    
    def _find_steam_window(self) -> Optional[int]:
        """Находит окно Steam"""
        if not win32gui:
            return None
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if 'steam' in window_title.lower():
                    windows.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        return windows[0] if windows else None
    
    def block_steam_ui(self):
        """Блокирует доступ к Steam UI, скрывая окна"""
        if not win32gui or not win32con:
            print("Предупреждение: pywin32 не установлен, блокировка UI недоступна")
            return
        
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                
                # Ищем окна Steam
                if 'steam' in window_title.lower() or 'steam' in class_name.lower():
                    windows.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(enum_callback, windows)
        
        for hwnd in windows:
            try:
                # Минимизируем окно
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                # Скрываем окно
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                self.steam_windows.append(hwnd)
            except Exception as e:
                print(f"Ошибка при скрытии окна Steam: {e}")
    
    def unblock_steam_ui(self):
        """Разблокирует доступ к Steam UI"""
        if not win32gui or not win32con:
            return
        
        for hwnd in self.steam_windows:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            except Exception as e:
                print(f"Ошибка при показе окна Steam: {e}")
        
        self.steam_windows.clear()
    
    def logout_from_steam(self):
        """Выходит из Steam аккаунта"""
        # Закрываем Steam полностью
        self.close_steam()
    
    def close_steam(self):
        """Закрывает все процессы Steam"""
        # Сначала разблокируем UI
        self.unblock_steam_ui()
        
        # Закрываем все процессы Steam
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'steam' in proc.info['name'].lower():
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Ждем завершения процессов
        time.sleep(2)
        
        # Принудительно закрываем, если не закрылись
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'steam' in proc.info['name'].lower():
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    def find_game_process(self, game_name: str) -> Optional[psutil.Process]:
        """Находит процесс игры"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if game_name.lower() in proc_name or proc_name in game_name.lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def is_game_running(self, game_name: str) -> bool:
        """Проверяет, запущена ли игра"""
        return self.find_game_process(game_name) is not None

