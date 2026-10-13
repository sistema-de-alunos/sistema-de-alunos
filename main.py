import sys
from pathlib import Path

from core.qt_core import QApplication, QIcon, QMainWindow
from core.theme import ESTILO_BARRA_ROLAGEM
from database.database import inicializar_banco
from ui_main import UI_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = UI_MainWindow()
        self.ui.setup_ui(self)
        self.showMaximized()


if __name__ == "__main__":
    inicializar_banco()

    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO_BARRA_ROLAGEM)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "logo.ico")))
    window = MainWindow()
    sys.exit(app.exec())
