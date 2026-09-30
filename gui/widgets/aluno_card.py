"""Item visual da lista de alunos: o card de cada aluno cadastrado."""

from core.qt_core import (
    QByteArray,
    QFrame,
    QHBoxLayout,
    QIcon,
    QLabel,
    QPainter,
    QPainterPath,
    QPixmap,
    QPushButton,
    QRectF,
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


# Lápis no mesmo traço fino da lixeira (editar a foto de perfil).
_SVG_LAPIS = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 20h9"></path>
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
</svg>
"""


def _icone_svg(svg_modelo: str, cor: str, tamanho: int = 18) -> QIcon:
    """Renderiza um dos ícones SVG acima na cor pedida, como QIcon."""
    svg = svg_modelo.format(cor=cor)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(tamanho, tamanho)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


# Ajuste da foto de perfil: (zoom, x, y). zoom 1 = a foto cobre o círculo
# justo; x/y = ponto da foto (fração 0-1 da largura/altura) que fica no
# centro do círculo. Independe do tamanho, então vale igual no card (52px) e
# na janela de ajuste.
AJUSTE_PADRAO = (1.0, 0.5, 0.5)


def ler_ajuste(texto) -> tuple:
    """"zoom,x,y" salvo no banco -> tupla; padrão se vazio ou inválido."""
    try:
        zoom, x, y = (float(v) for v in texto.split(","))
        return (max(zoom, 1.0), x, y)
    except (AttributeError, ValueError):
        return AJUSTE_PADRAO


def geometria_foto(largura: int, altura: int, tamanho: int, ajuste: tuple) -> tuple:
    """Retângulo (x, y, largura, altura) onde desenhar a foto num quadrado de
    `tamanho` px, já com x/y limitados para a foto nunca deixar o círculo
    com buraco."""
    zoom, cx, cy = ajuste
    escala = max(tamanho / largura, tamanho / altura) * zoom
    lw, lh = largura * escala, altura * escala
    meio_x, meio_y = tamanho / 2 / lw, tamanho / 2 / lh
    cx = min(max(cx, meio_x), 1 - meio_x)
    cy = min(max(cy, meio_y), 1 - meio_y)
    return (tamanho / 2 - cx * lw, tamanho / 2 - cy * lh, lw, lh)


def recortar_circulo(original: QPixmap, tamanho: int, ajuste: tuple = AJUSTE_PADRAO) -> QPixmap:
    """A foto posicionada por `ajuste`, recortada num círculo de `tamanho` px."""
    x, y, lw, lh = geometria_foto(original.width(), original.height(), tamanho, ajuste)
    resultado = QPixmap(tamanho, tamanho)
    resultado.fill(Qt.transparent)
    painter = QPainter(resultado)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    recorte = QPainterPath()
    recorte.addEllipse(0, 0, tamanho, tamanho)
    painter.setClipPath(recorte)
    painter.drawPixmap(QRectF(x, y, lw, lh), original, QRectF(original.rect()))
    painter.end()
    return resultado


def _iniciais(nome_completo: str) -> str:
    partes = [p for p in nome_completo.strip().split(" ") if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[-1][0]).upper()


class _BotaoIcone(QPushButton):
    """Ícone de ação do card: SVG minimalista, com leve troca de cor no hover."""

    def __init__(self, svg_modelo: str, cor_hover: str, fundo_hover: str, dica: str, parent=None):
        super().__init__(parent)
        self._icone_normal = _icone_svg(svg_modelo, Cores.TEXTO_SECUNDARIO)
        self._icone_hover = _icone_svg(svg_modelo, cor_hover)
        self.setIcon(self._icone_normal)
        self.setIconSize(QSize(18, 18))
        self.setToolTip(dica)
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
                background-color: {fundo_hover};
            }}
            QPushButton:pressed {{
                background-color: {fundo_hover};
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
    editar_foto_solicitado = Signal(int)

    def __init__(
        self, aluno_id: int, nome_completo: str, foto_perfil=None, foto_perfil_ajuste=None, parent=None
    ):
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
        foto = QPixmap(foto_perfil) if foto_perfil else QPixmap()
        if not foto.isNull():
            avatar.setPixmap(recortar_circulo(foto, TAMANHO_AVATAR, ler_ajuste(foto_perfil_ajuste)))
        layout.addWidget(avatar, alignment=Qt.AlignVCenter)

        nome = QLabel(nome_completo)
        nome.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: 15px; font-weight: 600;"
        )
        layout.addWidget(nome, stretch=1, alignment=Qt.AlignVCenter)

        botao_editar = _BotaoIcone(_SVG_LAPIS, Cores.AZUL_PRIMARIO, Cores.FUNDO, "Editar foto de perfil")
        botao_editar.clicked.connect(lambda: self.editar_foto_solicitado.emit(self._aluno_id))
        layout.addWidget(botao_editar, alignment=Qt.AlignVCenter)

        botao_excluir = _BotaoIcone(_SVG_LIXEIRA, Cores.ERRO, Cores.ERRO_FUNDO, "Excluir aluno")
        botao_excluir.clicked.connect(lambda: self.excluir_solicitado.emit(self._aluno_id))
        layout.addWidget(botao_excluir, alignment=Qt.AlignVCenter)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicado.emit(self._aluno_id)
