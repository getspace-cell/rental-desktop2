"""
Диалог настроек приложения
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt

class SettingsDialog(QDialog):
    """Диалог настроек"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Настройки")
        self.setFixedSize(600, 400)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Настраивает интерфейс"""
        layout = QVBoxLayout()
        
        # Steam
        steam_layout = QHBoxLayout()
        steam_label = QLabel("Путь к Steam:")
        steam_layout.addWidget(steam_label)
        
        self.steam_input = QLineEdit()
        steam_layout.addWidget(self.steam_input)
        
        steam_btn = QPushButton("Обзор...")
        steam_btn.clicked.connect(lambda: self.browse_file(self.steam_input, "Steam.exe"))
        steam_layout.addWidget(steam_btn)
        
        layout.addLayout(steam_layout)
        
        # Epic Games
        epic_layout = QHBoxLayout()
        epic_label = QLabel("Путь к Epic Games:")
        epic_layout.addWidget(epic_label)
        
        self.epic_input = QLineEdit()
        epic_layout.addWidget(self.epic_input)
        
        epic_btn = QPushButton("Обзор...")
        epic_btn.clicked.connect(lambda: self.browse_file(self.epic_input, "EpicGamesLauncher.exe"))
        epic_layout.addWidget(epic_btn)
        
        layout.addLayout(epic_layout)
        
        # Riot Games
        riot_layout = QHBoxLayout()
        riot_label = QLabel("Путь к Riot Games:")
        riot_layout.addWidget(riot_label)
        
        self.riot_input = QLineEdit()
        riot_layout.addWidget(self.riot_input)
        
        riot_btn = QPushButton("Обзор...")
        riot_btn.clicked.connect(lambda: self.browse_file(self.riot_input, "RiotClientServices.exe"))
        riot_layout.addWidget(riot_btn)
        
        layout.addLayout(riot_layout)
        
        # Battle.net
        battlenet_layout = QHBoxLayout()
        battlenet_label = QLabel("Путь к Battle.net:")
        battlenet_layout.addWidget(battlenet_label)
        
        self.battlenet_input = QLineEdit()
        battlenet_layout.addWidget(self.battlenet_input)
        
        battlenet_btn = QPushButton("Обзор...")
        battlenet_btn.clicked.connect(lambda: self.browse_file(self.battlenet_input, "Battle.net.exe"))
        battlenet_layout.addWidget(battlenet_btn)
        
        layout.addLayout(battlenet_layout)
        
        # VK Play
        vkplay_layout = QHBoxLayout()
        vkplay_label = QLabel("Путь к VK Play:")
        vkplay_layout.addWidget(vkplay_label)
        
        self.vkplay_input = QLineEdit()
        vkplay_layout.addWidget(self.vkplay_input)
        
        vkplay_btn = QPushButton("Обзор...")
        vkplay_btn.clicked.connect(lambda: self.browse_file(self.vkplay_input, "VKPlay.exe"))
        vkplay_layout.addWidget(vkplay_btn)
        
        layout.addLayout(vkplay_layout)
        
        # EA
        ea_layout = QHBoxLayout()
        ea_label = QLabel("Путь к EA App:")
        ea_layout.addWidget(ea_label)
        
        self.ea_input = QLineEdit()
        ea_layout.addWidget(self.ea_input)
        
        ea_btn = QPushButton("Обзор...")
        ea_btn.clicked.connect(lambda: self.browse_file(self.ea_input, "EADesktop.exe"))
        ea_layout.addWidget(ea_btn)
        
        layout.addLayout(ea_layout)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_settings)
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def browse_file(self, line_edit: QLineEdit, default_name: str):
        """Открывает диалог выбора файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Выберите {default_name}",
            "",
            f"Executable Files (*.exe);;All Files (*)"
        )
        
        if file_path:
            line_edit.setText(file_path)
    
    def load_settings(self):
        """Загружает настройки"""
        self.steam_input.setText(self.config.get_setting('steam_path', ''))
        self.epic_input.setText(self.config.get_setting('epic_path', ''))
        self.riot_input.setText(self.config.get_setting('riot_path', ''))
        self.battlenet_input.setText(self.config.get_setting('battlenet_path', ''))
        self.vkplay_input.setText(self.config.get_setting('vkplay_path', ''))
        self.ea_input.setText(self.config.get_setting('ea_path', ''))
    
    def save_settings(self):
        """Сохраняет настройки"""
        self.config.set_setting('steam_path', self.steam_input.text())
        self.config.set_setting('epic_path', self.epic_input.text())
        self.config.set_setting('riot_path', self.riot_input.text())
        self.config.set_setting('battlenet_path', self.battlenet_input.text())
        self.config.set_setting('vkplay_path', self.vkplay_input.text())
        self.config.set_setting('ea_path', self.ea_input.text())
        
        QMessageBox.information(self, "Успех", "Настройки сохранены")
        self.accept()

