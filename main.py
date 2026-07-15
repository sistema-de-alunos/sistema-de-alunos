import sys
import os
from core.qt_core import *
from ui_main import *


print("Diretório atual:", os.getcwd())
print("Arquivo:", __file__)
print("sys.path:")
for p in sys.path:
    print(" ", p)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = UI_MainWindow()
        self.ui.setup_ui(self)

        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())