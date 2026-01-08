"""
Главный файл приложения Rental Games Desktop
"""
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from config import Config
from api_client import APIClient
from ui.key_input_dialog import KeyInputDialog
from ui.main_window import MainWindow

def main():
    """Главная функция приложения"""
    app = QApplication(sys.argv)
    app.setApplicationName("Rental Games Desktop")
    
    config = Config()
    api_client = APIClient()
    
    # Проверяем наличие ключа
    pc_key = config.load_key()
    
    if not pc_key:
        # Показываем диалог ввода ключа
        dialog = KeyInputDialog()
        if dialog.exec_() == KeyInputDialog.Accepted and dialog.key:
            pc_key = dialog.key
            # Сохраняем ключ
            if config.save_key(pc_key):
                api_client.set_key(pc_key)
            else:
                QMessageBox.critical(
                    None,
                    "Ошибка",
                    "Не удалось сохранить ключ. Попробуйте снова."
                )
                sys.exit(1)
        else:
            sys.exit(0)
    else:
        # Проверяем валидность ключа через API
        api_client.set_key(pc_key)
        try:
            # Пробуем получить активную аренду для проверки ключа
            api_client.get_active_rental()
        except Exception as e:
            # Если ключ невалидный, запрашиваем новый
            QMessageBox.warning(
                None,
                "Неверный ключ",
                "Сохраненный ключ недействителен. Пожалуйста, введите новый ключ."
            )
            config.delete_key()
            
            dialog = KeyInputDialog()
            if dialog.exec_() == KeyInputDialog.Accepted and dialog.key:
                pc_key = dialog.key
                if config.save_key(pc_key):
                    api_client.set_key(pc_key)
                else:
                    QMessageBox.critical(
                        None,
                        "Ошибка",
                        "Не удалось сохранить ключ. Попробуйте снова."
                    )
                    sys.exit(1)
            else:
                sys.exit(0)
    
    # Создаем и показываем главное окно
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

