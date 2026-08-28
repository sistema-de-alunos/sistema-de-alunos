"""Botões padronizados usados nas telas do sistema."""

from core.qt_core import QPushButton, Qt
from core.theme import Cores, Fontes


class BotaoPrimario(QPushButton):
    """Botão de destaque (ação principal da tela), em azul."""

    def __init__(self, texto: str, parent=None):
        super().__init__(texto, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Cores.AZUL_PRIMARIO};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 20px;
                font-size: {Fontes.TAMANHO_TEXTO}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Cores.AZUL_ESCURO};
            }}
            QPushButton:pressed {{
                background-color: {Cores.AZUL_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Cores.DESABILITADO_FUNDO};
                color: {Cores.DESABILITADO_TEXTO};
            }}
            """
        )


class BotaoSecundario(QPushButton):
    """Botão neutro, usado para ações como 'Anterior'."""

    def __init__(self, texto: str, parent=None):
        super().__init__(texto, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Cores.SUPERFICIE};
                color: {Cores.TEXTO_PRIMARIO};
                border: 1px solid {Cores.BORDA};
                border-radius: 10px;
                padding: 0 20px;
                font-size: {Fontes.TAMANHO_TEXTO}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Cores.FUNDO};
            }}
            QPushButton:disabled {{
                color: {Cores.DESABILITADO_TEXTO};
                border-color: {Cores.DESABILITADO_FUNDO};
            }}
            """
        )
