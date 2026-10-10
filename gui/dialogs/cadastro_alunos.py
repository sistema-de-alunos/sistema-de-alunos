import inspect
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

from core.qt_core import (
    QApplication,
    QByteArray,
    QButtonGroup,
    QCalendarWidget,
    QColor,
    QComboBox,
    QDate,
    QEvent,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QLabel,
    QLineEdit,
    QObject,
    QPainter,
    QPalette,
    QPixmap,
    QEasingCurve,
    QPushButton,
    Qt,
    QRegularExpression,
    QRegularExpressionValidator,
    QScrollArea,
    QSize,
    QSizePolicy,
    QStackedWidget,
    QSvgRenderer,
    QTableWidget,
    QTextEdit,
    QTimer,
    QToolButton,
    QVariantAnimation,
    QVBoxLayout,
    QWidget,
    Signal,
)
from core.theme import Cores, Fontes
from core.validators import (
    FREQUENCIA_SEMANAL_OPCOES,
    SEXO_OPCOES,
    TEMPO_TREINO_OPCOES,
    validar_altura,
    validar_frequencia_semanal,
    validar_idade,
    validar_nome_completo,
    validar_objetivo_principal,
    validar_sexo,
    validar_tempo_sem_atividade,
    validar_tempo_treinamento,
    validar_tempo_treino_dia,
    validar_treinou_antes,
)
from gui.widgets.botao_principal import BotaoPrimario, BotaoSecundario
from gui.widgets.corpo_interativo import (
    CAMINHO_IMAGEM_FEMININO,
    CAMINHO_IMAGEM_MASCULINO,
    IDS_REGIOES_FEMININO,
    IDS_REGIOES_MASCULINO,
    PASTA_MASCARAS_FEMININO,
    PASTA_MASCARAS_MASCULINO,
    CorpoInterativoWidget,
)


class _CampoFormulario(QWidget):
    def __init__(
        self,
        label_texto: str,
        campo: QWidget,
        parent=None,
        *,
        tamanho_fonte_label: int = Fontes.TAMANHO_LABEL,
        tamanho_fonte_campo: int = 15,
    ):
        super().__init__(parent)
        self.campo = campo
        self._tamanho_fonte_campo = tamanho_fonte_campo

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_texto)
        label.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {tamanho_fonte_label}px; font-weight: 600;"
        )
        layout.addWidget(label)
        layout.addWidget(campo)

        self.label_erro = QLabel("")
        self.label_erro.setStyleSheet(
            f"background: transparent; border: none; color: {Cores.ERRO}; font-size: 12px;"
        )
        self.label_erro.hide()
        layout.addWidget(self.label_erro)

        self._marcar_campo(com_erro=False)

    def mostrar_erro(self, mensagem: str) -> None:
        self.label_erro.setText(mensagem)
        self.label_erro.show()
        self._marcar_campo(com_erro=True)

    def limpar_erro(self) -> None:
        self.label_erro.hide()
        self._marcar_campo(com_erro=False)

    def _marcar_campo(self, com_erro: bool) -> None:
        cor_borda = Cores.ERRO if com_erro else Cores.BORDA
        campo = self.campo
        if not isinstance(campo, (QLineEdit, QComboBox)):
            campo = campo.findChild(QLineEdit) or campo.findChild(QComboBox)
            if campo is None:
                return
        if isinstance(campo, QLineEdit):
            campo.setStyleSheet(
                f"""
                QLineEdit {{
                    background-color: {Cores.SUPERFICIE};
                    border: 1px solid {cor_borda};
                    border-radius: 10px;
                    padding-left: 18px;
                    font-size: {self._tamanho_fonte_campo}px;
                    color: {Cores.TEXTO_PRIMARIO};
                    min-height: 54px;
                }}
                QLineEdit:focus {{ border: 1px solid {Cores.AZUL_PRIMARIO}; }}
                """
            )
        elif isinstance(campo, QComboBox):
            campo.setStyleSheet(
                f"""
                QComboBox {{
                    background-color: {Cores.SUPERFICIE};
                    border: 1px solid {cor_borda};
                    border-radius: 10px;
                    padding-left: 18px;
                    font-size: {self._tamanho_fonte_campo}px;
                    color: {Cores.TEXTO_PRIMARIO};
                    min-height: 54px;
                }}
                QComboBox:focus {{
                    border: 1px solid {Cores.AZUL_PRIMARIO};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 30px;
                }}
                QComboBox::down-arrow {{
                    width: 10px;
                    height: 10px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {Cores.SUPERFICIE};
                    color: {Cores.TEXTO_PRIMARIO};
                    border: 1px solid {Cores.BORDA};
                    border-radius: 8px;
                    outline: none;
                    padding: 4px;
                    selection-background-color: {Cores.AZUL_PRIMARIO};
                    selection-color: white;
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: 32px;
                    padding-left: 10px;
                    border-radius: 6px;
                    color: {Cores.TEXTO_PRIMARIO};
                }}
                QComboBox QAbstractItemView::item:hover {{
                    background-color: {Cores.FUNDO};
                    color: {Cores.TEXTO_PRIMARIO};
                }}
                QComboBox QAbstractItemView::item:selected {{
                    background-color: {Cores.AZUL_PRIMARIO};
                    color: white;
                }}
                """
            )


def _aplicar_paleta_clara_popup(campo: QComboBox) -> None:
    paleta_popup = campo.view().palette()
    paleta_popup.setColor(QPalette.Base, QColor(Cores.SUPERFICIE))
    paleta_popup.setColor(QPalette.Text, QColor(Cores.TEXTO_PRIMARIO))
    paleta_popup.setColor(QPalette.Highlight, QColor(Cores.AZUL_PRIMARIO))
    paleta_popup.setColor(QPalette.HighlightedText, QColor("white"))
    campo.view().setPalette(paleta_popup)


def _criar_cartao() -> QFrame:
    cartao = QFrame()
    cartao.setStyleSheet(
        f"""
        background-color: {Cores.SUPERFICIE};
        border: 1px solid {Cores.BORDA};
        border-radius: 14px;
        """
    )
    return cartao


class _CampoAlturaMascarada(QLineEdit):
    _MAX_DIGITOS = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxLength(4)
        self.textEdited.connect(self._aplicar_mascara)

    def _aplicar_mascara(self, texto: str) -> None:
        digitos = "".join(caractere for caractere in texto if caractere.isdigit())
        digitos = digitos[: self._MAX_DIGITOS]

        if len(digitos) <= 1:
            novo_texto = digitos
        elif len(digitos) == 2:
            novo_texto = f"{digitos[0]}.{digitos[1]}"
        else:
            novo_texto = f"{digitos[0]}.{digitos[1:]}"

        self.setText(novo_texto)
        self.setCursorPosition(len(novo_texto))


class DadosAlunoStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        titulo = QLabel("Dados do Aluno")
        titulo.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: 30px; font-weight: 700;"
        )
        layout_raiz.addWidget(titulo)
        layout_raiz.addSpacing(6)

        descricao = QLabel(
            "Inicie o cadastro preenchendo as informações básicas do novo aluno "
            "para iniciar a avaliação."
        )
        descricao.setWordWrap(True)
        descricao.setStyleSheet(
            f"color: {Cores.TEXTO_DESCRICAO}; font-size: 18px; font-weight: 600;"
        )
        layout_raiz.addWidget(descricao)
        layout_raiz.addSpacing(16)

        cartao = _criar_cartao()
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 20, 28, 20)
        layout_cartao.setSpacing(16)

        self._campo_nome = QLineEdit()
        self._campo_nome.setPlaceholderText("Digite o nome completo do aluno")
        self._grupo_nome = _CampoFormulario(
            "Nome completo:",
            self._campo_nome,
            tamanho_fonte_label=15,
            tamanho_fonte_campo=16,
        )
        layout_cartao.addWidget(self._grupo_nome)

        self._campo_idade = QLineEdit()
        self._campo_idade.setPlaceholderText("Ex.: 25")
        self._campo_idade.setMaxLength(3)
        self._grupo_idade = _CampoFormulario(
            "Idade:",
            self._campo_idade,
            tamanho_fonte_label=15,
            tamanho_fonte_campo=16,
        )
        layout_cartao.addWidget(self._grupo_idade)

        self._campo_sexo = QComboBox()
        self._campo_sexo.setPlaceholderText("Selecione uma opção")
        for opcao in SEXO_OPCOES:
            self._campo_sexo.addItem(opcao, userData=opcao)
        self._campo_sexo.setCurrentIndex(-1)
        paleta_popup = self._campo_sexo.view().palette()
        paleta_popup.setColor(QPalette.Base, QColor(Cores.SUPERFICIE))
        paleta_popup.setColor(QPalette.Text, QColor(Cores.TEXTO_PRIMARIO))
        paleta_popup.setColor(QPalette.Highlight, QColor(Cores.AZUL_PRIMARIO))
        paleta_popup.setColor(QPalette.HighlightedText, QColor("white"))
        self._campo_sexo.view().setPalette(paleta_popup)
        self._grupo_sexo = _CampoFormulario(
            "Sexo:",
            self._campo_sexo,
            tamanho_fonte_label=15,
            tamanho_fonte_campo=16,
        )
        layout_cartao.addWidget(self._grupo_sexo)

        self._campo_altura = _CampoAlturaMascarada()
        self._campo_altura.setPlaceholderText("1.75")
        self._campo_altura.editingFinished.connect(self._formatar_altura)

        self._grupo_altura = _CampoFormulario(
            "Altura:",
            self._campo_altura,
            tamanho_fonte_label=15,
            tamanho_fonte_campo=16,
        )
        layout_cartao.addWidget(self._grupo_altura)

        layout_raiz.addWidget(cartao)

        self.setTabOrder(self._campo_nome, self._campo_idade)
        self.setTabOrder(self._campo_idade, self._campo_sexo)
        self.setTabOrder(self._campo_sexo, self._campo_altura)

    def obter_dados_validados(self):
        self._grupo_nome.limpar_erro()
        self._grupo_idade.limpar_erro()
        self._grupo_sexo.limpar_erro()
        self._grupo_altura.limpar_erro()

        nome = self._campo_nome.text()
        erro_nome = validar_nome_completo(nome)

        idade_texto = self._campo_idade.text()
        idade, erro_idade = validar_idade(idade_texto)

        sexo = self._campo_sexo.currentData()
        erro_sexo = validar_sexo(sexo)

        altura_texto = self._campo_altura.text()
        altura_m, erro_altura = validar_altura(altura_texto)

        valido = True
        if erro_nome:
            self._grupo_nome.mostrar_erro(erro_nome)
            valido = False
        if erro_idade:
            self._grupo_idade.mostrar_erro(erro_idade)
            valido = False
        if erro_sexo:
            self._grupo_sexo.mostrar_erro(erro_sexo)
            valido = False
        if erro_altura:
            self._grupo_altura.mostrar_erro(erro_altura)
            valido = False

        if not valido:
            return None

        return {
            "nome_completo": nome.strip(),
            "idade": idade,
            "sexo": sexo,
            "altura_m": altura_m,
        }

    def carregar_dados(self, dados: dict) -> None:
        self._campo_nome.setText(dados.get("nome_completo") or "")

        idade = dados.get("idade")
        self._campo_idade.setText("" if idade is None else str(idade))

        sexo = dados.get("sexo")
        self._campo_sexo.setCurrentIndex(self._campo_sexo.findData(sexo) if sexo else -1)

        altura_m = dados.get("altura_m")
        self._campo_altura.setText("" if altura_m is None else f"{altura_m:.2f}")

        self._grupo_nome.limpar_erro()
        self._grupo_idade.limpar_erro()
        self._grupo_sexo.limpar_erro()
        self._grupo_altura.limpar_erro()

    def bloquear_campos_fixos(self, bloqueado: bool) -> None:
        self._campo_nome.setReadOnly(bloqueado)
        self._campo_sexo.setEnabled(not bloqueado)

    def _formatar_altura(self) -> None:
        altura_m, erro = validar_altura(self._campo_altura.text())
        if erro is None:
            self._campo_altura.setText(f"{altura_m:.2f}")

    def limpar(self) -> None:
        self._campo_nome.clear()
        self._campo_idade.clear()
        self._campo_sexo.setCurrentIndex(-1)
        self._campo_altura.clear()
        self._grupo_nome.limpar_erro()
        self._grupo_idade.limpar_erro()
        self._grupo_sexo.limpar_erro()
        self._grupo_altura.limpar_erro()

    def focar_primeiro_campo(self) -> None:
        self._campo_nome.setFocus()


_SVG_CHECK = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="4 12 9 17 20 6"></polyline>
</svg>
"""

_SVG_X = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
    <line x1="5" y1="5" x2="19" y2="19"></line>
    <line x1="19" y1="5" x2="5" y2="19"></line>
</svg>
"""


def _renderizar_icone(svg_modelo: str, cor: str, tamanho: int = 16) -> QIcon:
    svg = svg_modelo.format(cor=cor)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(tamanho, tamanho)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class _BotaoOpcaoSimNao(QPushButton):
    def __init__(self, texto: str, positivo: bool, parent=None):
        super().__init__(f"  {texto}", parent)
        cor_destaque = Cores.SUCESSO if positivo else Cores.ERRO
        cor_fundo_marcado = Cores.SUCESSO_FUNDO if positivo else Cores.ERRO_FUNDO
        icone_svg = _SVG_CHECK if positivo else _SVG_X

        self.setIcon(_renderizar_icone(icone_svg, cor_destaque))
        self.setIconSize(QSize(16, 16))
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(54)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.BORDA};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 15px;
                font-weight: 600;
                color: {Cores.TEXTO_PRIMARIO};
                text-align: center;
            }}
            QPushButton:hover {{
                border: 1px solid {cor_destaque};
            }}
            QPushButton:checked {{
                background-color: {cor_fundo_marcado};
                border: 1px solid {cor_destaque};
                color: {cor_destaque};
            }}
            """
        )


class AnamneseStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        cabecalho = QFrame()
        cabecalho.setStyleSheet(
            f"background-color: {Cores.AZUL_ESCURO}; border-radius: 14px;"
        )
        layout_cabecalho = QVBoxLayout(cabecalho)
        layout_cabecalho.setContentsMargins(28, 20, 28, 20)
        layout_cabecalho.setSpacing(4)

        titulo_cabecalho = QLabel("Anamnese")
        titulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TITULO}px; font-weight: 700;"
        )
        layout_cabecalho.addWidget(titulo_cabecalho)

        subtitulo_cabecalho = QLabel("Etapa 2: Histórico de atividade física")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        cartao_treinou = _criar_cartao()
        layout_treinou = QVBoxLayout(cartao_treinou)
        layout_treinou.setContentsMargins(28, 24, 28, 24)
        layout_treinou.setSpacing(14)

        pergunta_treinou = QLabel("Já treinou antes?")
        pergunta_treinou.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_LABEL}px; font-weight: 600;"
        )
        layout_treinou.addWidget(pergunta_treinou)

        layout_opcoes = QHBoxLayout()
        layout_opcoes.setSpacing(14)
        self._botao_sim = _BotaoOpcaoSimNao("Sim", positivo=True)
        self._botao_nao = _BotaoOpcaoSimNao("Não", positivo=False)
        layout_opcoes.addWidget(self._botao_sim, stretch=1)
        layout_opcoes.addWidget(self._botao_nao, stretch=1)
        layout_treinou.addLayout(layout_opcoes)

        self._grupo_treinou = QButtonGroup(self)
        self._grupo_treinou.setExclusive(True)
        self._grupo_treinou.addButton(self._botao_sim)
        self._grupo_treinou.addButton(self._botao_nao)

        self._label_erro_treinou = QLabel("")
        self._label_erro_treinou.setStyleSheet(
            f"background: transparent; border: none; color: {Cores.ERRO}; font-size: 12px;"
        )
        self._label_erro_treinou.hide()
        layout_treinou.addWidget(self._label_erro_treinou)

        layout_raiz.addWidget(cartao_treinou)

        self._campo_tempo_treinamento = QLineEdit()
        self._campo_tempo_treinamento.setPlaceholderText("Ex: 6 meses, 2 anos...")
        self._grupo_tempo_treinamento = _CampoFormulario(
            "Treina há quanto tempo?", self._campo_tempo_treinamento
        )
        self._cartao_tempo_treinamento = self._empacotar_em_cartao(self._grupo_tempo_treinamento)
        layout_raiz.addWidget(self._cartao_tempo_treinamento)

        self._campo_tempo_parado = QLineEdit()
        self._campo_tempo_parado.setPlaceholderText("Ex: Nunca parei, 3 meses...")
        self._grupo_tempo_parado = _CampoFormulario(
            "Tempo sem atividade física?", self._campo_tempo_parado
        )
        self._cartao_tempo_parado = self._empacotar_em_cartao(self._grupo_tempo_parado)
        layout_raiz.addWidget(self._cartao_tempo_parado)

        self._botao_sim.toggled.connect(self._atualizar_visibilidade_tempo)
        self._atualizar_visibilidade_tempo()

    @staticmethod
    def _empacotar_em_cartao(conteudo: QWidget) -> QFrame:
        cartao = _criar_cartao()
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.addWidget(conteudo)
        return cartao

    def _atualizar_visibilidade_tempo(self) -> None:
        mostrar = self._botao_sim.isChecked()
        self._cartao_tempo_treinamento.setVisible(mostrar)
        self._cartao_tempo_parado.setVisible(mostrar)
        if not mostrar:
            self._campo_tempo_treinamento.clear()
            self._campo_tempo_parado.clear()
            self._grupo_tempo_treinamento.limpar_erro()
            self._grupo_tempo_parado.limpar_erro()

    def obter_dados_validados(self):
        self._label_erro_treinou.hide()
        self._grupo_tempo_treinamento.limpar_erro()
        self._grupo_tempo_parado.limpar_erro()

        if self._botao_sim.isChecked():
            treinou_antes = "Sim"
        elif self._botao_nao.isChecked():
            treinou_antes = "Não"
        else:
            treinou_antes = None

        erro_treinou = validar_treinou_antes(treinou_antes)

        valido = True
        primeiro_campo_invalido = None
        if erro_treinou:
            self._label_erro_treinou.setText(erro_treinou)
            self._label_erro_treinou.show()
            valido = False
            primeiro_campo_invalido = self._botao_sim

        if treinou_antes == "Sim":
            tempo_treinamento = self._campo_tempo_treinamento.text().strip()
            erro_tempo_treinamento = validar_tempo_treinamento(tempo_treinamento)

            tempo_sem_atividade = self._campo_tempo_parado.text().strip()
            erro_tempo_parado = validar_tempo_sem_atividade(tempo_sem_atividade)

            if erro_tempo_treinamento:
                self._grupo_tempo_treinamento.mostrar_erro(erro_tempo_treinamento)
                valido = False
                primeiro_campo_invalido = primeiro_campo_invalido or self._campo_tempo_treinamento
            if erro_tempo_parado:
                self._grupo_tempo_parado.mostrar_erro(erro_tempo_parado)
                valido = False
                primeiro_campo_invalido = primeiro_campo_invalido or self._campo_tempo_parado
        else:
            tempo_treinamento = None
            tempo_sem_atividade = None

        if not valido:
            if primeiro_campo_invalido is not None:
                primeiro_campo_invalido.setFocus()
            return None

        return {
            "treinou_antes": treinou_antes,
            "tempo_treinamento": tempo_treinamento,
            "tempo_sem_atividade": tempo_sem_atividade,
        }

    def limpar(self) -> None:
        self._grupo_treinou.setExclusive(False)
        self._botao_sim.setChecked(False)
        self._botao_nao.setChecked(False)
        self._grupo_treinou.setExclusive(True)
        self._campo_tempo_treinamento.clear()
        self._campo_tempo_parado.clear()
        self._label_erro_treinou.hide()
        self._grupo_tempo_treinamento.limpar_erro()
        self._grupo_tempo_parado.limpar_erro()

    def carregar_dados(self, dados: dict) -> None:
        treinou_antes = dados.get("treinou_antes")
        self._grupo_treinou.setExclusive(False)
        self._botao_sim.setChecked(treinou_antes == "Sim")
        self._botao_nao.setChecked(treinou_antes == "Não")
        self._grupo_treinou.setExclusive(True)

        self._campo_tempo_treinamento.setText(dados.get("tempo_treinamento") or "")
        self._campo_tempo_parado.setText(dados.get("tempo_sem_atividade") or "")

        self._label_erro_treinou.hide()
        self._grupo_tempo_treinamento.limpar_erro()
        self._grupo_tempo_parado.limpar_erro()

    def bloquear_campos_fixos(self, bloqueado: bool) -> None:
        self._botao_sim.setEnabled(not bloqueado)
        self._botao_nao.setEnabled(not bloqueado)
        self._campo_tempo_treinamento.setReadOnly(bloqueado)
        self._campo_tempo_parado.setReadOnly(bloqueado)


_TAMANHO_ICONE_OBJETIVO = 18
_DURACAO_TRANSICAO_ICONE_MS = 200

_SVG_TENDENCIA_BAIXA = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline>
    <polyline points="17 18 23 18 23 12"></polyline>
</svg>
"""

_SVG_HALTER = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="1" y="9" width="4" height="6" rx="1"></rect>
    <rect x="19" y="9" width="4" height="6" rx="1"></rect>
    <line x1="5" y1="12" x2="19" y2="12"></line>
</svg>
"""

_SVG_PULSO = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
</svg>
"""

_SVG_CRUZ_MEDICA = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="9"></circle>
    <line x1="12" y1="8" x2="12" y2="16"></line>
    <line x1="8" y1="12" x2="16" y2="12"></line>
</svg>
"""

_SVG_MAIS_OPCOES = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
    <circle cx="5" cy="12" r="1.6" fill="{cor}" stroke="none"></circle>
    <circle cx="12" cy="12" r="1.6" fill="{cor}" stroke="none"></circle>
    <circle cx="19" cy="12" r="1.6" fill="{cor}" stroke="none"></circle>
</svg>
"""


class _BotaoObjetivo(QPushButton):
    def __init__(self, texto: str, svg_icone: str, parent=None):
        super().__init__(texto, parent)
        self._svg_icone = svg_icone
        self._cor_normal = QColor(Cores.TEXTO_SECUNDARIO)
        self._cor_selecionado = QColor(Cores.SUCESSO)

        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(54)
        self.setIconSize(QSize(_TAMANHO_ICONE_OBJETIVO, _TAMANHO_ICONE_OBJETIVO))
        self._aplicar_cor_icone(self._cor_normal)

        self._animacao_icone = QVariantAnimation(self)
        self._animacao_icone.setDuration(_DURACAO_TRANSICAO_ICONE_MS)
        self._animacao_icone.setEasingCurve(QEasingCurve.InOutQuad)
        self._animacao_icone.valueChanged.connect(self._aplicar_cor_icone)
        self.toggled.connect(self._animar_para_estado)

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.BORDA};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 15px;
                font-weight: 600;
                color: {Cores.TEXTO_PRIMARIO};
                text-align: center;
            }}
            QPushButton:hover {{
                border: 1px solid {Cores.SUCESSO};
            }}
            QPushButton:checked {{
                background-color: {Cores.SUCESSO_FUNDO};
                border: 1px solid {Cores.SUCESSO};
                color: {Cores.SUCESSO};
            }}
            """
        )

    def _animar_para_estado(self, marcado: bool) -> None:
        cor_atual = self._animacao_icone.currentValue() or self._cor_normal
        self._animacao_icone.stop()
        self._animacao_icone.setStartValue(QColor(cor_atual))
        self._animacao_icone.setEndValue(
            self._cor_selecionado if marcado else self._cor_normal
        )
        self._animacao_icone.start()

    def _aplicar_cor_icone(self, cor: QColor) -> None:
        self.setIcon(_renderizar_icone(self._svg_icone, cor.name(), _TAMANHO_ICONE_OBJETIVO))


_OBJETIVOS = [
    ("Emagrecimento", "emagrecimento", _SVG_TENDENCIA_BAIXA),
    ("Hipertrofia", "hipertrofia", _SVG_HALTER),
    ("Condicionamento", "condicionamento", _SVG_PULSO),
    ("Reabilitação", "reabilitacao", _SVG_CRUZ_MEDICA),
]
_OBJETIVO_OUTRO_VALOR = "outro"


class ObjetivoPrincipalStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        cabecalho = QFrame()
        cabecalho.setStyleSheet(
            f"background-color: {Cores.AZUL_ESCURO}; border-radius: 14px;"
        )
        layout_cabecalho = QVBoxLayout(cabecalho)
        layout_cabecalho.setContentsMargins(28, 20, 28, 20)
        layout_cabecalho.setSpacing(4)

        titulo_cabecalho = QLabel("Anamnese")
        titulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TITULO}px; font-weight: 700;"
        )
        layout_cabecalho.addWidget(titulo_cabecalho)

        subtitulo_cabecalho = QLabel("Etapa 3: Objetivo principal")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        cartao = _criar_cartao()
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(14)

        pergunta = QLabel("Qual seu objetivo principal?")
        pergunta.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_LABEL}px; font-weight: 600;"
        )
        layout_cartao.addWidget(pergunta)

        grade = QGridLayout()
        grade.setHorizontalSpacing(14)
        grade.setVerticalSpacing(14)

        self._grupo_objetivo = QButtonGroup(self)
        self._grupo_objetivo.setExclusive(True)
        self._botoes_objetivo = {}

        for indice, (texto, valor, svg_icone) in enumerate(_OBJETIVOS):
            botao = _BotaoObjetivo(texto, svg_icone)
            self._grupo_objetivo.addButton(botao)
            self._botoes_objetivo[valor] = botao
            grade.addWidget(botao, indice // 2, indice % 2)

        layout_cartao.addLayout(grade)

        self._botao_outro = _BotaoObjetivo("Outro", _SVG_MAIS_OPCOES)
        self._grupo_objetivo.addButton(self._botao_outro)
        self._botoes_objetivo[_OBJETIVO_OUTRO_VALOR] = self._botao_outro
        layout_cartao.addWidget(self._botao_outro)

        self._bloco_outro = QWidget()
        layout_bloco_outro = QVBoxLayout(self._bloco_outro)
        layout_bloco_outro.setContentsMargins(0, 0, 0, 0)
        layout_bloco_outro.setSpacing(6)

        label_outro = QLabel("Descreva seu objetivo:")
        label_outro.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_LABEL}px; font-weight: 600;"
        )
        layout_bloco_outro.addWidget(label_outro)

        self._campo_outro = QTextEdit()
        self._campo_outro.setPlaceholderText("Descreva seu objetivo aqui...")
        self._campo_outro.setFixedHeight(90)
        self._estilo_campo_outro_normal = f"""
            QTextEdit {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.BORDA};
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 15px;
                color: {Cores.TEXTO_PRIMARIO};
            }}
            QTextEdit:focus {{ border: 1px solid {Cores.AZUL_PRIMARIO}; }}
            """
        self._estilo_campo_outro_erro = f"""
            QTextEdit {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.ERRO};
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 15px;
                color: {Cores.TEXTO_PRIMARIO};
            }}
            QTextEdit:focus {{ border: 1px solid {Cores.AZUL_PRIMARIO}; }}
            """
        self._campo_outro.setStyleSheet(self._estilo_campo_outro_normal)
        layout_bloco_outro.addWidget(self._campo_outro)

        self._label_erro_outro = QLabel("")
        self._label_erro_outro.setStyleSheet(
            f"background: transparent; border: none; color: {Cores.ERRO}; font-size: 12px;"
        )
        self._label_erro_outro.hide()
        layout_bloco_outro.addWidget(self._label_erro_outro)

        self._bloco_outro.hide()
        layout_cartao.addWidget(self._bloco_outro)

        self._botao_outro.toggled.connect(self._bloco_outro.setVisible)
        self._botao_outro.toggled.connect(lambda _: self._limpar_erro_outro())
        self._campo_outro.textChanged.connect(self._limpar_erro_outro)

        self._label_erro_objetivo = QLabel("")
        self._label_erro_objetivo.setStyleSheet(
            f"background: transparent; border: none; color: {Cores.ERRO}; font-size: 12px;"
        )
        self._label_erro_objetivo.hide()
        layout_cartao.addWidget(self._label_erro_objetivo)

        layout_raiz.addWidget(cartao)
        layout_raiz.addStretch(1)

    def _limpar_erro_outro(self) -> None:
        self._label_erro_outro.hide()
        self._campo_outro.setStyleSheet(self._estilo_campo_outro_normal)

    def obter_dados_validados(self):
        self._label_erro_objetivo.hide()
        self._limpar_erro_outro()

        objetivo = None
        for valor, botao in self._botoes_objetivo.items():
            if botao.isChecked():
                objetivo = valor
                break

        erro = validar_objetivo_principal(objetivo)
        if erro:
            self._label_erro_objetivo.setText(erro)
            self._label_erro_objetivo.show()
            return None

        objetivo_outro = None
        if objetivo == _OBJETIVO_OUTRO_VALOR:
            objetivo_outro = self._campo_outro.toPlainText().strip()
            if not objetivo_outro:
                self._label_erro_outro.setText("Descreva seu objetivo.")
                self._label_erro_outro.show()
                self._campo_outro.setStyleSheet(self._estilo_campo_outro_erro)
                self._campo_outro.setFocus()
                return None

        return {
            "objetivo_principal": objetivo,
            "objetivo_outro": objetivo_outro,
        }

    def limpar(self) -> None:
        self._grupo_objetivo.setExclusive(False)
        for botao in self._botoes_objetivo.values():
            botao.setChecked(False)
        self._grupo_objetivo.setExclusive(True)
        self._campo_outro.clear()
        self._label_erro_objetivo.hide()
        self._limpar_erro_outro()

    def carregar_dados(self, dados: dict) -> None:
        self._grupo_objetivo.setExclusive(False)
        for botao in self._botoes_objetivo.values():
            botao.setChecked(False)
        self._grupo_objetivo.setExclusive(True)

        objetivo = dados.get("objetivo_principal")
        botao_selecionado = self._botoes_objetivo.get(objetivo)
        if botao_selecionado is not None:
            botao_selecionado.setChecked(True)

        self._campo_outro.setPlainText(dados.get("objetivo_outro") or "")
        self._label_erro_objetivo.hide()
        self._limpar_erro_outro()

    def bloquear_campos_fixos(self, bloqueado: bool) -> None:
        for botao in self._botoes_objetivo.values():
            botao.setEnabled(not bloqueado)
        self._campo_outro.setReadOnly(bloqueado)


class FrequenciaTreinoStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        cabecalho = QFrame()
        cabecalho.setStyleSheet(
            f"background-color: {Cores.AZUL_ESCURO}; border-radius: 14px;"
        )
        layout_cabecalho = QVBoxLayout(cabecalho)
        layout_cabecalho.setContentsMargins(28, 20, 28, 20)
        layout_cabecalho.setSpacing(4)

        titulo_cabecalho = QLabel("Anamnese")
        titulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TITULO}px; font-weight: 700;"
        )
        layout_cabecalho.addWidget(titulo_cabecalho)

        subtitulo_cabecalho = QLabel("Etapa 4: Frequência e tempo de treino")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        self._campo_frequencia = QComboBox()
        for opcao in FREQUENCIA_SEMANAL_OPCOES:
            self._campo_frequencia.addItem(opcao, userData=opcao)
        _aplicar_paleta_clara_popup(self._campo_frequencia)
        self._grupo_frequencia = _CampoFormulario(
            "Frequência semanal?", self._campo_frequencia
        )
        layout_raiz.addWidget(self._empacotar_em_cartao(self._grupo_frequencia))

        self._campo_tempo_treino = QComboBox()
        for opcao in TEMPO_TREINO_OPCOES:
            self._campo_tempo_treino.addItem(opcao, userData=opcao)
        _aplicar_paleta_clara_popup(self._campo_tempo_treino)
        self._grupo_tempo_treino = _CampoFormulario(
            "Tempo de Treino por dia?", self._campo_tempo_treino
        )
        layout_raiz.addWidget(self._empacotar_em_cartao(self._grupo_tempo_treino))

        layout_raiz.addStretch(1)

        self.setTabOrder(self._campo_frequencia, self._campo_tempo_treino)

    @staticmethod
    def _empacotar_em_cartao(conteudo: QWidget) -> QFrame:
        cartao = _criar_cartao()
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.addWidget(conteudo)
        return cartao

    def obter_dados_validados(self):
        self._grupo_frequencia.limpar_erro()
        self._grupo_tempo_treino.limpar_erro()

        frequencia = self._campo_frequencia.currentData()
        erro_frequencia = validar_frequencia_semanal(frequencia)

        tempo_treino = self._campo_tempo_treino.currentData()
        erro_tempo_treino = validar_tempo_treino_dia(tempo_treino)

        valido = True
        if erro_frequencia:
            self._grupo_frequencia.mostrar_erro(erro_frequencia)
            valido = False
        if erro_tempo_treino:
            self._grupo_tempo_treino.mostrar_erro(erro_tempo_treino)
            valido = False

        if not valido:
            return None

        return {
            "frequencia_semanal": frequencia,
            "tempo_treino_dia": tempo_treino,
        }

    def limpar(self) -> None:
        self._campo_frequencia.setCurrentIndex(0)
        self._campo_tempo_treino.setCurrentIndex(0)
        self._grupo_frequencia.limpar_erro()
        self._grupo_tempo_treino.limpar_erro()

    def carregar_dados(self, dados: dict) -> None:
        frequencia = dados.get("frequencia_semanal")
        indice_frequencia = self._campo_frequencia.findData(frequencia) if frequencia else -1
        self._campo_frequencia.setCurrentIndex(indice_frequencia if indice_frequencia >= 0 else 0)

        tempo_treino = dados.get("tempo_treino_dia")
        indice_tempo = self._campo_tempo_treino.findData(tempo_treino) if tempo_treino else -1
        self._campo_tempo_treino.setCurrentIndex(indice_tempo if indice_tempo >= 0 else 0)

        self._grupo_frequencia.limpar_erro()
        self._grupo_tempo_treino.limpar_erro()

    def bloquear_campos_fixos(self, bloqueado: bool) -> None:
        pass


class _PerguntaSaude(QWidget):
    def __init__(self, texto_pergunta: str, parent=None, com_qual: bool = True):
        super().__init__(parent)
        self._com_qual = com_qual

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(6)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        label = QLabel(texto_pergunta)
        label.setWordWrap(True)
        label.setFixedWidth(220)
        label.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_LABEL}px; font-weight: 600;"
        )
        layout.addWidget(label)

        self._botao_sim = _BotaoOpcaoSimNao("Sim", positivo=True)
        self._botao_nao = _BotaoOpcaoSimNao("Não", positivo=False)
        layout.addWidget(self._botao_sim)
        layout.addWidget(self._botao_nao)

        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._grupo.addButton(self._botao_sim)
        self._grupo.addButton(self._botao_nao)

        self._campo_qual = QLineEdit()
        self._campo_qual.setPlaceholderText("Qual?")
        self._estilo_qual_normal = f"""
            QLineEdit {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.BORDA};
                border-radius: 10px;
                padding-left: 14px;
                font-size: 15px;
                color: {Cores.TEXTO_PRIMARIO};
                min-height: 54px;
            }}
            QLineEdit:focus {{ border: 1px solid {Cores.AZUL_PRIMARIO}; }}
            """
        self._estilo_qual_erro = f"""
            QLineEdit {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.ERRO};
                border-radius: 10px;
                padding-left: 14px;
                font-size: 15px;
                color: {Cores.TEXTO_PRIMARIO};
                min-height: 54px;
            }}
            QLineEdit:focus {{ border: 1px solid {Cores.AZUL_PRIMARIO}; }}
            """
        self._campo_qual.setStyleSheet(self._estilo_qual_normal)
        self._campo_qual.hide()
        layout.addWidget(self._campo_qual, stretch=1)

        if com_qual:
            self._botao_sim.toggled.connect(self._campo_qual.setVisible)
        self._botao_sim.toggled.connect(lambda _: self.limpar_erro())
        self._botao_nao.toggled.connect(lambda _: self.limpar_erro())
        self._campo_qual.textChanged.connect(self.limpar_erro)

        layout_raiz.addLayout(layout)

        self._label_erro = QLabel("")
        self._label_erro.setStyleSheet(
            f"background: transparent; border: none; color: {Cores.ERRO}; font-size: 12px;"
        )
        self._label_erro.hide()
        layout_raiz.addWidget(self._label_erro)

    def validar(self) -> bool:
        self.limpar_erro()
        tem, qual = self.obter_resposta()

        if tem not in ("Sim", "Não"):
            self._mostrar_erro("Selecione uma opção.")
            return False

        if tem == "Sim" and self._com_qual and not qual:
            self._mostrar_erro("Preencha esse campo.")
            self._campo_qual.setStyleSheet(self._estilo_qual_erro)
            return False

        return True

    def _mostrar_erro(self, mensagem: str) -> None:
        self._label_erro.setText(mensagem)
        self._label_erro.show()

    def limpar_erro(self) -> None:
        self._label_erro.hide()
        self._campo_qual.setStyleSheet(self._estilo_qual_normal)

    def focar_invalido(self) -> None:
        if self._botao_sim.isChecked() and not self._campo_qual.text().strip():
            self._campo_qual.setFocus()
        else:
            self._botao_sim.setFocus()

    def obter_resposta(self):
        if self._botao_sim.isChecked():
            tem = "Sim"
        elif self._botao_nao.isChecked():
            tem = "Não"
        else:
            tem = None

        qual = self._campo_qual.text().strip() if tem == "Sim" else None
        return tem, qual

    def limpar(self) -> None:
        self._grupo.setExclusive(False)
        self._botao_sim.setChecked(False)
        self._botao_nao.setChecked(False)
        self._grupo.setExclusive(True)
        self._campo_qual.clear()
        self.limpar_erro()

    def definir_resposta(self, tem: Optional[str], qual: Optional[str]) -> None:
        self._grupo.setExclusive(False)
        self._botao_sim.setChecked(tem == "Sim")
        self._botao_nao.setChecked(tem == "Não")
        self._grupo.setExclusive(True)
        self._campo_qual.setText(qual or "")
        self.limpar_erro()


_PERGUNTAS_SAUDE = [
    ("doenca", "Doença/Problema de saúde?"),
    ("limitacao", "Limitação de movimento?"),
    ("dor", "Dor em algum movimento?"),
    ("cirurgia", "Cirurgia?"),
]


class HistoricoSaudeStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        cabecalho = QFrame()
        cabecalho.setStyleSheet(
            f"background-color: {Cores.AZUL_ESCURO}; border-radius: 14px;"
        )
        layout_cabecalho = QVBoxLayout(cabecalho)
        layout_cabecalho.setContentsMargins(28, 20, 28, 20)
        layout_cabecalho.setSpacing(4)

        titulo_cabecalho = QLabel("Anamnese")
        titulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TITULO}px; font-weight: 700;"
        )
        layout_cabecalho.addWidget(titulo_cabecalho)

        subtitulo_cabecalho = QLabel("Etapa 5: Histórico de saúde e limitações")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        cartao = _criar_cartao()
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(20)

        self._perguntas = {}
        for chave, texto in _PERGUNTAS_SAUDE:
            pergunta = _PerguntaSaude(texto)
            self._perguntas[chave] = pergunta
            layout_cartao.addWidget(pergunta)

        layout_raiz.addWidget(cartao)
        layout_raiz.addStretch(1)

    def obter_dados_validados(self):
        primeira_invalida = None
        valido = True
        for pergunta in self._perguntas.values():
            if not pergunta.validar():
                valido = False
                if primeira_invalida is None:
                    primeira_invalida = pergunta

        if not valido:
            primeira_invalida.focar_invalido()
            return None

        dados = {}
        for chave, pergunta in self._perguntas.items():
            tem, qual = pergunta.obter_resposta()
            dados[f"{chave}_tem"] = tem
            dados[f"{chave}_qual"] = qual
        return dados

    def limpar(self) -> None:
        for pergunta in self._perguntas.values():
            pergunta.limpar()

    def carregar_dados(self, dados: dict) -> None:
        for chave, pergunta in self._perguntas.items():
            pergunta.definir_resposta(dados.get(f"{chave}_tem"), dados.get(f"{chave}_qual"))


_PERGUNTAS_HABITOS = [
    ("medicamento_controlado", "Medicamento controlado?"),
    ("fazendo_dieta", "Está fazendo dieta?"),
    ("consumo_alcool", "Consumo de álcool?"),
    ("fuma", "Fuma?"),
]


class HabitosVidaStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        cabecalho = QFrame()
        cabecalho.setStyleSheet(
            f"background-color: {Cores.AZUL_ESCURO}; border-radius: 14px;"
        )
        layout_cabecalho = QVBoxLayout(cabecalho)
        layout_cabecalho.setContentsMargins(28, 20, 28, 20)
        layout_cabecalho.setSpacing(4)

        titulo_cabecalho = QLabel("Anamnese")
        titulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TITULO}px; font-weight: 700;"
        )
        layout_cabecalho.addWidget(titulo_cabecalho)

        subtitulo_cabecalho = QLabel("Etapa 6: Hábitos de vida")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        cartao = _criar_cartao()
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(20)

        self._perguntas = {}
        for chave, texto in _PERGUNTAS_HABITOS:
            pergunta = _PerguntaSaude(texto, com_qual=False)
            self._perguntas[chave] = pergunta
            layout_cartao.addWidget(pergunta)

        layout_raiz.addWidget(cartao)
        layout_raiz.addStretch(1)

    def obter_dados_validados(self):
        invalidas = [p for p in self._perguntas.values() if not p.validar()]
        if invalidas:
            invalidas[0].focar_invalido()
            return None
        return {chave: pergunta.obter_resposta()[0] for chave, pergunta in self._perguntas.items()}

    def limpar(self) -> None:
        for pergunta in self._perguntas.values():
            pergunta.limpar()

    def carregar_dados(self, dados: dict) -> None:
        for chave, pergunta in self._perguntas.items():
            pergunta.definir_resposta(dados.get(chave), None)


def _cabecalho_bloco_medidas(texto: str, *, centralizado: bool = False) -> QFrame:
    cabecalho = QFrame()
    cabecalho.setStyleSheet(
        f"background-color: {Cores.AZUL_ESCURO}; border: none; "
        f"border-top-left-radius: 14px; border-top-right-radius: 14px;"
    )
    layout = QVBoxLayout(cabecalho)
    layout.setContentsMargins(20, 12, 20, 12)
    titulo = QLabel(texto)
    titulo.setStyleSheet(
        f"background: transparent; border: none; color: white; "
        f"font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 700;"
    )
    if centralizado:
        titulo.setAlignment(Qt.AlignCenter)
    layout.addWidget(titulo)
    return cabecalho


def _texto_para_numero(texto: str) -> Optional[float]:
    texto = (texto or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


_LINHAS_PARTE_SUPERIOR = [
    ("ombro", "Ombro", "shoulder"),
    ("torax", "Tórax", "chest"),
    ("cintura", "Cintura", "waist"),
    ("abdominal", "Abdominal", "abdomen"),
    ("quadril", "Quadril", "hip"),
]
_LINHAS_BRACOS = [
    ("braco_e", "Braço (E)", "left_arm"),
    ("braco_e_contraido", "Braço (E) Contraído", "left_arm"),
    ("braco_d", "Braço (D)", "right_arm"),
    ("braco_d_contraido", "Braço (D) Contraído", "right_arm"),
    ("antebraco_e", "Antebraço (E)", "left_forearm"),
    ("antebraco_d", "Antebraço (D)", "right_forearm"),
]
_LINHAS_PARTE_INFERIOR = [
    ("coxa_d", "Coxa D", "right_thigh"),
    ("coxa_e", "Coxa E", "left_thigh"),
    ("panturrilha_e", "Panturrilha E", "left_calf"),
    ("panturrilha_d", "Panturrilha D", "right_calf"),
]
_REGIAO_POR_CHAVE = {
    chave: regiao
    for chave, _texto, regiao in _LINHAS_PARTE_SUPERIOR + _LINHAS_BRACOS + _LINHAS_PARTE_INFERIOR
}


class AvaliacaoFisicaStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._num_colunas = _NUM_COLUNAS_INICIAL
        self._num_avaliacoes_salvas = 0
        self._coluna_ativa = 0

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        cartao = _criar_cartao()
        cartao.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout_cartao = QHBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(24)

        self._tabela_circunferencias, self._campos_circunferencias = _criar_tabela_widgets(
            _LINHAS_CIRCUNFERENCIAS
        )

        self._botao_nova_avaliacao = QPushButton("+")
        self._botao_nova_avaliacao.setCursor(Qt.PointingHandCursor)
        self._botao_nova_avaliacao.setFixedSize(28, 28)
        self._botao_nova_avaliacao.setToolTip("Adicionar nova avaliação")
        self._botao_nova_avaliacao.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 35);
                color: white;
                border: 1px solid rgba(255, 255, 255, 110);
                border-radius: 14px;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 70); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 110); }
            """
        )
        self._botao_nova_avaliacao.clicked.connect(self._adicionar_nova_avaliacao)

        bloco_circunferencias = _criar_card_tabela(
            "Circunferências",
            self._tabela_circunferencias,
            widget_extra_cabecalho=self._botao_nova_avaliacao,
        )

        painel_tabela = QWidget()
        painel_tabela.setStyleSheet("background: transparent;")
        coluna_tabela = QVBoxLayout(painel_tabela)
        coluna_tabela.setContentsMargins(0, 0, 4, 0)
        coluna_tabela.setSpacing(0)
        coluna_tabela.addWidget(bloco_circunferencias)
        coluna_tabela.addStretch(1)

        rolagem_tabela = QScrollArea()
        rolagem_tabela.setWidget(painel_tabela)
        rolagem_tabela.setWidgetResizable(True)
        rolagem_tabela.setFrameShape(QFrame.NoFrame)
        rolagem_tabela.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rolagem_tabela.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        rolagem_tabela.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        layout_cartao.addWidget(rolagem_tabela, stretch=3)

        self._pilha_corpo = QStackedWidget()

        self._corpo_masculino = CorpoInterativoWidget(
            CAMINHO_IMAGEM_MASCULINO, PASTA_MASCARAS_MASCULINO, IDS_REGIOES_MASCULINO
        )
        self._corpo_masculino.regiao_clicada.connect(self._focar_campo_da_regiao)
        self._pilha_corpo.addWidget(self._corpo_masculino)

        self._corpo_feminino = CorpoInterativoWidget(
            CAMINHO_IMAGEM_FEMININO, PASTA_MASCARAS_FEMININO, IDS_REGIOES_FEMININO
        )
        self._corpo_feminino.regiao_clicada.connect(self._focar_campo_da_regiao)
        self._pilha_corpo.addWidget(self._corpo_feminino)

        self._placeholder_corpo = QLabel("Selecione o sexo na\nEtapa 1 para ver o boneco")
        self._placeholder_corpo.setAlignment(Qt.AlignCenter)
        self._placeholder_corpo.setWordWrap(True)
        self._placeholder_corpo.setStyleSheet(
            f"background-color: {Cores.FUNDO}; border: 1px dashed {Cores.BORDA}; "
            f"border-radius: 12px; color: {Cores.TEXTO_SECUNDARIO}; "
            f"font-size: 13px; font-weight: 600;"
        )
        self._pilha_corpo.addWidget(self._placeholder_corpo)

        layout_cartao.addWidget(self._pilha_corpo, stretch=2)

        layout_raiz.addWidget(cartao, stretch=1)

        self._conectar_coluna_boneco(
            [(chave, self._campos_circunferencias[chave][0]) for chave in _REGIAO_POR_CHAVE]
        )
        self._recalcular_destaques()

    def ao_entrar(self, dados_coletados: dict) -> None:
        sexo = dados_coletados.get("sexo")
        if sexo == "Masculino":
            pagina = self._corpo_masculino
        elif sexo == "Feminino":
            pagina = self._corpo_feminino
        else:
            pagina = self._placeholder_corpo
        self._pilha_corpo.setCurrentWidget(pagina)


    def _conectar_coluna_boneco(self, pares_chave_widget) -> None:
        for _chave, widget in pares_chave_widget:
            widget.textChanged.connect(self._recalcular_destaques)

    def _adicionar_nova_avaliacao(self) -> None:
        novos = _adicionar_coluna_tabela(
            self._tabela_circunferencias, self._campos_circunferencias, _LINHAS_CIRCUNFERENCIAS
        )
        self._conectar_coluna_boneco(
            [(chave, widget) for chave, widget in novos if chave in _REGIAO_POR_CHAVE]
        )

        self._num_colunas += 1
        self._coluna_ativa = self._num_colunas - 1

        barra = self._tabela_circunferencias.horizontalScrollBar()
        barra.setValue(barra.maximum())

    def avaliacoes_ja_salvas(self) -> int:
        return self._num_avaliacoes_salvas

    def _definir_coluna_bloqueada(self, coluna: int, bloqueada: bool) -> None:
        for chave, _rotulo, _tipo, _maximo in _LINHAS_CIRCUNFERENCIAS:
            _definir_celula_somente_leitura(self._campos_circunferencias[chave][coluna], bloqueada)

    def _recalcular_destaques(self) -> None:
        regioes_ativas = {
            regiao
            for chave, regiao in _REGIAO_POR_CHAVE.items()
            if any(campo.text().strip() for campo in self._campos_circunferencias[chave])
        }
        self._corpo_masculino.definir_regioes_selecionadas(regioes_ativas)
        self._corpo_feminino.definir_regioes_selecionadas(regioes_ativas)

    def _focar_campo_da_regiao(self, regiao_id: str) -> None:
        for chave, id_regiao in _REGIAO_POR_CHAVE.items():
            if id_regiao == regiao_id:
                campo = self._campos_circunferencias[chave][self._coluna_ativa]
                campo.setFocus()
                campo.selectAll()
                return

    def obter_dados_validados(self):
        def extrair_numeros(chave):
            return [
                _texto_para_numero(campo.text())
                for campo in self._campos_circunferencias[chave]
            ]

        def extrair_datas():
            return [_valor_data(campo) for campo in self._campos_circunferencias["datas"]]

        circunferencias = {"datas": extrair_datas()}
        for chave, _rotulo, tipo, _maximo in _LINHAS_CIRCUNFERENCIAS:
            if tipo == "numero":
                circunferencias[chave] = extrair_numeros(chave)

        return {"circunferencias": circunferencias}

    def limpar(self) -> None:
        _remover_colunas_extras_tabela(self._tabela_circunferencias, self._campos_circunferencias)
        self._num_colunas = _NUM_COLUNAS_INICIAL
        self._num_avaliacoes_salvas = 0
        self._coluna_ativa = 0
        for widgets in self._campos_circunferencias.values():
            for widget in widgets:
                _limpar_widget(widget)
        self._definir_coluna_bloqueada(0, False)
        self._recalcular_destaques()

    def carregar_avaliacoes(self, avaliacoes: list) -> None:
        _remover_colunas_extras_tabela(self._tabela_circunferencias, self._campos_circunferencias)
        self._num_colunas = _NUM_COLUNAS_INICIAL
        self._num_avaliacoes_salvas = 0
        self._coluna_ativa = 0
        for widgets in self._campos_circunferencias.values():
            for widget in widgets:
                _limpar_widget(widget)
        self._definir_coluna_bloqueada(0, False)

        if not avaliacoes:
            self._recalcular_destaques()
            return

        while self._num_colunas < len(avaliacoes):
            novos = _adicionar_coluna_tabela(
                self._tabela_circunferencias, self._campos_circunferencias, _LINHAS_CIRCUNFERENCIAS
            )
            self._conectar_coluna_boneco(
                [(chave, widget) for chave, widget in novos if chave in _REGIAO_POR_CHAVE]
            )
            self._num_colunas += 1
        self._coluna_ativa = self._num_colunas - 1

        for coluna, avaliacao in enumerate(avaliacoes):
            data_valida = _qdate_de_texto(avaliacao.get("data"))
            self._campos_circunferencias["datas"][coluna].setDate(data_valida or _DATA_SENTINELA)
            for chave, _rotulo, tipo, _maximo in _LINHAS_CIRCUNFERENCIAS:
                if tipo != "numero":
                    continue
                valor = avaliacao.get(chave)
                campo = self._campos_circunferencias[chave][coluna]
                campo.setText("" if valor is None else _formatar_numero(valor))

        self._num_avaliacoes_salvas = len(avaliacoes)
        for coluna in range(self._num_avaliacoes_salvas):
            self._definir_coluna_bloqueada(coluna, True)

        self._recalcular_destaques()


_CAMINHO_IMAGEM_MUSCULO_GORDURA = str(
    Path(__file__).resolve().parent.parent.parent / "musculogordura.png"
)

_LIMITE_MEDIDA = 300.0

_LINHAS_CIRCUNFERENCIAS = [
    ("datas", "Datas:", "data", None),
    ("ombro", "Ombro", "numero", _LIMITE_MEDIDA),
    ("torax", "Tórax", "numero", _LIMITE_MEDIDA),
    ("cintura", "Cintura", "numero", _LIMITE_MEDIDA),
    ("abdominal", "Abdominal", "numero", _LIMITE_MEDIDA),
    ("quadril", "Quadril", "numero", _LIMITE_MEDIDA),
    ("braco_e", "Braço (E)", "numero", _LIMITE_MEDIDA),
    ("braco_e_contraido", "Braço (E) Contraído", "numero", _LIMITE_MEDIDA),
    ("braco_d", "Braço (D)", "numero", _LIMITE_MEDIDA),
    ("braco_d_contraido", "Braço (D) Contraído", "numero", _LIMITE_MEDIDA),
    ("antebraco_e", "Antebraço (E)", "numero", _LIMITE_MEDIDA),
    ("antebraco_d", "Antebraço (D)", "numero", _LIMITE_MEDIDA),
    ("coxa_e", "Coxa E", "numero", _LIMITE_MEDIDA),
    ("coxa_d", "Coxa D", "numero", _LIMITE_MEDIDA),
    ("panturrilha_e", "Panturrilha E", "numero", _LIMITE_MEDIDA),
    ("panturrilha_d", "Panturrilha D", "numero", _LIMITE_MEDIDA),
]

_LIMITE_DOBRA_MM = 100.0

_LINHAS_DOBRAS_REAIS = [
    ("triceps", "Tríceps", "numero", _LIMITE_DOBRA_MM),
    ("peito", "Peito", "numero", _LIMITE_DOBRA_MM),
    ("axilar_media", "Axilar média", "numero", _LIMITE_DOBRA_MM),
    ("subescapular", "Subescapular", "numero", _LIMITE_DOBRA_MM),
    ("dobra_abdominal", "Abdominal", "numero", _LIMITE_DOBRA_MM),
    ("supra_iliaca", "Supra-iliaca", "numero", _LIMITE_DOBRA_MM),
    ("coxa_dobra", "Coxa", "numero", _LIMITE_DOBRA_MM),
]
_CHAVES_DOBRAS_7 = tuple(chave for chave, _rotulo, _tipo, _maximo in _LINHAS_DOBRAS_REAIS)
_ROTULOS_DOBRAS_7 = {chave: rotulo for chave, rotulo, _tipo, _maximo in _LINHAS_DOBRAS_REAIS}

_LINHAS_DOBRAS_COM_DATA = [("datas", "Datas:", "data", None)] + list(_LINHAS_DOBRAS_REAIS)

_LINHAS_PESO = [
    ("peso", "Peso (kg)", "numero", _LIMITE_MEDIDA),
]
_LINHAS_COMPOSICAO_CORPORAL = [
    ("datas", "Datas:", "resultado", None),
    ("massa_magra", "Massa Magra (kg)", "resultado", None),
    ("massa_gorda", "Massa Gorda (kg)", "resultado", None),
    ("percentual_gordura", "% Gordura Corporal", "resultado", None),
    ("densidade_corporal", "Densidade Corporal (g/cm³)", "resultado", None),
]

_NUM_COLUNAS_INICIAL = 1
_LARGURA_MINIMA_COLUNA_DADOS = 130
_ALTURA_LINHA_TABELA = 36
_LARGURA_ROTULO_TABELA = 190

_DATA_SENTINELA = QDate(2000, 1, 1)

_ESTILO_CAMPO_NUMERICO_NORMAL = f"""
    QLineEdit {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 2px;
        font-size: 13px;
        font-weight: 600;
        color: {Cores.TEXTO_PRIMARIO};
    }}
    QLineEdit:focus {{ background-color: {Cores.FUNDO}; border: 1px solid {Cores.AZUL_PRIMARIO}; }}
"""
_ESTILO_CAMPO_NUMERICO_ERRO = f"""
    QLineEdit {{
        background-color: {Cores.ERRO_FUNDO};
        border: 1px solid {Cores.ERRO};
        border-radius: 4px;
        padding: 2px;
        font-size: 13px;
        font-weight: 600;
        color: {Cores.TEXTO_PRIMARIO};
    }}
"""
_ESTILO_CAMPO_DATA_NORMAL = f"""
    QLineEdit {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 2px;
        font-size: 13px;
        font-weight: 600;
        color: {Cores.TEXTO_PRIMARIO};
    }}
    QLineEdit:focus {{ background-color: {Cores.FUNDO}; border: 1px solid {Cores.AZUL_PRIMARIO}; }}
"""
_ESTILO_CAMPO_DATA_ERRO = f"""
    QLineEdit {{
        background-color: {Cores.ERRO_FUNDO};
        border: 1px solid {Cores.ERRO};
        border-radius: 4px;
        padding: 2px;
        font-size: 13px;
        font-weight: 600;
        color: {Cores.TEXTO_PRIMARIO};
    }}
"""


def _marcar_campo_erro(campo: QWidget, com_erro: bool) -> None:
    if isinstance(campo, _CampoData):
        campo.setStyleSheet(_ESTILO_CAMPO_DATA_ERRO if com_erro else _ESTILO_CAMPO_DATA_NORMAL)
    else:
        campo.setStyleSheet(_ESTILO_CAMPO_NUMERICO_ERRO if com_erro else _ESTILO_CAMPO_NUMERICO_NORMAL)


def _criar_validador_numerico(maximo: float, casas_decimais: int = 1) -> QRegularExpressionValidator:
    digitos_inteiros = len(str(int(maximo)))
    padrao = QRegularExpression(
        rf"^\d{{0,{digitos_inteiros}}}([.,]\d{{0,{casas_decimais}}})?$"
    )
    return QRegularExpressionValidator(padrao)


def _criar_campo_numerico(maximo: float, *, casas_decimais: int = 1) -> QLineEdit:
    campo = QLineEdit()
    campo.setAlignment(Qt.AlignCenter)
    campo.setFrame(False)
    campo.setValidator(_criar_validador_numerico(maximo, casas_decimais))
    _marcar_campo_erro(campo, com_erro=False)
    return campo


_SVG_CALENDARIO = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="{cor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="5" width="18" height="16" rx="2"></rect>
    <line x1="16" y1="3" x2="16" y2="7"></line>
    <line x1="8" y1="3" x2="8" y2="7"></line>
    <line x1="3" y1="10" x2="21" y2="10"></line>
</svg>
"""


class _CampoData(QWidget):
    dateChanged = Signal(QDate)

    _MAX_DIGITOS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = _DATA_SENTINELA
        self._invalido = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._linha = QLineEdit()
        self._linha.setFrame(False)
        self._linha.setAlignment(Qt.AlignCenter)
        self._linha.setMaxLength(10)
        self._linha.textEdited.connect(self._aplicar_mascara)
        layout.addWidget(self._linha, stretch=1)

        self._botao_calendario = QToolButton()
        self._botao_calendario.setCursor(Qt.PointingHandCursor)
        self._botao_calendario.setAutoRaise(True)
        self._botao_calendario.setFixedSize(20, 20)
        self._botao_calendario.setIconSize(QSize(13, 13))
        self._botao_calendario.setIcon(
            _renderizar_icone(_SVG_CALENDARIO, Cores.TEXTO_SECUNDARIO, 13)
        )
        self._botao_calendario.setStyleSheet(
            "QToolButton { border: none; background: transparent; }"
        )
        self._botao_calendario.setToolTip("Abrir calendário")
        self._botao_calendario.clicked.connect(self._abrir_calendario)
        layout.addWidget(self._botao_calendario)

        self._aplicar_estilo()


    def _aplicar_mascara(self, texto: str) -> None:
        digitos = "".join(caractere for caractere in texto if caractere.isdigit())
        digitos = digitos[: self._MAX_DIGITOS]

        if len(digitos) <= 2:
            novo_texto = digitos
        elif len(digitos) <= 4:
            novo_texto = f"{digitos[0:2]}/{digitos[2:4]}"
        else:
            novo_texto = f"{digitos[0:2]}/{digitos[2:4]}/{digitos[4:8]}"

        self._linha.setText(novo_texto)
        self._linha.setCursorPosition(len(novo_texto))

        if len(digitos) == self._MAX_DIGITOS:
            dia, mes, ano = int(digitos[0:2]), int(digitos[2:4]), int(digitos[4:8])
            candidata = QDate(ano, mes, dia)
            if candidata.isValid():
                self._invalido = False
                self._definir_data_interna(candidata)
            else:
                self._invalido = True
                self._definir_data_interna(_DATA_SENTINELA)
        else:
            self._invalido = False
            self._definir_data_interna(_DATA_SENTINELA)

        self._aplicar_estilo()

    def _definir_data_interna(self, data: QDate) -> None:
        if data != self._data:
            self._data = data
            self.dateChanged.emit(data)


    def date(self) -> QDate:
        return self._data

    def setDate(self, data: QDate) -> None:
        self._invalido = False
        self._linha.setText("" if data == _DATA_SENTINELA else data.toString("dd/MM/yyyy"))
        self._definir_data_interna(data)
        self._aplicar_estilo()

    def setFocus(self, *args) -> None:
        self._linha.setFocus()

    def setStyleSheet(self, estilo: str) -> None:
        self._linha.setStyleSheet(estilo)

    def _aplicar_estilo(self) -> None:
        _marcar_campo_erro(self, com_erro=self._invalido)


    def _abrir_calendario(self) -> None:
        calendario = QCalendarWidget(self)
        calendario.setWindowFlags(Qt.Popup)
        calendario.setGridVisible(True)
        calendario.setSelectedDate(
            self._data if self._data != _DATA_SENTINELA else QDate.currentDate()
        )
        calendario.clicked.connect(
            lambda data, cal=calendario: self._selecionar_do_calendario(data, cal)
        )
        calendario.move(self.mapToGlobal(self.rect().bottomLeft()))
        calendario.show()

    def _selecionar_do_calendario(self, data: QDate, calendario: QCalendarWidget) -> None:
        self.setDate(data)
        calendario.close()


    def definir_somente_leitura(self, somente_leitura: bool) -> None:
        self._linha.setReadOnly(somente_leitura)
        self._botao_calendario.setEnabled(not somente_leitura)


def _data_local_hoje() -> QDate:
    return QDate.currentDate()


def _criar_campo_data() -> _CampoData:
    campo = _CampoData()
    campo.setDate(_data_local_hoje())
    return campo


def _criar_label_resultado() -> QLabel:
    label = QLabel("—")
    label.setAlignment(Qt.AlignCenter)
    label.setStyleSheet(
        f"background: transparent; border: none; color: {Cores.TEXTO_PRIMARIO}; "
        f"font-size: 13px; font-weight: 700;"
    )
    return label


def _criar_widget_celula(tipo: str, maximo: Optional[float]) -> QWidget:
    if tipo == "data":
        return _criar_campo_data()
    if tipo == "resultado":
        return _criar_label_resultado()
    return _criar_campo_numerico(maximo)


def _criar_tabela_widgets(especificacoes, num_colunas: int = _NUM_COLUNAS_INICIAL):
    rotulos = [rotulo for _chave, rotulo, _tipo, _maximo in especificacoes]
    tabela = QTableWidget(len(especificacoes), num_colunas)
    tabela.setVerticalHeaderLabels(rotulos)
    tabela.horizontalHeader().hide()
    tabela.verticalHeader().setFixedWidth(_LARGURA_ROTULO_TABELA)
    tabela.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    tabela.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
    tabela.verticalHeader().setDefaultSectionSize(_ALTURA_LINHA_TABELA)
    tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    tabela.horizontalHeader().setMinimumSectionSize(_LARGURA_MINIMA_COLUNA_DADOS)
    tabela.setSelectionMode(QTableWidget.NoSelection)
    tabela.setEditTriggers(QTableWidget.NoEditTriggers)
    tabela.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    tabela.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    tabela.setStyleSheet(
        f"""
        QTableWidget {{
            background-color: {Cores.SUPERFICIE};
            gridline-color: {Cores.BORDA};
            border: 1px solid {Cores.BORDA};
        }}
        QHeaderView::section {{
            background-color: {Cores.FUNDO};
            color: {Cores.TEXTO_PRIMARIO};
            font-weight: 600;
            font-size: 12px;
            padding: 0 10px;
            border: none;
            border-right: 1px solid {Cores.BORDA};
            border-bottom: 1px solid {Cores.BORDA};
        }}
        """
    )

    matriz: Dict[str, list] = {}
    for linha, (chave, _rotulo, tipo, maximo) in enumerate(especificacoes):
        widgets_linha = []
        for coluna in range(num_colunas):
            widget = _criar_widget_celula(tipo, maximo)
            tabela.setCellWidget(linha, coluna, widget)
            widgets_linha.append(widget)
        matriz[chave] = widgets_linha

    tabela.setFixedHeight(tabela.verticalHeader().length() + 2 * tabela.frameWidth() + 2)
    return tabela, matriz


def _adicionar_coluna_tabela(
    tabela: QTableWidget, matriz: Dict[str, list], especificacoes
) -> list:
    nova_coluna = tabela.columnCount()
    tabela.insertColumn(nova_coluna)
    widgets_criados = []
    for linha, (chave, _rotulo, tipo, maximo) in enumerate(especificacoes):
        widget = _criar_widget_celula(tipo, maximo)
        tabela.setCellWidget(linha, nova_coluna, widget)
        matriz[chave].append(widget)
        widgets_criados.append((chave, widget))
    return widgets_criados


def _remover_colunas_extras_tabela(tabela: QTableWidget, matriz: Dict[str, list]) -> None:
    while tabela.columnCount() > 1:
        tabela.removeColumn(tabela.columnCount() - 1)
    for lista_widgets in matriz.values():
        del lista_widgets[1:]


def _valor_data(campo: _CampoData) -> Optional[str]:
    if campo.date() == _DATA_SENTINELA:
        return None
    return campo.date().toString("dd/MM/yyyy")


def _qdate_de_texto(texto: Optional[str]) -> Optional[QDate]:
    if not texto:
        return None
    partes = texto.split("/")
    if len(partes) != 3:
        return None
    try:
        dia, mes, ano = (int(parte) for parte in partes)
        data = QDate(ano, mes, dia)
    except ValueError:
        return None
    return data if data.isValid() else None


def _formatar_numero(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _limpar_widget(widget: QWidget) -> None:
    if isinstance(widget, _CampoData):
        widget.setDate(_data_local_hoje())
    elif isinstance(widget, QLabel):
        widget.setText("—")
        widget.setToolTip("")
    else:
        widget.clear()


def _definir_celula_somente_leitura(widget: QWidget, somente_leitura: bool) -> None:
    if isinstance(widget, _CampoData):
        widget.definir_somente_leitura(somente_leitura)
    elif isinstance(widget, QLineEdit):
        widget.setReadOnly(somente_leitura)


def _criar_card_tabela(
    titulo: str, *widgets: QWidget, widget_extra_cabecalho: Optional[QWidget] = None
) -> QFrame:
    cartao = _criar_cartao()
    layout = QVBoxLayout(cartao)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    if widget_extra_cabecalho is None:
        layout.addWidget(_cabecalho_bloco_medidas(titulo, centralizado=True))
    else:
        cabecalho = QFrame()
        cabecalho.setStyleSheet(
            f"background-color: {Cores.AZUL_ESCURO}; border: none; "
            f"border-top-left-radius: 14px; border-top-right-radius: 14px;"
        )
        layout_cabecalho = QHBoxLayout(cabecalho)
        layout_cabecalho.setContentsMargins(20, 10, 14, 10)
        titulo_label = QLabel(titulo)
        titulo_label.setStyleSheet(
            f"background: transparent; border: none; color: white; "
            f"font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 700;"
        )
        layout_cabecalho.addStretch(1)
        layout_cabecalho.addWidget(titulo_label)
        layout_cabecalho.addStretch(1)
        layout_cabecalho.addWidget(widget_extra_cabecalho, alignment=Qt.AlignVCenter)
        layout.addWidget(cabecalho)

    corpo = QWidget()
    corpo.setStyleSheet("background: transparent;")
    layout_corpo = QVBoxLayout(corpo)
    layout_corpo.setContentsMargins(20, 16, 20, 16)
    layout_corpo.setSpacing(14)
    for widget in widgets:
        layout_corpo.addWidget(widget)
    layout.addWidget(corpo)

    return cartao


class _ImagemProporcional(QLabel):
    def __init__(self, caminho_imagem: str, parent=None):
        super().__init__(parent)
        self._pixmap_original = QPixmap(caminho_imagem)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(80, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._atualizar_pixmap()

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self._atualizar_pixmap()

    def _atualizar_pixmap(self) -> None:
        if self._pixmap_original.isNull():
            return
        self.setPixmap(
            self._pixmap_original.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )


_CONSTANTES_JP7 = {
    "Masculino": {
        "intercepto": 1.112,
        "coef_s": 0.00043499,
        "coef_s2": 0.00000055,
        "coef_idade": 0.00028826,
    },
    "Feminino": {
        "intercepto": 1.097,
        "coef_s": 0.00046971,
        "coef_s2": 0.00000056,
        "coef_idade": 0.00012828,
    },
}


def _calcular_composicao_jp7(
    sexo: Optional[str],
    idade: Optional[int],
    peso: Optional[float],
    dobras: Dict[str, Optional[float]],
) -> Optional[dict]:
    constantes = _CONSTANTES_JP7.get(sexo)
    if constantes is None or idade is None or peso is None:
        return None
    valores_dobras = [dobras.get(chave) for chave in _CHAVES_DOBRAS_7]
    if any(valor is None for valor in valores_dobras):
        return None

    soma = sum(valores_dobras)
    densidade = (
        constantes["intercepto"]
        - constantes["coef_s"] * soma
        + constantes["coef_s2"] * (soma ** 2)
        - constantes["coef_idade"] * idade
    )
    percentual = (495 / densidade) - 450
    percentual_protegido = max(0.0, percentual)
    massa_gorda = peso * (percentual_protegido / 100)
    massa_magra = peso - massa_gorda
    return {
        "soma": soma,
        "densidade": densidade,
        "percentual": percentual,
        "percentual_protegido": percentual_protegido,
        "massa_gorda": massa_gorda,
        "massa_magra": massa_magra,
    }


class ComposicaoCorporalStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._sexo: Optional[str] = None
        self._idade: Optional[int] = None

        self._num_colunas = _NUM_COLUNAS_INICIAL
        self._num_avaliacoes_salvas = 0

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        cartao = _criar_cartao()
        cartao.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout_cartao = QHBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(24)

        painel_esquerdo = QWidget()
        painel_esquerdo.setStyleSheet("background: transparent;")
        coluna_esquerda = QVBoxLayout(painel_esquerdo)
        coluna_esquerda.setContentsMargins(0, 0, 4, 0)
        coluna_esquerda.setSpacing(28)

        self._label_erro = QLabel("")
        self._label_erro.setWordWrap(True)
        self._label_erro.setStyleSheet(
            f"""
            background-color: {Cores.ERRO_FUNDO};
            color: {Cores.ERRO};
            border-radius: 8px;
            padding: 10px 14px;
            font-size: {Fontes.TAMANHO_LABEL}px;
            """
        )
        self._label_erro.hide()
        coluna_esquerda.addWidget(self._label_erro)

        self._tabela_dobras_reais, self._campos_dobras_reais = _criar_tabela_widgets(
            _LINHAS_DOBRAS_COM_DATA
        )

        self._botao_nova_avaliacao = QPushButton("+")
        self._botao_nova_avaliacao.setCursor(Qt.PointingHandCursor)
        self._botao_nova_avaliacao.setFixedSize(28, 28)
        self._botao_nova_avaliacao.setToolTip("Adicionar nova avaliação")
        self._botao_nova_avaliacao.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 35);
                color: white;
                border: 1px solid rgba(255, 255, 255, 110);
                border-radius: 14px;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 70); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 110); }
            """
        )
        self._botao_nova_avaliacao.clicked.connect(self._adicionar_nova_avaliacao)

        self._tabela_peso, self._campos_peso = _criar_tabela_widgets(_LINHAS_PESO)

        divisor_peso = QFrame()
        divisor_peso.setFixedHeight(1)
        divisor_peso.setStyleSheet(f"background-color: {Cores.BORDA};")

        bloco_dobras = _criar_card_tabela(
            "Dobras Cutâneas (mm)",
            self._tabela_dobras_reais,
            divisor_peso,
            self._tabela_peso,
            widget_extra_cabecalho=self._botao_nova_avaliacao,
        )
        coluna_esquerda.addWidget(bloco_dobras)

        self._tabela_composicao, self._campos_composicao = _criar_tabela_widgets(
            _LINHAS_COMPOSICAO_CORPORAL
        )
        bloco_composicao = _criar_card_tabela("Composição corporal", self._tabela_composicao)
        coluna_esquerda.addWidget(bloco_composicao)

        coluna_esquerda.addStretch(1)

        self._tabelas_reavaliacao = (
            self._tabela_dobras_reais,
            self._tabela_peso,
            self._tabela_composicao,
        )
        for tabela in self._tabelas_reavaliacao:
            tabela.horizontalScrollBar().valueChanged.connect(
                lambda valor, origem=tabela: self._sincronizar_scroll_horizontal(origem, valor)
            )

        coluna_inicial = _NUM_COLUNAS_INICIAL - 1
        self._conectar_coluna_calculo(
            [(chave, self._campos_dobras_reais[chave][coluna_inicial])
             for chave, _r, _t, _m in _LINHAS_DOBRAS_COM_DATA],
            [(chave, self._campos_peso[chave][coluna_inicial]) for chave, _r, _t, _m in _LINHAS_PESO],
        )

        self._campos_peso["peso"][0].textChanged.connect(self._limpar_erro_validacao)
        self._campos_dobras_reais["datas"][0].dateChanged.connect(self._limpar_erro_validacao)

        self._recalcular_composicao()

        rolagem_esquerda = QScrollArea()
        rolagem_esquerda.setWidget(painel_esquerdo)
        rolagem_esquerda.setWidgetResizable(True)
        rolagem_esquerda.setFrameShape(QFrame.NoFrame)
        rolagem_esquerda.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        rolagem_esquerda.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        rolagem_esquerda.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        layout_cartao.addWidget(rolagem_esquerda, stretch=3)

        self._imagem_musculo_gordura = _ImagemProporcional(_CAMINHO_IMAGEM_MUSCULO_GORDURA)
        layout_cartao.addWidget(self._imagem_musculo_gordura, stretch=2)

        layout_raiz.addWidget(cartao, stretch=1)

    def ao_entrar(self, dados_coletados: dict) -> None:
        self._sexo = dados_coletados.get("sexo")
        self._idade = dados_coletados.get("idade")
        self._recalcular_composicao()


    def _conectar_coluna_calculo(self, widgets_dobras, widgets_peso) -> None:
        for chave, widget in widgets_dobras:
            if chave == "datas":
                widget.dateChanged.connect(self._recalcular_composicao)
            else:
                widget.textChanged.connect(self._recalcular_composicao)
        for _chave, widget in widgets_peso:
            widget.textChanged.connect(self._recalcular_composicao)

    def _sincronizar_scroll_horizontal(self, origem: QTableWidget, valor: int) -> None:
        for tabela in self._tabelas_reavaliacao:
            if tabela is origem:
                continue
            barra = tabela.horizontalScrollBar()
            if barra.value() != valor:
                barra.blockSignals(True)
                barra.setValue(valor)
                barra.blockSignals(False)

    def _adicionar_nova_avaliacao(self) -> None:
        novos_dobras = _adicionar_coluna_tabela(
            self._tabela_dobras_reais, self._campos_dobras_reais, _LINHAS_DOBRAS_COM_DATA
        )
        novos_peso = _adicionar_coluna_tabela(self._tabela_peso, self._campos_peso, _LINHAS_PESO)
        _adicionar_coluna_tabela(
            self._tabela_composicao, self._campos_composicao, _LINHAS_COMPOSICAO_CORPORAL
        )
        self._conectar_coluna_calculo(novos_dobras, novos_peso)

        self._num_colunas += 1
        self._recalcular_composicao()

        barra = self._tabela_dobras_reais.horizontalScrollBar()
        barra.setValue(barra.maximum())

    def avaliacoes_ja_salvas(self) -> int:
        return self._num_avaliacoes_salvas

    def _definir_coluna_bloqueada(self, coluna: int, bloqueada: bool) -> None:
        for chave, _rotulo, _tipo, _maximo in _LINHAS_DOBRAS_COM_DATA:
            _definir_celula_somente_leitura(self._campos_dobras_reais[chave][coluna], bloqueada)
        for chave, _rotulo, _tipo, _maximo in _LINHAS_PESO:
            _definir_celula_somente_leitura(self._campos_peso[chave][coluna], bloqueada)

    def _recalcular_composicao(self) -> None:
        campos_datas = self._campos_dobras_reais["datas"]
        campos_peso = self._campos_peso["peso"]
        labels_data = self._campos_composicao["datas"]
        labels_magra = self._campos_composicao["massa_magra"]
        labels_gorda = self._campos_composicao["massa_gorda"]
        labels_percentual = self._campos_composicao["percentual_gordura"]
        labels_densidade = self._campos_composicao["densidade_corporal"]
        grupos_resultado = (labels_magra, labels_gorda, labels_percentual, labels_densidade)

        for coluna in range(self._num_colunas):
            data = _valor_data(campos_datas[coluna])
            labels_data[coluna].setText(data if data else "—")

            peso = _texto_para_numero(campos_peso[coluna].text())
            dobras = {
                chave: _texto_para_numero(self._campos_dobras_reais[chave][coluna].text())
                for chave in _CHAVES_DOBRAS_7
            }

            faltando = []
            if not self._sexo:
                faltando.append("o sexo (Etapa 1)")
            elif self._sexo not in _CONSTANTES_JP7:
                faltando.append(
                    f'um sexo Masculino ou Feminino na Etapa 1 (o protocolo de '
                    f'Jackson & Pollock não é definido para "{self._sexo}")'
                )
            if not self._idade:
                faltando.append("a idade (Etapa 1)")
            if peso is None:
                faltando.append("o peso")
            for chave in _CHAVES_DOBRAS_7:
                if dobras[chave] is None:
                    faltando.append(f"a dobra cutânea {_ROTULOS_DOBRAS_7[chave]}")

            if faltando:
                itens = (
                    ", ".join(faltando[:-1]) + " e " + faltando[-1]
                    if len(faltando) > 1
                    else faltando[0]
                )
                dica = f"Preencha {itens} para calcular a composição corporal."
                for grupo in grupos_resultado:
                    grupo[coluna].setText("—")
                    grupo[coluna].setToolTip(dica)
                continue

            resultado = _calcular_composicao_jp7(self._sexo, self._idade, peso, dobras)

            labels_magra[coluna].setText(f"{_formatar_numero(resultado['massa_magra'], 2)} kg")
            labels_gorda[coluna].setText(f"{_formatar_numero(resultado['massa_gorda'], 2)} kg")
            labels_percentual[coluna].setText(
                f"{_formatar_numero(resultado['percentual_protegido'], 2)}%"
            )
            labels_densidade[coluna].setText(_formatar_numero(resultado["densidade"], 4))
            if resultado["percentual"] < 0:
                dica_percentual = (
                    f"% Gordura calculada pela fórmula: "
                    f"{_formatar_numero(resultado['percentual'], 2)}% -- "
                    f"protegida para 0% nos cálculos de massa (nunca negativa)."
                )
            else:
                dica_percentual = ""
            for grupo in grupos_resultado:
                grupo[coluna].setToolTip("")
            labels_percentual[coluna].setToolTip(dica_percentual)


    def _limpar_erro_validacao(self) -> None:
        self._label_erro.hide()
        _marcar_campo_erro(self._campos_dobras_reais["datas"][0], com_erro=False)
        _marcar_campo_erro(self._campos_peso["peso"][0], com_erro=False)

    def _mostrar_erro_validacao(self, mensagem: str, campo: QWidget) -> None:
        self._label_erro.setText(mensagem)
        self._label_erro.show()
        _marcar_campo_erro(campo, com_erro=True)
        campo.setFocus()

    def obter_dados_validados(self):
        self._limpar_erro_validacao()

        campo_data = self._campos_dobras_reais["datas"][0]
        if campo_data.date() == _DATA_SENTINELA:
            self._mostrar_erro_validacao("Informe uma data válida.", campo_data)
            return None

        campo_peso = self._campos_peso["peso"][0]
        if _texto_para_numero(campo_peso.text()) is None:
            self._mostrar_erro_validacao("Preencha o campo Peso.", campo_peso)
            return None

        def extrair_numeros(matriz, chave):
            return [_texto_para_numero(w.text()) for w in matriz[chave]]

        def extrair_datas(matriz):
            return [_valor_data(w) for w in matriz["datas"]]

        dobras_cutaneas = {"datas": extrair_datas(self._campos_dobras_reais)}
        for chave in _CHAVES_DOBRAS_7:
            dobras_cutaneas[chave] = extrair_numeros(self._campos_dobras_reais, chave)

        peso = extrair_numeros(self._campos_peso, "peso")
        massa_magra = []
        massa_gorda = []
        percentual_gordura = []
        percentual_gordura_bruto = []
        densidade_corporal = []
        soma_dobras = []
        for coluna in range(self._num_colunas):
            p = peso[coluna]
            dobras_coluna = {chave: dobras_cutaneas[chave][coluna] for chave in _CHAVES_DOBRAS_7}
            resultado = _calcular_composicao_jp7(self._sexo, self._idade, p, dobras_coluna)
            if resultado is None:
                massa_magra.append(None)
                massa_gorda.append(None)
                percentual_gordura.append(None)
                percentual_gordura_bruto.append(None)
                densidade_corporal.append(None)
                soma_dobras.append(None)
            else:
                massa_magra.append(round(resultado["massa_magra"], 2))
                massa_gorda.append(round(resultado["massa_gorda"], 2))
                percentual_gordura.append(round(resultado["percentual_protegido"], 2))
                percentual_gordura_bruto.append(round(resultado["percentual"], 2))
                densidade_corporal.append(round(resultado["densidade"], 4))
                soma_dobras.append(round(resultado["soma"], 2))

        composicao_corporal = {
            "datas": dobras_cutaneas["datas"],
            "massa_magra": massa_magra,
            "massa_gorda": massa_gorda,
            "percentual_gordura": percentual_gordura,
            "percentual_gordura_bruto": percentual_gordura_bruto,
            "densidade_corporal": densidade_corporal,
            "soma_dobras": soma_dobras,
        }

        return {
            "dobras_cutaneas": dobras_cutaneas,
            "peso": peso,
            "composicao_corporal": composicao_corporal,
        }

    def limpar(self) -> None:
        for tabela, matriz in zip(
            self._tabelas_reavaliacao,
            (
                self._campos_dobras_reais,
                self._campos_peso,
                self._campos_composicao,
            ),
        ):
            _remover_colunas_extras_tabela(tabela, matriz)
        self._num_colunas = _NUM_COLUNAS_INICIAL
        self._num_avaliacoes_salvas = 0

        for matriz in (
            self._campos_dobras_reais,
            self._campos_peso,
            self._campos_composicao,
        ):
            for widgets in matriz.values():
                for widget in widgets:
                    _limpar_widget(widget)
        self._definir_coluna_bloqueada(0, False)
        self._limpar_erro_validacao()

    def carregar_avaliacoes(self, avaliacoes: list) -> None:
        for tabela, matriz in zip(
            self._tabelas_reavaliacao,
            (self._campos_dobras_reais, self._campos_peso, self._campos_composicao),
        ):
            _remover_colunas_extras_tabela(tabela, matriz)
        self._num_colunas = _NUM_COLUNAS_INICIAL
        self._num_avaliacoes_salvas = 0

        for matriz in (self._campos_dobras_reais, self._campos_peso, self._campos_composicao):
            for widgets in matriz.values():
                for widget in widgets:
                    _limpar_widget(widget)
        self._definir_coluna_bloqueada(0, False)
        self._limpar_erro_validacao()

        if not avaliacoes:
            self._recalcular_composicao()
            return

        while self._num_colunas < len(avaliacoes):
            novos_dobras = _adicionar_coluna_tabela(
                self._tabela_dobras_reais, self._campos_dobras_reais, _LINHAS_DOBRAS_COM_DATA
            )
            novos_peso = _adicionar_coluna_tabela(self._tabela_peso, self._campos_peso, _LINHAS_PESO)
            _adicionar_coluna_tabela(
                self._tabela_composicao, self._campos_composicao, _LINHAS_COMPOSICAO_CORPORAL
            )
            self._conectar_coluna_calculo(novos_dobras, novos_peso)
            self._num_colunas += 1

        for coluna, avaliacao in enumerate(avaliacoes):
            data_valida = _qdate_de_texto(avaliacao.get("data"))
            self._campos_dobras_reais["datas"][coluna].setDate(data_valida or _DATA_SENTINELA)

            for chave in _CHAVES_DOBRAS_7:
                valor = avaliacao.get(chave)
                campo = self._campos_dobras_reais[chave][coluna]
                campo.setText("" if valor is None else _formatar_numero(valor))

            peso_valor = avaliacao.get("peso")
            self._campos_peso["peso"][coluna].setText(
                "" if peso_valor is None else _formatar_numero(peso_valor)
            )

        self._num_avaliacoes_salvas = len(avaliacoes)
        for coluna in range(self._num_avaliacoes_salvas):
            self._definir_coluna_bloqueada(coluna, True)

        self._recalcular_composicao()


_SLOTS_FOTOS = [
    ("foto_frente", "Imagem de frente"),
    ("foto_costas", "Imagem de costa"),
    ("foto_lado_direito", "Imagem do lado direito"),
    ("foto_lado_esquerdo", "Imagem do lado esquerdo"),
]

_FILTRO_ARQUIVOS_IMAGEM = "Imagens (*.png *.jpg *.jpeg *.webp)"


class _AreaFotoClicavel(QLabel):
    clicada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._caminho: Optional[str] = None
        self._pixmap_original: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(60, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._atualizar_conteudo()

    @property
    def caminho_imagem(self) -> Optional[str]:
        return self._caminho

    def definir_imagem(self, caminho: Optional[str]) -> None:
        if not caminho:
            self._caminho = None
            self._pixmap_original = None
            self._atualizar_conteudo()
            return

        pixmap = QPixmap(caminho)
        if pixmap.isNull():
            return
        self._caminho = caminho
        self._pixmap_original = pixmap
        self._atualizar_conteudo()

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self._atualizar_conteudo()

    def mousePressEvent(self, evento) -> None:
        super().mousePressEvent(evento)
        self.clicada.emit()

    def _atualizar_conteudo(self) -> None:
        if self._pixmap_original is None:
            self.clear()
            self.setText("+")
            self.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {Cores.SUPERFICIE};
                    border: 1px dashed {Cores.BORDA};
                    border-radius: 10px;
                    color: {Cores.TEXTO_SECUNDARIO};
                    font-size: 34px;
                    font-weight: 300;
                }}
                """
            )
        else:
            self.setText("")
            self.setPixmap(
                self._pixmap_original.scaled(
                    self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            self.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {Cores.SUPERFICIE};
                    border: 1px solid {Cores.BORDA};
                    border-radius: 10px;
                }}
                """
            )


class _CardFotoAluno(QFrame):
    solicitar_imagem = Signal()

    def __init__(self, titulo: Optional[str], parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {Cores.FUNDO};
                border: 1px solid {Cores.BORDA};
                border-radius: 12px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        if titulo:
            label_titulo = QLabel(titulo)
            label_titulo.setAlignment(Qt.AlignCenter)
            label_titulo.setStyleSheet(
                f"background: transparent; border: none; "
                f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_LABEL}px; font-weight: 600;"
            )
            layout.addWidget(label_titulo)

        self._area = _AreaFotoClicavel()
        self._area.clicada.connect(self.solicitar_imagem.emit)
        layout.addWidget(self._area, stretch=1)

    @property
    def caminho_imagem(self) -> Optional[str]:
        return self._area.caminho_imagem

    def definir_imagem(self, caminho: Optional[str]) -> None:
        self._area.definir_imagem(caminho)


_RAZAO_LARGURA_ALTURA_CARD_FOTO = 4 / 5
_ALTURA_MINIMA_CARD_FOTO = 100
_ALTURA_MAXIMA_CARD_FOTO = 420
_ESPACAMENTO_GRADE_FOTOS = 18
_MARGEM_PAINEL_FOTOS = 20
_RAZAO_ALTURA_BOTAO_NOVA_SESSAO = 0.65
_MARGEM_TOPO_SESSAO_FOTOS = 12
_ESPACO_CABECALHO_SESSAO_FOTOS = 8


class _PainelFotosAluno(QFrame):
    tamanho_card_mudou = Signal(QSize)

    def __init__(self, numero: int, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {Cores.SUPERFICIE};
                border: 1px solid {Cores.BORDA};
                border-radius: 14px;
            }}
            """
        )
        self.bloqueada = False

        self.cards: Dict[str, _CardFotoAluno] = {
            chave: _CardFotoAluno(titulo) for chave, titulo in _SLOTS_FOTOS
        }

        self._cabecalho = QWidget()
        self._cabecalho.setStyleSheet("background: transparent; border: none;")
        layout_cabecalho = QHBoxLayout(self._cabecalho)
        layout_cabecalho.setContentsMargins(0, 0, 0, 0)
        layout_cabecalho.setSpacing(8)
        titulo = QLabel(f"Sessão {numero}")
        titulo.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_LABEL}px; font-weight: 700;"
        )
        layout_cabecalho.addWidget(titulo)
        layout_cabecalho.addStretch(1)
        rotulo_data = QLabel("Data:")
        rotulo_data.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: 13px; font-weight: 600;"
        )
        layout_cabecalho.addWidget(rotulo_data)
        self.campo_data = _criar_campo_data()
        self.campo_data._linha.setPlaceholderText("dd/mm/aaaa")
        self.campo_data.setFixedWidth(120)
        layout_cabecalho.addWidget(self.campo_data)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            _MARGEM_PAINEL_FOTOS, _MARGEM_TOPO_SESSAO_FOTOS,
            _MARGEM_PAINEL_FOTOS, _MARGEM_PAINEL_FOTOS,
        )
        layout.setSpacing(_ESPACO_CABECALHO_SESSAO_FOTOS)
        layout.addWidget(self._cabecalho)
        self._grade = QGridLayout()
        self._grade.setContentsMargins(0, 0, 0, 0)
        self._grade.setHorizontalSpacing(_ESPACAMENTO_GRADE_FOTOS)
        self._grade.setVerticalSpacing(_ESPACAMENTO_GRADE_FOTOS)
        for indice, card in enumerate(self.cards.values()):
            self._grade.addWidget(card, indice // 2, indice % 2)
        layout.addLayout(self._grade)

    def definir_bloqueada(self, bloqueada: bool) -> None:
        self.bloqueada = bloqueada
        self.campo_data.definir_somente_leitura(bloqueada)
        for card in self.cards.values():
            card._area.setCursor(Qt.ArrowCursor if bloqueada else Qt.PointingHandCursor)

    def dados(self) -> dict:
        dados = {"data": _valor_data(self.campo_data)}
        dados.update({chave: card.caminho_imagem for chave, card in self.cards.items()})
        return dados

    def ajustar(self, altura_total: int) -> None:
        altura_disponivel = (
            altura_total - 2 * self.frameWidth()
            - _MARGEM_TOPO_SESSAO_FOTOS - _MARGEM_PAINEL_FOTOS
            - self._cabecalho.sizeHint().height() - _ESPACO_CABECALHO_SESSAO_FOTOS
            - self._grade.verticalSpacing()
        )
        altura_celula = altura_disponivel / 2
        if altura_celula <= 0:
            return

        altura = max(altura_celula, _ALTURA_MINIMA_CARD_FOTO)
        altura = min(altura, _ALTURA_MAXIMA_CARD_FOTO)
        largura = altura * _RAZAO_LARGURA_ALTURA_CARD_FOTO

        tamanho = QSize(int(largura), int(altura))
        for card in self.cards.values():
            card.setFixedSize(tamanho)

        espaco_h = self._grade.horizontalSpacing()
        largura_painel = int(largura) * 2 + espaco_h + 2 * _MARGEM_PAINEL_FOTOS
        self.setFixedWidth(largura_painel)
        self.tamanho_card_mudou.emit(tamanho)


class _AreaSessoesFotos(QScrollArea):
    redimensionada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.verticalScrollBar().valueChanged.connect(
            lambda valor: valor and self.verticalScrollBar().setValue(0)
        )

    def wheelEvent(self, evento) -> None:
        delta = evento.angleDelta().y() or evento.angleDelta().x()
        barra = self.horizontalScrollBar()
        barra.setValue(barra.value() - delta)
        evento.accept()

    def altura_sessoes(self) -> int:
        return self.height() - self.horizontalScrollBar().sizeHint().height()

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self.redimensionada.emit()


class ImagensAlunoStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(12)

        self._label_erro = QLabel("")
        self._label_erro.setWordWrap(True)
        self._label_erro.setStyleSheet(
            f"""
            background-color: {Cores.ERRO_FUNDO};
            color: {Cores.ERRO};
            border-radius: 8px;
            padding: 10px 14px;
            font-size: {Fontes.TAMANHO_LABEL}px;
            """
        )
        self._label_erro.hide()
        layout_raiz.addWidget(self._label_erro)

        self._sessoes: list = []
        self._num_sessoes_salvas = 0

        conteudo = QWidget()
        conteudo.setStyleSheet("background: transparent;")
        self._layout_sessoes = QHBoxLayout(conteudo)
        self._layout_sessoes.setContentsMargins(0, 0, 0, 0)
        self._layout_sessoes.setSpacing(_ESPACAMENTO_GRADE_FOTOS)
        self._layout_sessoes.addStretch(1)
        self._botao_nova_sessao = _CardFotoAluno(None)
        self._botao_nova_sessao.setToolTip("Adicionar nova sessão de fotos")
        self._botao_nova_sessao.solicitar_imagem.connect(self._adicionar_sessao_clicado)
        self._botao_nova_sessao._area.setMinimumSize(1, 1)
        self._layout_sessoes.addWidget(self._botao_nova_sessao, 0, Qt.AlignVCenter)
        self._layout_sessoes.addStretch(1)

        self._area = _AreaSessoesFotos()
        self._area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._area.setWidgetResizable(True)
        self._area.setWidget(conteudo)
        self._area.redimensionada.connect(self._ajustar_sessoes)
        layout_raiz.addWidget(self._area, 1)

        self._nova_sessao()


    def _nova_sessao(self) -> _PainelFotosAluno:
        sessao = _PainelFotosAluno(len(self._sessoes) + 1)
        for chave, card in sessao.cards.items():
            card.solicitar_imagem.connect(
                lambda sessao=sessao, chave=chave: self._selecionar_imagem(sessao, chave)
            )
        sessao.tamanho_card_mudou.connect(self._ajustar_botao_nova_sessao)
        self._layout_sessoes.insertWidget(self._layout_sessoes.count() - 2, sessao)
        self._sessoes.append(sessao)
        sessao.ajustar(self._area.altura_sessoes())
        return sessao

    def _ajustar_sessoes(self) -> None:
        altura = self._area.altura_sessoes()
        for sessao in self._sessoes:
            sessao.ajustar(altura)

    def _adicionar_sessao_clicado(self) -> None:
        self._nova_sessao()
        self._limpar_erro()
        barra = self._area.horizontalScrollBar()
        QTimer.singleShot(0, lambda: barra.setValue(barra.maximum()))

    def _ajustar_botao_nova_sessao(self, tamanho_card: QSize) -> None:
        altura = int(tamanho_card.height() * _RAZAO_ALTURA_BOTAO_NOVA_SESSAO)
        self._botao_nova_sessao.setFixedSize(
            int(altura * _RAZAO_LARGURA_ALTURA_CARD_FOTO), altura
        )

    def _remover_sessoes(self) -> None:
        for sessao in self._sessoes:
            self._layout_sessoes.removeWidget(sessao)
            sessao.deleteLater()
        self._sessoes = []
        self._num_sessoes_salvas = 0
        self._limpar_erro()

    def _selecionar_imagem(self, sessao: _PainelFotosAluno, chave: str) -> None:
        if sessao.bloqueada:
            return
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar imagem", "", _FILTRO_ARQUIVOS_IMAGEM
        )
        if caminho:
            sessao.cards[chave].definir_imagem(caminho)


    def _limpar_erro(self) -> None:
        self._label_erro.hide()
        for sessao in self._sessoes:
            _marcar_campo_erro(sessao.campo_data, com_erro=False)

    def avaliacoes_ja_salvas(self) -> int:
        return self._num_sessoes_salvas

    def obter_dados_validados(self):
        self._limpar_erro()
        for numero, sessao in enumerate(self._sessoes, start=1):
            if sessao.bloqueada:
                continue
            dados = sessao.dados()
            tem_foto = any(dados[chave] for chave, _ in _SLOTS_FOTOS)
            if tem_foto and dados["data"] is None:
                self._label_erro.setText(f"Informe a data da Sessão {numero}.")
                self._label_erro.show()
                _marcar_campo_erro(sessao.campo_data, com_erro=True)
                self._area.ensureWidgetVisible(sessao)
                sessao.campo_data.setFocus()
                return None
        return {"sessoes_fotos": [sessao.dados() for sessao in self._sessoes]}

    def limpar(self) -> None:
        self._remover_sessoes()
        self._nova_sessao()

    def carregar_sessoes(self, sessoes: list) -> None:
        self._remover_sessoes()
        for salva in sessoes:
            sessao = self._nova_sessao()
            sessao.campo_data.setDate(_qdate_de_texto(salva.get("data")) or _DATA_SENTINELA)
            for chave, card in sessao.cards.items():
                card.definir_imagem(salva.get(chave))
            sessao.definir_bloqueada(True)
        self._num_sessoes_salvas = len(sessoes)
        if not sessoes:
            self._nova_sessao()


def _sessoes_fotos_para_banco(sessoes: list, a_partir_de: int = 0) -> list:
    return [
        sessao for indice, sessao in enumerate(sessoes)
        if indice >= a_partir_de and any(sessao.get(chave) for chave, _ in _SLOTS_FOTOS)
    ]


def _avaliacoes_circunferencias_para_banco(circunferencias: dict, a_partir_de: int = 0) -> list:
    datas = circunferencias.get("datas", [])
    avaliacoes = []
    for indice, data in enumerate(datas):
        if indice < a_partir_de:
            continue
        linha = {"data": data}
        for chave, _rotulo, tipo, _maximo in _LINHAS_CIRCUNFERENCIAS:
            if tipo == "numero":
                linha[chave] = circunferencias.get(chave, [])[indice]
        if any(valor is not None for chave, valor in linha.items() if chave != "data"):
            avaliacoes.append(linha)
    return avaliacoes


def _avaliacoes_composicao_para_banco(
    dobras_cutaneas: dict, peso: list, composicao_corporal: dict, a_partir_de: int = 0
) -> list:
    datas = dobras_cutaneas.get("datas", [])
    avaliacoes = []
    for indice, data in enumerate(datas):
        if indice < a_partir_de:
            continue
        linha = {"data": data, "peso": peso[indice]}
        for chave in _CHAVES_DOBRAS_7:
            linha[chave] = dobras_cutaneas.get(chave, [])[indice]
        for chave in (
            "soma_dobras", "densidade_corporal", "percentual_gordura",
            "percentual_gordura_bruto", "massa_gorda", "massa_magra",
        ):
            linha[chave] = composicao_corporal.get(chave, [])[indice]
        if any(valor is not None for chave, valor in linha.items() if chave != "data"):
            avaliacoes.append(linha)
    return avaliacoes


_CAMPOS_ALUNO_EDITAVEIS_APOS_CADASTRO = (
    "altura_m",
    "idade",
    "frequencia_semanal",
    "tempo_treino_dia",
    "doenca_tem",
    "doenca_qual",
    "limitacao_tem",
    "limitacao_qual",
    "dor_tem",
    "dor_qual",
    "cirurgia_tem",
    "cirurgia_qual",
    "medicamento_controlado",
    "fazendo_dieta",
    "consumo_alcool",
    "fuma",
)


_AZUL_PARA_ROSA = {
    Cores.AZUL_PRIMARIO: Cores.ROSA_PRIMARIO,
    Cores.AZUL_ESCURO: Cores.ROSA_ESCURO,
    Cores.AZUL_HOVER: Cores.ROSA_HOVER,
}
_ROSA_PARA_AZUL = {rosa: azul for azul, rosa in _AZUL_PARA_ROSA.items()}


class _TemaFeminino(QObject):
    """Troca o azul pelo rosa no cadastro enquanto o sexo selecionado for Feminino.

    Fica escutando StyleChange/Polish para repintar estilos reaplicados depois
    (ex.: campo que sai do estado de erro) e widgets criados mais tarde.
    """

    def __init__(self, raiz: QWidget):
        super().__init__(raiz)
        self._raiz = raiz
        self._ativo = False

    def definir(self, ativo: bool) -> None:
        if ativo == self._ativo:
            return
        self._ativo = ativo
        if ativo:
            QApplication.instance().installEventFilter(self)
        else:
            QApplication.instance().removeEventFilter(self)
        for widget in [self._raiz, *self._raiz.findChildren(QWidget)]:
            self._pintar(widget)

    def eventFilter(self, obj, evento):
        if evento.type() in (QEvent.StyleChange, QEvent.Polish) and isinstance(obj, QWidget):
            pai = obj
            while pai is not None and pai is not self._raiz:
                pai = pai.parentWidget()
            if pai is not None:
                self._pintar(obj)
        return False

    def _pintar(self, widget: QWidget) -> None:
        mapa = _AZUL_PARA_ROSA if self._ativo else _ROSA_PARA_AZUL
        estilo = novo = widget.styleSheet()
        for de, para in mapa.items():
            novo = novo.replace(de, para)
        if novo != estilo:
            widget.setStyleSheet(novo)
        paleta = widget.palette()
        destaque = paleta.color(QPalette.Highlight).name().upper()
        if destaque in mapa:
            paleta.setColor(QPalette.Highlight, QColor(mapa[destaque]))
            widget.setPalette(paleta)


class CadastroAlunoWizard(QWidget):
    cadastro_concluido = Signal()
    voltar_para_home = Signal()

    def __init__(self, aluno_service, parent=None):
        super().__init__(parent)
        self._aluno_service = aluno_service
        self._dados_coletados: dict = {}
        self._etapa_atual = 0
        self._aluno_id: Optional[int] = None

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_PAGINA};")

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(40, 30, 40, 30)
        layout_raiz.setSpacing(20)

        layout_raiz.addStretch(1)

        self._label_erro_geral = QLabel("")
        self._label_erro_geral.setWordWrap(True)
        self._label_erro_geral.setStyleSheet(
            f"""
            background-color: {Cores.ERRO_FUNDO};
            color: {Cores.ERRO};
            border-radius: 8px;
            padding: 10px 14px;
            font-size: {Fontes.TAMANHO_LABEL}px;
            """
        )
        self._label_erro_geral.hide()
        layout_raiz.addWidget(self._label_erro_geral)

        self._etapas = [
            DadosAlunoStep(),
            AnamneseStep(),
            ObjetivoPrincipalStep(),
            FrequenciaTreinoStep(),
            HistoricoSaudeStep(),
            HabitosVidaStep(),
            AvaliacaoFisicaStep(),
            ComposicaoCorporalStep(),
            ImagensAlunoStep(),
        ]

        self._tema_feminino = _TemaFeminino(self)
        campo_sexo = self._etapas[0]._campo_sexo
        campo_sexo.currentIndexChanged.connect(
            lambda: self._tema_feminino.definir(campo_sexo.currentData() == "Feminino")
        )

        self._stack = QStackedWidget()
        for etapa in self._etapas:
            self._stack.addWidget(etapa)
        layout_raiz.addWidget(self._stack, stretch=12)
        self._layout_raiz = layout_raiz
        self._stack.currentChanged.connect(self._ajustar_espacadores)

        layout_raiz.addStretch(1)

        layout_navegacao = QHBoxLayout()
        layout_navegacao.setSpacing(12)

        self._botao_anterior = BotaoSecundario("< Anterior")
        self._botao_anterior.setFixedWidth(140)
        self._botao_anterior.clicked.connect(self._anterior_clicado)
        layout_navegacao.addWidget(self._botao_anterior)

        layout_navegacao.addStretch()

        self._botao_proximo = BotaoPrimario("Próximo >")
        self._botao_proximo.setFixedWidth(160)
        self._botao_proximo.clicked.connect(self._proximo_clicado)
        layout_navegacao.addWidget(self._botao_proximo)

        layout_raiz.addLayout(layout_navegacao)

        self._atualizar_botoes()


    def _atualizar_botoes(self) -> None:
        ultima_etapa = self._etapa_atual == len(self._etapas) - 1
        self._botao_proximo.setText("Salvar" if ultima_etapa else "Próximo >")

    def _ajustar_espacadores(self, indice: int) -> None:
        fator = 0 if isinstance(self._etapas[indice], ImagensAlunoStep) else 1
        self._layout_raiz.setStretch(0, fator)
        self._layout_raiz.setStretch(3, fator)

    def _anterior_clicado(self) -> None:
        self._label_erro_geral.hide()
        if self._etapa_atual == 0:
            self.voltar_para_home.emit()
            return
        self._etapa_atual -= 1
        self._stack.setCurrentIndex(self._etapa_atual)
        self._atualizar_botoes()
        self._notificar_entrada_etapa()

    def _proximo_clicado(self) -> None:
        self._label_erro_geral.hide()
        etapa_widget = self._etapas[self._etapa_atual]
        dados = etapa_widget.obter_dados_validados()
        if dados is None:
            return

        self._dados_coletados.update(dados)

        if self._etapa_atual < len(self._etapas) - 1:
            self._etapa_atual += 1
            self._stack.setCurrentIndex(self._etapa_atual)
            self._atualizar_botoes()
            self._notificar_entrada_etapa()
        else:
            self._salvar_aluno()

    def _notificar_entrada_etapa(self) -> None:
        etapa_atual = self._etapas[self._etapa_atual]
        ao_entrar = getattr(etapa_atual, "ao_entrar", None)
        if ao_entrar is not None:
            ao_entrar(self._dados_coletados)

    def _salvar_aluno(self) -> None:
        parametros_aceitos = set(inspect.signature(self._aluno_service.criar_aluno).parameters)
        dados_para_salvar = {
            chave: valor
            for chave, valor in self._dados_coletados.items()
            if chave in parametros_aceitos
        }

        etapa_circunferencias = self._etapas[6]
        etapa_composicao = self._etapas[7]
        etapa_imagens = self._etapas[8]

        avaliacoes_circunferencias_novas = _avaliacoes_circunferencias_para_banco(
            self._dados_coletados.get("circunferencias", {}),
            a_partir_de=etapa_circunferencias.avaliacoes_ja_salvas(),
        )
        avaliacoes_composicao_novas = _avaliacoes_composicao_para_banco(
            self._dados_coletados.get("dobras_cutaneas", {}),
            self._dados_coletados.get("peso", []),
            self._dados_coletados.get("composicao_corporal", {}),
            a_partir_de=etapa_composicao.avaliacoes_ja_salvas(),
        )
        sessoes_fotos_novas = _sessoes_fotos_para_banco(
            self._dados_coletados.get("sessoes_fotos", []),
            a_partir_de=etapa_imagens.avaliacoes_ja_salvas(),
        )

        try:
            if self._aluno_id is None:
                aluno = self._aluno_service.criar_aluno(**dados_para_salvar)
                self._aluno_id = aluno.id
            else:
                dados_editaveis = {
                    chave: valor
                    for chave, valor in dados_para_salvar.items()
                    if chave in _CAMPOS_ALUNO_EDITAVEIS_APOS_CADASTRO
                }
                self._aluno_service.atualizar_aluno(self._aluno_id, **dados_editaveis)

            self._aluno_service.adicionar_avaliacoes_circunferencias(
                self._aluno_id, avaliacoes_circunferencias_novas
            )
            self._aluno_service.adicionar_avaliacoes_composicao(
                self._aluno_id, avaliacoes_composicao_novas
            )
            self._aluno_service.adicionar_sessoes_fotos(self._aluno_id, sessoes_fotos_novas)
        except Exception:
            self._label_erro_geral.setText(
                "Não foi possível salvar o aluno agora. Tente novamente."
            )
            self._label_erro_geral.show()
            return

        self.cadastro_concluido.emit()


    def _definir_bloqueio_dados_basicos(self, bloqueado: bool) -> None:
        etapa_dados, etapa_anamnese, etapa_objetivo, etapa_frequencia = self._etapas[:4]
        etapa_dados.bloquear_campos_fixos(bloqueado)
        etapa_anamnese.bloquear_campos_fixos(bloqueado)
        etapa_objetivo.bloquear_campos_fixos(bloqueado)
        etapa_frequencia.bloquear_campos_fixos(bloqueado)

    def resetar(self) -> None:
        self._aluno_id = None
        self._dados_coletados = {}
        self._etapa_atual = 0
        self._stack.setCurrentIndex(0)
        self._label_erro_geral.hide()
        for etapa in self._etapas:
            etapa.limpar()
        self._definir_bloqueio_dados_basicos(bloqueado=False)
        self._atualizar_botoes()
        QTimer.singleShot(0, self._etapas[0].focar_primeiro_campo)

    def abrir_para_edicao(self, aluno_id: int) -> bool:
        aluno = self._aluno_service.buscar_por_id(aluno_id)
        if aluno is None:
            return False

        dados_aluno = asdict(aluno)

        self._aluno_id = aluno_id
        self._dados_coletados = dict(dados_aluno)
        self._label_erro_geral.hide()

        etapa_dados, etapa_anamnese, etapa_objetivo, etapa_frequencia, etapa_saude, \
            etapa_habitos, etapa_circunferencias, etapa_composicao, etapa_imagens = self._etapas

        for etapa in (
            etapa_dados, etapa_anamnese, etapa_objetivo, etapa_frequencia,
            etapa_saude, etapa_habitos,
        ):
            etapa.limpar()
            etapa.carregar_dados(dados_aluno)

        self._definir_bloqueio_dados_basicos(bloqueado=True)

        etapa_circunferencias.carregar_avaliacoes(
            self._aluno_service.listar_avaliacoes_circunferencias(aluno_id)
        )
        etapa_composicao.carregar_avaliacoes(
            self._aluno_service.listar_avaliacoes_composicao(aluno_id)
        )
        etapa_imagens.carregar_sessoes(self._aluno_service.listar_sessoes_fotos(aluno_id))

        self._etapa_atual = 0
        self._stack.setCurrentIndex(0)
        self._label_erro_geral.hide()
        self._atualizar_botoes()
        self._notificar_entrada_etapa()
        return True
