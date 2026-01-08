"""
Диалог для ввода ключа ПК
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

class KeyInputDialog(QDialog):
    """Диалог для ввода ключа ПК клуба"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ввод ключа ПК")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        
        self.key = None
        self.setup_ui()
    
    def setup_ui(self):
        """Настраивает интерфейс"""
        layout = QVBoxLayout()
        
        # Метка
        label = QLabel("Введите ключ ПК клуба:")
        layout.addWidget(label)
        
        # Поле ввода
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Введите ключ...")
        self.key_input.returnPressed.connect(self.accept_key)
        layout.addWidget(self.key_input)
        
        # Кнопки
        button_layout = QVBoxLayout()
        
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept_key)
        button_layout.addWidget(btn_ok)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def accept_key(self):
        """Принимает ключ"""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите ключ")
            return
        
        self.key = key
        self.accept()

