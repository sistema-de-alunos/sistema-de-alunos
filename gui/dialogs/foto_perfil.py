from typing import Optional

from core.qt_core import (
    QColor,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPainter,
    QPainterPath,
    QPixmap,
    QRectF,
    QSlider,
    Qt,
    QVBoxLayout,
    QWidget,
    Signal,
)
from core.theme import Cores
from gui.widgets.aluno_card import AJUSTE_PADRAO, geometria_foto, ler_ajuste
from gui.widgets.botao_principal import BotaoPrimario, BotaoSecundario

_TAMANHO_AREA = 260
_ZOOM_MAXIMO = 4.0
_FILTRO_IMAGENS = "Imagens (*.png *.jpg *.jpeg *.webp)"


class _AreaAjuste(QWidget):
    zoom_alterado = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(_TAMANHO_AREA, _TAMANHO_AREA)
        self.setCursor(Qt.OpenHandCursor)
        self._pixmap: Optional[QPixmap] = None
        self._ajuste = AJUSTE_PADRAO
        self._ultimo_ponto = None

    @property
    def ajuste(self) -> tuple:
        return self._ajuste

    def definir(self, pixmap: Optional[QPixmap], ajuste: tuple) -> None:
        self._pixmap = pixmap
        self._fixar(ajuste)

    def definir_zoom(self, zoom: float) -> None:
        _, cx, cy = self._ajuste
        self._fixar((zoom, cx, cy))

    def _fixar(self, ajuste: tuple) -> None:
        if self._pixmap is not None:
            zoom = min(max(ajuste[0], 1.0), _ZOOM_MAXIMO)
            x, y, lw, lh = geometria_foto(
                self._pixmap.width(), self._pixmap.height(), _TAMANHO_AREA, (zoom, ajuste[1], ajuste[2])
            )
            ajuste = (zoom, (_TAMANHO_AREA / 2 - x) / lw, (_TAMANHO_AREA / 2 - y) / lh)
        self._ajuste = ajuste
        self.update()

    def paintEvent(self, evento) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.fillRect(self.rect(), QColor(Cores.FUNDO))
        if self._pixmap is None:
            painter.setPen(QColor(Cores.TEXTO_SECUNDARIO))
            painter.drawText(self.rect(), Qt.AlignCenter, "Sem foto")
            return
        x, y, lw, lh = geometria_foto(
            self._pixmap.width(), self._pixmap.height(), _TAMANHO_AREA, self._ajuste
        )
        painter.drawPixmap(QRectF(x, y, lw, lh), self._pixmap, QRectF(self._pixmap.rect()))
        fora = QPainterPath()
        fora.addRect(QRectF(self.rect()))
        circulo = QPainterPath()
        circulo.addEllipse(QRectF(self.rect()))
        painter.fillPath(fora.subtracted(circulo), QColor(0, 0, 0, 140))

    def mousePressEvent(self, evento) -> None:
        self._ultimo_ponto = evento.position()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, evento) -> None:
        if self._ultimo_ponto is None or self._pixmap is None:
            return
        delta = evento.position() - self._ultimo_ponto
        self._ultimo_ponto = evento.position()
        zoom, cx, cy = self._ajuste
        _, _, lw, lh = geometria_foto(
            self._pixmap.width(), self._pixmap.height(), _TAMANHO_AREA, self._ajuste
        )
        self._fixar((zoom, cx - delta.x() / lw, cy - delta.y() / lh))

    def mouseReleaseEvent(self, evento) -> None:
        self._ultimo_ponto = None
        self.setCursor(Qt.OpenHandCursor)

    def wheelEvent(self, evento) -> None:
        if self._pixmap is None:
            return
        passo = 1.1 if evento.angleDelta().y() > 0 else 1 / 1.1
        self.definir_zoom(self._ajuste[0] * passo)
        self.zoom_alterado.emit(self._ajuste[0])


class FotoPerfilDialog(QDialog):
    def __init__(self, caminho: Optional[str], ajuste_texto: Optional[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Foto de perfil")
        self.setStyleSheet(f"QDialog {{ background-color: {Cores.SUPERFICIE}; }}")
        self._caminho = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        dica = QLabel("Arraste a foto para posicionar e use a roda do mouse ou a barra para o zoom.")
        dica.setWordWrap(True)
        dica.setStyleSheet(f"color: {Cores.TEXTO_SECUNDARIO}; font-size: 13px;")
        layout.addWidget(dica)

        self._area = _AreaAjuste()
        layout.addWidget(self._area, alignment=Qt.AlignHCenter)

        self._zoom = QSlider(Qt.Horizontal)
        self._zoom.setRange(100, int(_ZOOM_MAXIMO * 100))
        self._zoom.valueChanged.connect(lambda v: self._area.definir_zoom(v / 100))
        self._area.zoom_alterado.connect(self._sincronizar_barra)
        layout.addWidget(self._zoom)

        linha_foto = QHBoxLayout()
        botao_trocar = BotaoSecundario("Escolher imagem")
        botao_trocar.clicked.connect(self._escolher_imagem)
        linha_foto.addWidget(botao_trocar)
        self._botao_remover = BotaoSecundario("Remover foto")
        self._botao_remover.setStyleSheet(
            self._botao_remover.styleSheet() + f"QPushButton {{ color: {Cores.ERRO}; }}"
        )
        self._botao_remover.clicked.connect(self._remover)
        linha_foto.addWidget(self._botao_remover)
        layout.addLayout(linha_foto)

        linha_acoes = QHBoxLayout()
        botao_cancelar = BotaoSecundario("Cancelar")
        botao_cancelar.clicked.connect(self.reject)
        linha_acoes.addWidget(botao_cancelar)
        botao_salvar = BotaoPrimario("Salvar")
        botao_salvar.clicked.connect(self.accept)
        linha_acoes.addWidget(botao_salvar)
        layout.addLayout(linha_acoes)

        self._carregar(caminho, ler_ajuste(ajuste_texto))

    @property
    def caminho(self) -> Optional[str]:
        return self._caminho

    @property
    def ajuste_texto(self) -> Optional[str]:
        if self._caminho is None:
            return None
        return ",".join(f"{v:.4f}" for v in self._area.ajuste)

    def _carregar(self, caminho: Optional[str], ajuste: tuple) -> None:
        pixmap = QPixmap(caminho) if caminho else QPixmap()
        if pixmap.isNull():
            caminho, pixmap = None, None
        self._caminho = caminho
        self._area.definir(pixmap, ajuste)
        self._sincronizar_barra(self._area.ajuste[0])
        self._zoom.setEnabled(pixmap is not None)
        self._botao_remover.setEnabled(pixmap is not None)

    def _sincronizar_barra(self, zoom: float) -> None:
        self._zoom.blockSignals(True)
        self._zoom.setValue(int(round(zoom * 100)))
        self._zoom.blockSignals(False)

    def _escolher_imagem(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar foto de perfil", "", _FILTRO_IMAGENS)
        if not caminho:
            return
        if QPixmap(caminho).isNull():
            QMessageBox.warning(self, "Foto de perfil", "Não foi possível abrir essa imagem. Escolha outro arquivo.")
            return
        self._carregar(caminho, AJUSTE_PADRAO)

    def _remover(self) -> None:
        self._carregar(None, AJUSTE_PADRAO)
