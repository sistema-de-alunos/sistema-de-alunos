import sys

from core.qt_core import QApplication, QMainWindow
from database.database import inicializar_banco
from ui_main import UI_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = UI_MainWindow()
        self.ui.setup_ui(self)
        # Maximizada nativamente pelo Qt: ocupa toda a área útil da tela do
        # usuário (se adaptando à resolução do monitor atual), mantendo a
        # barra de título e a barra de tarefas visíveis — diferente de
        # showFullScreen(), que cobriria a tela inteira sem elas. Nada de
        # coordenadas/tamanhos fixos: o Qt calcula a geometria em tempo de
        # execução a partir da tela onde a janela é aberta.
        self.showMaximized()


if __name__ == "__main__":
    inicializar_banco()

    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())
