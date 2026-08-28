import sys

from core.qt_core import QApplication, QMainWindow
from database.database import inicializar_banco
from ui_main import UI_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = UI_MainWindow()
        self.ui.setup_ui(self)
        self.show()


if __name__ == "__main__":
    inicializar_banco()

    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
