"""Item visual da lista de alunos: o card de cada aluno cadastrado."""

from core.qt_core import (
    QByteArray,
    QFrame,
    QHBoxLayout,
    QIcon,
    QLabel,
    QPainter,
    QPixmap,
    QPushButton,
    Qt,
    QSize,
    QSvgRenderer,
    Signal,
)
from core.theme import Cores, Fontes

TAMANHO_AVATAR = 52

# Ícone de lixeira minimalista (traço fino, sem preenchimento), desenhado em
# SVG para não depender da fonte de emoji do sistema — que renderiza um
# desenho colorido e "pesado" em vez de um ícone de interface discreto.
_SVG_LIXEIRA = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path>
    <line x1="10" y1="11" x2="10" y2="17"></line>
    <line x1="14" y1="11" x2="14" y2="17"></line>
</svg>
"""


def _icone_lixeira(cor: str, tamanho: int = 18) -> QIcon:
    """Renderiza o ícone de lixeira acima na cor pedida, como QIcon."""
    svg = _SVG_LIXEIRA.format(cor=cor)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(tamanho, tamanho)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def _iniciais(nome_completo: str) -> str:
    partes = [p for p in nome_completo.strip().split(" ") if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[-1][0]).upper()


class _BotaoExcluir(QPushButton):
    """Ícone de excluir do card: SVG minimalista, com leve troca de cor no hover."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icone_normal = _icone_lixeira(Cores.TEXTO_SECUNDARIO)
        self._icone_hover = _icone_lixeira(Cores.ERRO)
        self.setIcon(self._icone_normal)
        self.setIconSize(QSize(18, 18))
        self.setToolTip("Excluir aluno")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(36, 36)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {Cores.ERRO_FUNDO};
            }}
            QPushButton:pressed {{
                background-color: {Cores.ERRO_FUNDO};
            }}
            """
        )

    def enterEvent(self, event):
        self.setIcon(self._icone_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._icone_normal)
        super().leaveEvent(event)


class AlunoCard(QFrame):
    """Um item clicável da lista, representando um aluno cadastrado."""

    clicado = Signal(int)
    excluir_solicitado = Signal(int)

    def __init__(self, aluno_id: int, nome_completo: str, parent=None):
        super().__init__(parent)
        self._aluno_id = aluno_id
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(76)
        self.setStyleSheet(
            f"""
            AlunoCard {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.BORDA};
                border-radius: 12px;
            }}
            AlunoCard:hover {{
                border: 1px solid {Cores.AZUL_PRIMARIO};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        avatar = QLabel(_iniciais(nome_completo))
        avatar.setFixedSize(TAMANHO_AVATAR, TAMANHO_AVATAR)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            f"""
            QLabel {{
                background-color: {Cores.FUNDO};
                border: none;
                color: {Cores.AZUL_ESCURO};
                border-radius: {TAMANHO_AVATAR // 2}px;
                font-weight: 700;
                font-size: 16px;
            }}
            """
        )
        layout.addWidget(avatar, alignment=Qt.AlignVCenter)

        nome = QLabel(nome_completo)
        nome.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: 15px; font-weight: 600;"
        )
        layout.addWidget(nome, stretch=1, alignment=Qt.AlignVCenter)

        botao_excluir = _BotaoExcluir()
        botao_excluir.clicked.connect(lambda: self.excluir_solicitado.emit(self._aluno_id))
        layout.addWidget(botao_excluir, alignment=Qt.AlignVCenter)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicado.emit(self._aluno_id)
