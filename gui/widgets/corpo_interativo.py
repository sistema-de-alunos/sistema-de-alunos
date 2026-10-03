from pathlib import Path
from typing import Dict, Optional

from core.qt_core import (
    QPainter,
    QPixmap,
    QRectF,
    QSize,
    QSizePolicy,
    Qt,
    QWidget,
    Signal,
)

_PASTA_ASSETS = Path(__file__).resolve().parent.parent.parent / "assets" / "corpos"

CAMINHO_IMAGEM_MASCULINO = str(_PASTA_ASSETS / "corpohomem.png")
PASTA_MASCARAS_MASCULINO = _PASTA_ASSETS / "mascaras_masculino"

CAMINHO_IMAGEM_FEMININO = str(_PASTA_ASSETS / "corpomulher.png")
PASTA_MASCARAS_FEMININO = _PASTA_ASSETS / "mascaras_feminino"

IDS_REGIOES_MASCULINO = (
    "shoulder",
    "chest",
    "waist",
    "abdomen",
    "hip",
    "left_arm",
    "right_arm",
    "right_forearm",
    "left_forearm",
    "left_thigh",
    "right_thigh",
    "left_calf",
    "right_calf",
)
IDS_REGIOES_FEMININO = IDS_REGIOES_MASCULINO

_OPACIDADE_SELECIONADO = 0.62
_OPACIDADE_HOVER = 0.30
_ALFA_MINIMO_CLIQUE = 25


class CorpoInterativoWidget(QWidget):
    regiao_clicada = Signal(str)

    def __init__(
        self,
        caminho_imagem: str,
        pasta_mascaras: Path,
        ids_regioes,
        parent=None,
    ):
        super().__init__(parent)
        self._pixmap = QPixmap(caminho_imagem)
        self._selecionadas: set = set()
        self._regiao_hover: Optional[str] = None

        self._mascaras: Dict[str, QPixmap] = {}
        self._mascaras_imagem = {}
        for id_regiao in ids_regioes:
            caminho = pasta_mascaras / f"{id_regiao}.png"
            pixmap = QPixmap(str(caminho))
            if pixmap.isNull():
                continue
            self._mascaras[id_regiao] = pixmap
            self._mascaras_imagem[id_regiao] = pixmap.toImage()

        self.setMinimumSize(160, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def definir_regioes_selecionadas(self, ids) -> None:
        novo_conjunto = set(ids)
        if novo_conjunto == self._selecionadas:
            return
        self._selecionadas = novo_conjunto
        self.update()

    def sizeHint(self) -> QSize:
        if self._pixmap.isNull():
            return super().sizeHint()
        return QSize(self._pixmap.width() // 4, self._pixmap.height() // 4)


    def _retangulo_imagem(self) -> QRectF:
        if self._pixmap.isNull():
            return QRectF()
        tamanho_ajustado = self._pixmap.size().scaled(self.size(), Qt.KeepAspectRatio)
        x = (self.width() - tamanho_ajustado.width()) / 2
        y = (self.height() - tamanho_ajustado.height()) / 2
        return QRectF(x, y, tamanho_ajustado.width(), tamanho_ajustado.height())

    def _regiao_no_ponto(self, ponto_widget) -> Optional[str]:
        retangulo = self._retangulo_imagem()
        if retangulo.isEmpty() or not retangulo.contains(ponto_widget):
            return None

        img_x = int((ponto_widget.x() - retangulo.x()) / retangulo.width() * self._pixmap.width())
        img_y = int((ponto_widget.y() - retangulo.y()) / retangulo.height() * self._pixmap.height())

        melhor_id, melhor_alfa = None, _ALFA_MINIMO_CLIQUE
        for id_regiao, imagem in self._mascaras_imagem.items():
            if not (0 <= img_x < imagem.width() and 0 <= img_y < imagem.height()):
                continue
            alfa = imagem.pixelColor(img_x, img_y).alpha()
            if alfa > melhor_alfa:
                melhor_alfa = alfa
                melhor_id = id_regiao
        return melhor_id


    def paintEvent(self, evento) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        retangulo = self._retangulo_imagem()
        if not self._pixmap.isNull():
            painter.drawPixmap(retangulo, self._pixmap, QRectF(self._pixmap.rect()))

        if self._regiao_hover and self._regiao_hover not in self._selecionadas:
            self._pintar_mascara(painter, self._regiao_hover, retangulo, _OPACIDADE_HOVER)

        for id_regiao in self._selecionadas:
            self._pintar_mascara(painter, id_regiao, retangulo, _OPACIDADE_SELECIONADO)

        painter.end()

    def _pintar_mascara(self, painter, id_regiao: str, retangulo: QRectF, opacidade: float) -> None:
        pixmap = self._mascaras.get(id_regiao)
        if pixmap is None or pixmap.isNull():
            return
        painter.setOpacity(opacidade)
        painter.drawPixmap(retangulo, pixmap, QRectF(pixmap.rect()))
        painter.setOpacity(1.0)


    def mouseMoveEvent(self, evento) -> None:
        nova_regiao = self._regiao_no_ponto(evento.position())
        if nova_regiao != self._regiao_hover:
            self._regiao_hover = nova_regiao
            self.setCursor(Qt.PointingHandCursor if nova_regiao else Qt.ArrowCursor)
            self.update()

    def leaveEvent(self, evento) -> None:
        if self._regiao_hover is not None:
            self._regiao_hover = None
            self.setCursor(Qt.ArrowCursor)
            self.update()

    def mousePressEvent(self, evento) -> None:
        regiao = self._regiao_no_ponto(evento.position())
        if regiao:
            self.regiao_clicada.emit(regiao)

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self.update()
