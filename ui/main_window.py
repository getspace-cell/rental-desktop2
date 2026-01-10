"""
Главное окно приложения
"""
import sys
import threading
import time
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QListWidgetItem,
                             QMessageBox, QProgressBar, QMenuBar, QAction)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt5.QtGui import QPixmap, QIcon
from api_client import APIClient
from game_launcher import GameLauncher
from config import Config
from ui.settings_dialog import SettingsDialog

class GameMonitorWorker(QObject):
    """Воркер для мониторинга игры в отдельном потоке"""
    game_closed = pyqtSignal()
    status_updated = pyqtSignal(str)
    
    def __init__(self, game_launcher):
        super().__init__()
        self.game_launcher = game_launcher
        self.running = False
    
    def start_monitoring(self):
        """Начинает мониторинг"""
        self.running = True
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.running = False
    
    def monitor_loop(self):
        """Цикл мониторинга - выполняется в отдельном потоке"""
        while self.running:
            if not self.game_launcher.monitor_game():
                self.game_closed.emit()
                break
            time.sleep(2)

class GameMonitor(QObject):
    """Класс для управления мониторингом игры"""
    game_closed = pyqtSignal()
    
    def __init__(self, game_launcher, parent=None):
        super().__init__(parent)
        self.game_launcher = game_launcher
        self.thread = None
        self.worker = None
    
    def start_monitoring(self):
        """Начинает мониторинг в отдельном потоке"""
        self.thread = QThread()
        self.worker = GameMonitorWorker(self.game_launcher)
        self.worker.moveToThread(self.thread)
        
        # Подключаем сигналы
        self.thread.started.connect(self.worker.monitor_loop)
        self.worker.game_closed.connect(self.game_closed)
        self.worker.game_closed.connect(self.stop_monitoring)
        
        # Запускаем поток
        self.worker.start_monitoring()
        self.thread.start()
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        if self.worker:
            self.worker.stop_monitoring()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.api_client = APIClient()
        self.game_launcher = GameLauncher(self.api_client, self.config)
        self.games = []
        self.current_rental = None
        self.monitor = None
        
        # Загружаем ключ
        pc_key = self.config.load_key()
        if pc_key:
            self.api_client.set_key(pc_key)
        
        self.setup_ui()
        
        # Завершаем активную аренду перед загрузкой игр (асинхронно, чтобы не блокировать UI)
        # Используем QTimer для выполнения после инициализации UI
        QTimer.singleShot(100, self.end_active_rental_on_startup)
        
        # Таймер для обновления статуса
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # Обновляем каждые 5 секунд
    
    def setup_ui(self):
        """Настраивает интерфейс"""
        self.setWindowTitle("Rental Games Desktop")
        self.setGeometry(100, 100, 1000, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Меню
        menubar = self.menuBar()
        
        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.show_settings)
        menubar.addAction(settings_action)
        
        # Заголовок
        title = QLabel("Доступные игры")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # Список игр
        self.games_list = QListWidget()
        self.games_list.itemDoubleClicked.connect(self.on_game_double_clicked)
        main_layout.addWidget(self.games_list)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.play_button = QPushButton("Играть")
        self.play_button.clicked.connect(self.on_play_clicked)
        self.play_button.setEnabled(False)
        button_layout.addWidget(self.play_button)
        
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.clicked.connect(self.load_games)
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        
        # Статус бар
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Готов к работе")
        self.status_bar.addWidget(self.status_label)
        
        # Прогресс бар для аренды
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
    
    def end_active_rental_on_startup(self):
        """Завершает активную аренду при запуске и затем загружает игры"""
        def do_end_and_load():
            """Выполняется в отдельном потоке"""
            try:
                if not self.api_client.pc_key:
                    # Если нет ключа, сразу загружаем игры
                    QTimer.singleShot(0, self.load_games)
                    return
                
                print("Проверка активной аренды при запуске...")
                QTimer.singleShot(0, lambda: self.status_label.setText("Проверка активной аренды..."))
                
                # Получаем информацию об активной аренде
                rental_info = self.api_client.get_active_rental()
                
                if rental_info.get('hasActiveRental') and rental_info.get('rental'):
                    active_rental = rental_info['rental']
                    session_id = active_rental.get('id')
                    game_title = active_rental.get('gameTitle', 'Неизвестная игра')
                    
                    print(f"Обнаружена активная аренда: {game_title} (session_id: {session_id})")
                    QTimer.singleShot(0, lambda: self.status_label.setText(f"Завершение активной аренды: {game_title}..."))
                    
                    # Завершаем активную аренду
                    try:
                        if session_id:
                            print(f"Завершаем аренду с session_id: {session_id}")
                            self.api_client.end_rental(session_id)
                        else:
                            print("Завершаем аренду без session_id")
                            self.api_client.end_rental()
                        
                        print("Активная аренда успешно завершена при запуске")
                        QTimer.singleShot(0, lambda: self.status_label.setText("Активная аренда завершена"))
                        
                    except Exception as e:
                        print(f"Ошибка при завершении активной аренды при запуске: {e}")
                        import traceback
                        traceback.print_exc()
                        # Продолжаем работу даже если не удалось завершить аренду
                        QTimer.singleShot(0, lambda: self.status_label.setText(f"Не удалось завершить активную аренду"))
                else:
                    print("Активная аренда не найдена при запуске")
                    QTimer.singleShot(0, lambda: self.status_label.setText("Активная аренда не найдена"))
                
                # Загружаем игры после завершения проверки
                QTimer.singleShot(500, self.load_games)
                
            except Exception as e:
                print(f"Ошибка при проверке активной аренды при запуске: {e}")
                import traceback
                traceback.print_exc()
                # Продолжаем работу даже при ошибке
                QTimer.singleShot(0, lambda: self.status_label.setText("Ошибка проверки аренды"))
                # Загружаем игры даже при ошибке
                QTimer.singleShot(500, self.load_games)
        
        # Запускаем в отдельном потоке, чтобы не блокировать UI
        thread = threading.Thread(target=do_end_and_load, daemon=True)
        thread.start()
    
    def load_games(self):
        """Загружает список игр"""
        try:
            self.status_label.setText("Загрузка игр...")
            self.games = self.api_client.get_games()
            self.update_games_list()
            self.status_label.setText(f"Загружено игр: {len(self.games)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить игры: {e}")
            self.status_label.setText("Ошибка загрузки игр")
    
    def update_games_list(self):
        """Обновляет список игр"""
        self.games_list.clear()
        
        for game in self.games:
            item_text = f"{game['title']}"
            if game.get('availableAccounts', 0) > 0:
                item_text += f" (Доступно: {game['availableAccounts']})"
            else:
                item_text += " (Недоступно)"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, game)
            
            # Отключаем недоступные игры
            if game.get('availableAccounts', 0) == 0:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            
            self.games_list.addItem(item)
    
    def on_game_double_clicked(self, item: QListWidgetItem):
        """Обработчик двойного клика по игре"""
        game = item.data(Qt.UserRole)
        if game and game.get('availableAccounts', 0) > 0:
            self.launch_game(game)
    
    def on_play_clicked(self):
        """Обработчик нажатия кнопки 'Играть'"""
        current_item = self.games_list.currentItem()
        if not current_item:
            return
        
        game = current_item.data(Qt.UserRole)
        if game:
            self.launch_game(game)
    
    def launch_game(self, game: dict):
        """Запускает игру"""
        # Проверяем настройки
        steam_path = self.config.get_setting('steam_path')
        if not steam_path:
            QMessageBox.warning(
                self, 
                "Настройки", 
                "Пожалуйста, укажите путь к Steam в настройках"
            )
            self.show_settings()
            return
        
        # Проверяем активную аренду
        if self.current_rental:
            reply = QMessageBox.question(
                self,
                "Активная аренда",
                "У вас уже есть активная аренда. Завершить её и начать новую?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.end_current_rental()
            else:
                return
        
        # Запускаем игру
        try:
            self.status_label.setText(f"Запуск игры {game['title']}...")
            self.play_button.setEnabled(False)
            
            # Запускаем в отдельном потоке
            thread = threading.Thread(
                target=self._launch_game_thread,
                args=(game,),
                daemon=True
            )
            thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить игру: {e}")
            self.status_label.setText("Ошибка запуска игры")
            self.play_button.setEnabled(True)
    
    def _launch_game_thread(self, game: dict):
        """Запускает игру в отдельном потоке"""
        try:
            success = self.game_launcher.launch_game(game, duration_hours=1)
            
            if success:
                # Получаем информацию об активной аренде
                try:
                    rental_info = self.api_client.get_active_rental()
                    if rental_info.get('hasActiveRental'):
                        self.current_rental = rental_info['rental']
                        
                        # Запускаем мониторинг в отдельном Qt потоке
                        self.monitor = GameMonitor(self.game_launcher, self)
                        self.monitor.game_closed.connect(self.on_game_closed)
                        self.monitor.start_monitoring()
                        
                        # Используем QTimer для безопасного обновления UI из другого потока
                        QTimer.singleShot(0, lambda: self._update_ui_after_launch(game))
                    else:
                        QTimer.singleShot(0, lambda: self.status_label.setText("Игра запущена, но аренда не найдена"))
                except Exception as e:
                    print(f"Ошибка при получении информации об аренде: {e}")
                    QTimer.singleShot(0, lambda: self.status_label.setText(f"Игра запущена: {game['title']}"))
            else:
                QTimer.singleShot(0, lambda: self.status_label.setText("Ошибка запуска игры"))
                
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"Ошибка при запуске игры: {traceback.format_exc()}")
            QTimer.singleShot(0, lambda: self.status_label.setText(f"Ошибка: {error_msg}"))
        finally:
            QTimer.singleShot(0, lambda: self.play_button.setEnabled(True))
    
    def _update_ui_after_launch(self, game: dict):
        """Безопасно обновляет UI после запуска игры (вызывается из главного потока)"""
        self.status_label.setText(f"Игра запущена: {game['title']}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
    
    def on_game_closed(self):
        """Обработчик закрытия игры"""
        self.end_current_rental()
        QMessageBox.information(self, "Игра закрыта", "Сессия аренды завершена")
    
    def end_current_rental(self):
        """Завершает текущую аренду"""
        if self.monitor:
            self.monitor.stop_monitoring()
            self.monitor = None
        
        if self.game_launcher:
            self.game_launcher.end_session()
        
        self.current_rental = None
        self.progress_bar.setVisible(False)
        self.status_label.setText("Готов к работе")
    
    def update_status(self):
        """Обновляет статус - вызывается из главного потока"""
        if self.current_rental:
            # Обновляем информацию об аренде
            try:
                rental_info = self.api_client.get_active_rental()
                if rental_info.get('hasActiveRental'):
                    rental = rental_info['rental']
                    remaining = rental.get('remainingHours', 0)
                    self.status_label.setText(
                        f"Аренда активна: {rental['gameTitle']} "
                        f"(Осталось: {remaining:.1f} ч.)"
                    )
                    
                    # Обновляем прогресс бар
                    total_hours = rental.get('plannedDurationHours', 1)
                    if total_hours > 0:
                        progress = int((1 - remaining / total_hours) * 100)
                        self.progress_bar.setValue(progress)
                else:
                    # Аренда завершена
                    self.end_current_rental()
            except Exception as e:
                print(f"Ошибка при обновлении статуса: {e}")
    
    def show_settings(self):
        """Показывает диалог настроек"""
        dialog = SettingsDialog(self.config, self)
        dialog.exec_()
    
    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        if self.current_rental:
            reply = QMessageBox.question(
                self,
                "Активная аренда",
                "У вас есть активная аренда. Завершить сессию?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.end_current_rental()
        
        event.accept()

