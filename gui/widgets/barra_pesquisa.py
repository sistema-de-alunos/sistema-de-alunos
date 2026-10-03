from core.qt_core import QLineEdit, Signal
from core.theme import Cores, Fontes


class BarraPesquisa(QLineEdit):
    pesquisa_alterada = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Buscar Aluno")
        self.setFixedHeight(54)
        self.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.BORDA};
                border-radius: 12px;
                padding-left: 18px;
                font-size: 16px;
                color: {Cores.TEXTO_PRIMARIO};
            }}
            QLineEdit:focus {{
                border: 1px solid {Cores.AZUL_PRIMARIO};
            }}
            """
        )
        self.textChanged.connect(self.pesquisa_alterada.emit)
