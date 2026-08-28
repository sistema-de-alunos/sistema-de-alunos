"""Tela 2 — Cadastro de aluno, organizado como etapas navegáveis.

`CadastroAlunoWizard` controla a navegação e acumula os dados coletados em
cada etapa. Cada etapa é um QWidget independente responsável pelo seu
próprio conteúdo visual (título/cabeçalho + card(s)) — o wizard só cuida do
fundo da página, da barra de navegação e de empilhar as etapas. Para
adicionar uma nova etapa no futuro basta criar um QWidget com o mesmo
formato — método `obter_dados_validados()` e `limpar()` — e incluí-lo na
lista `self._etapas`.
"""

from core.qt_core import (
    QByteArray,
    QButtonGroup,
    QColor,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QIcon,
    QLabel,
    QLineEdit,
    QPainter,
    QPalette,
    QPixmap,
    QEasingCurve,
    QPushButton,
    Qt,
    QSize,
    QStackedWidget,
    QSvgRenderer,
    QTextEdit,
    QTimer,
    QVariantAnimation,
    QVBoxLayout,
    QWidget,
    Signal,
)
from core.theme import Cores, Fontes
from core.validators import (
    SEXO_OPCOES,
    validar_idade,
    validar_nome_completo,
    validar_objetivo_principal,
    validar_sexo,
    validar_treinou_antes,
)
from gui.widgets.botao_principal import BotaoPrimario, BotaoSecundario


class _CampoFormulario(QWidget):
    """Agrupa label + campo + mensagem de erro, com estilo consistente."""

    def __init__(self, label_texto: str, campo: QWidget, parent=None):
        super().__init__(parent)
        self.campo = campo

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_texto)
        label.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_LABEL}px; font-weight: 600;"
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
        if isinstance(self.campo, QLineEdit):
            self.campo.setStyleSheet(
                f"""
                QLineEdit {{
                    background-color: {Cores.SUPERFICIE};
                    border: 1px solid {cor_borda};
                    border-radius: 10px;
                    padding-left: 18px;
                    font-size: 15px;
                    color: {Cores.TEXTO_PRIMARIO};
                    min-height: 54px;
                }}
                QLineEdit:focus {{ border: 1px solid {Cores.AZUL_PRIMARIO}; }}
                """
            )
        elif isinstance(self.campo, QComboBox):
            # A causa do dropdown "invisível" é a QComboBox herdar a paleta
            # escura do sistema para o popup (QAbstractItemView) enquanto o
            # campo fechado usa cores claras definidas aqui. Sem estilizar
            # explicitamente QAbstractItemView (e seus itens/hover/seleção),
            # o Qt usa a paleta padrão do SO para a lista suspensa, que no
            # Windows costuma ficar com texto claro sobre fundo claro.
            self.campo.setStyleSheet(
                f"""
                QComboBox {{
                    background-color: {Cores.SUPERFICIE};
                    border: 1px solid {cor_borda};
                    border-radius: 10px;
                    padding-left: 18px;
                    font-size: 15px;
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


def _criar_cartao() -> QFrame:
    """Cartão branco padrão usado em todas as etapas do cadastro.

    Estilo aplicado direto na instância (sem seletor de tipo "QFrame"): como
    QLabel também é, por herança, um QFrame, um seletor de tipo aqui
    vazaria o fundo/borda do cartão para as labels internas, dando a elas
    uma aparência indesejada de "caixa".
    """
    cartao = QFrame()
    cartao.setStyleSheet(
        f"""
        background-color: {Cores.SUPERFICIE};
        border: 1px solid {Cores.BORDA};
        border-radius: 14px;
        """
    )
    return cartao


class DadosAlunoStep(QWidget):
    """Etapa 1 do cadastro: nome completo, idade e sexo."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(20)

        titulo = QLabel("Dados do Aluno")
        titulo.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_TITULO}px; font-weight: 700;"
        )
        layout_raiz.addWidget(titulo)

        descricao = QLabel(
            "Inicie o cadastro preenchendo as informações básicas do novo aluno "
            "para iniciar a avaliação."
        )
        descricao.setWordWrap(True)
        descricao.setStyleSheet(
            f"color: {Cores.TEXTO_DESCRICAO}; font-size: 16px; font-weight: 600;"
        )
        layout_raiz.addWidget(descricao)

        cartao = _criar_cartao()
        # Margem superior um pouco maior: dá mais respiro entre o topo do
        # cartão e o início dos campos do formulário.
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 32, 28, 28)
        layout_cartao.setSpacing(24)

        self._campo_nome = QLineEdit()
        self._campo_nome.setPlaceholderText("Digite o nome completo do aluno")
        self._grupo_nome = _CampoFormulario("Nome completo:", self._campo_nome)
        layout_cartao.addWidget(self._grupo_nome)

        self._campo_idade = QLineEdit()
        self._campo_idade.setPlaceholderText("Ex.: 25")
        self._campo_idade.setMaxLength(3)
        self._grupo_idade = _CampoFormulario("Idade:", self._campo_idade)
        layout_cartao.addWidget(self._grupo_idade)

        self._campo_sexo = QComboBox()
        self._campo_sexo.addItem("Selecione uma opção", userData=None)
        for opcao in SEXO_OPCOES:
            self._campo_sexo.addItem(opcao, userData=opcao)
        # Reforça a paleta clara diretamente na view interna do popup: em
        # alguns temas do Windows o QSS do QComboBox não é suficiente para
        # sobrescrever a paleta padrão herdada pela lista suspensa.
        paleta_popup = self._campo_sexo.view().palette()
        paleta_popup.setColor(QPalette.Base, QColor(Cores.SUPERFICIE))
        paleta_popup.setColor(QPalette.Text, QColor(Cores.TEXTO_PRIMARIO))
        paleta_popup.setColor(QPalette.Highlight, QColor(Cores.AZUL_PRIMARIO))
        paleta_popup.setColor(QPalette.HighlightedText, QColor("white"))
        self._campo_sexo.view().setPalette(paleta_popup)
        self._grupo_sexo = _CampoFormulario("Sexo:", self._campo_sexo)
        layout_cartao.addWidget(self._grupo_sexo)

        layout_raiz.addWidget(cartao)

        # Tab entre os campos segue a ordem natural em que foram criados.
        self.setTabOrder(self._campo_nome, self._campo_idade)
        self.setTabOrder(self._campo_idade, self._campo_sexo)

    def obter_dados_validados(self):
        """Valida os campos; retorna um dict com os dados ou None se inválido."""
        self._grupo_nome.limpar_erro()
        self._grupo_idade.limpar_erro()
        self._grupo_sexo.limpar_erro()

        nome = self._campo_nome.text()
        erro_nome = validar_nome_completo(nome)

        idade_texto = self._campo_idade.text()
        idade, erro_idade = validar_idade(idade_texto)

        sexo = self._campo_sexo.currentData()
        erro_sexo = validar_sexo(sexo)

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

        if not valido:
            return None

        return {
            "nome_completo": nome.strip(),
            "idade": idade,
            "sexo": sexo,
        }

    def limpar(self) -> None:
        self._campo_nome.clear()
        self._campo_idade.clear()
        self._campo_sexo.setCurrentIndex(0)
        self._grupo_nome.limpar_erro()
        self._grupo_idade.limpar_erro()
        self._grupo_sexo.limpar_erro()

    def focar_primeiro_campo(self) -> None:
        self._campo_nome.setFocus()


# -- Etapa 2: Anamnese ---------------------------------------------------

# Ícones minimalistas (traço fino, sem preenchimento) desenhados em SVG, no
# mesmo espírito do ícone de lixeira já usado no card do aluno: evita
# depender da fonte de emoji do sistema para um resultado leve e consistente.
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
    """Botão de seleção única usado nas opções 'Sim' / 'Não' da anamnese."""

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
    """Etapa 2 do cadastro: histórico de atividade física (anamnese)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        # Cabeçalho ---------------------------------------------------------
        # Mesmo azul já usado no restante do sistema (hover dos botões
        # primários); aqui vira o fundo do banner de título da etapa.
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

        # Card "Já treinou antes?" -------------------------------------------
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

        # QButtonGroup garante a seleção única (Sim OU Não, nunca os dois).
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

        # Card "Treina há quanto tempo?" -------------------------------------
        self._campo_tempo_treinamento = QLineEdit()
        self._campo_tempo_treinamento.setPlaceholderText("Ex: 6 meses, 2 anos...")
        self._grupo_tempo_treinamento = _CampoFormulario(
            "Treina há quanto tempo?", self._campo_tempo_treinamento
        )
        layout_raiz.addWidget(self._empacotar_em_cartao(self._grupo_tempo_treinamento))

        # Card "Tempo sem atividade física?" ----------------------------------
        self._campo_tempo_parado = QLineEdit()
        self._campo_tempo_parado.setPlaceholderText("Ex: Nunca parei, 3 meses...")
        self._grupo_tempo_parado = _CampoFormulario(
            "Tempo sem atividade física?", self._campo_tempo_parado
        )
        layout_raiz.addWidget(self._empacotar_em_cartao(self._grupo_tempo_parado))

    @staticmethod
    def _empacotar_em_cartao(conteudo: QWidget) -> QFrame:
        cartao = _criar_cartao()
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.addWidget(conteudo)
        return cartao

    def obter_dados_validados(self):
        """Valida a etapa; retorna um dict com os dados ou None se inválida."""
        self._label_erro_treinou.hide()

        if self._botao_sim.isChecked():
            treinou_antes = "Sim"
        elif self._botao_nao.isChecked():
            treinou_antes = "Não"
        else:
            treinou_antes = None

        erro_treinou = validar_treinou_antes(treinou_antes)
        if erro_treinou:
            self._label_erro_treinou.setText(erro_treinou)
            self._label_erro_treinou.show()
            return None

        return {
            "treinou_antes": treinou_antes,
            "tempo_treinamento": self._campo_tempo_treinamento.text().strip(),
            "tempo_sem_atividade": self._campo_tempo_parado.text().strip(),
        }

    def limpar(self) -> None:
        # setExclusive(False) permite desmarcar os dois temporariamente: sob
        # exclusividade normal, um QButtonGroup não deixa um botão marcado
        # ser desmarcado sem marcar outro no lugar.
        self._grupo_treinou.setExclusive(False)
        self._botao_sim.setChecked(False)
        self._botao_nao.setChecked(False)
        self._grupo_treinou.setExclusive(True)
        self._campo_tempo_treinamento.clear()
        self._campo_tempo_parado.clear()
        self._label_erro_treinou.hide()


# -- Etapa 3: Objetivo principal ------------------------------------------


_TAMANHO_ICONE_OBJETIVO = 18
_DURACAO_TRANSICAO_ICONE_MS = 200

# Ícones minimalistas (mesmo traço fino das demais etapas) para cada opção
# de objetivo. Só a cor muda entre estado normal/selecionado — o desenho é
# sempre o mesmo, então a "troca de cor" pode ser animada quadro a quadro.
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
    """Botão de seleção única usado nas opções de objetivo principal.

    Mesmo padrão visual/de estado do botão 'Sim' da Etapa 2 (fundo e borda
    verdes quando marcado) — aqui sem variante vermelha, pois todo objetivo
    marcado usa o mesmo verde de "selecionado". O ícone à esquerda do texto
    acompanha esse estado: sua cor faz uma transição suave (não uma troca
    brusca) entre a cor normal e o verde de seleção.
    """

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

        # Anima só a cor do ícone (QVariantAnimation interpola QColor
        # nativamente); o botão continua com o mesmo tamanho/ícone o tempo
        # todo — cada quadro apenas re-renderiza o mesmo SVG numa cor
        # intermediária entre a normal e a verde de seleção.
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


# (texto, valor salvo no banco, ícone) de cada botão de objetivo
_OBJETIVOS = [
    ("Emagrecimento", "emagrecimento", _SVG_TENDENCIA_BAIXA),
    ("Hipertrofia", "hipertrofia", _SVG_HALTER),
    ("Condicionamento", "condicionamento", _SVG_PULSO),
    ("Reabilitação", "reabilitacao", _SVG_CRUZ_MEDICA),
]
_OBJETIVO_OUTRO_VALOR = "outro"


class ObjetivoPrincipalStep(QWidget):
    """Etapa 3 do cadastro: objetivo principal do aluno na anamnese."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        # Cabeçalho — mesmo banner azul da Etapa 2, só muda o subtítulo.
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

        # Card "Qual seu objetivo principal?" --------------------------------
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

        # Grade 2 colunas para os quatro objetivos fixos; "Outro" fica numa
        # linha própria, ocupando a largura toda, como no modelo enviado.
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

        # Bloco "Descreva seu objetivo" — só existe visualmente quando
        # "Outro" está marcado; escondido, não deixa espaço vazio no card.
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
        self._campo_outro.setStyleSheet(
            f"""
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
        )
        layout_bloco_outro.addWidget(self._campo_outro)

        self._bloco_outro.hide()
        layout_cartao.addWidget(self._bloco_outro)

        self._botao_outro.toggled.connect(self._bloco_outro.setVisible)

        self._label_erro_objetivo = QLabel("")
        self._label_erro_objetivo.setStyleSheet(
            f"background: transparent; border: none; color: {Cores.ERRO}; font-size: 12px;"
        )
        self._label_erro_objetivo.hide()
        layout_cartao.addWidget(self._label_erro_objetivo)

        layout_raiz.addWidget(cartao)
        # Sem conteúdo suficiente para preencher a altura que o
        # QStackedWidget reserva para a etapa, o espaço sobrando seria
        # redistribuído entre cabeçalho e cartão (esticando visivelmente o
        # cabeçalho, que tem fundo colorido). Este stretch absorve essa
        # sobra no fim, mantendo os dois do tamanho do próprio conteúdo.
        layout_raiz.addStretch(1)

    def obter_dados_validados(self):
        """Valida a etapa; retorna um dict com os dados ou None se inválida."""
        self._label_erro_objetivo.hide()

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

        objetivo_outro = (
            self._campo_outro.toPlainText().strip()
            if objetivo == _OBJETIVO_OUTRO_VALOR
            else None
        )

        return {
            "objetivo_principal": objetivo,
            "objetivo_outro": objetivo_outro,
        }

    def limpar(self) -> None:
        # setExclusive(False) permite desmarcar todos temporariamente: sob
        # exclusividade normal, um QButtonGroup não deixa um botão marcado
        # ser desmarcado sem marcar outro no lugar.
        self._grupo_objetivo.setExclusive(False)
        for botao in self._botoes_objetivo.values():
            botao.setChecked(False)
        self._grupo_objetivo.setExclusive(True)
        self._campo_outro.clear()
        self._label_erro_objetivo.hide()


class CadastroAlunoWizard(QWidget):
    """Container que controla a navegação entre as etapas do cadastro."""

    cadastro_concluido = Signal()
    voltar_para_home = Signal()

    def __init__(self, aluno_service, parent=None):
        super().__init__(parent)
        self._aluno_service = aluno_service
        self._dados_coletados: dict = {}
        self._etapa_atual = 0

        # Sem WA_StyledBackground, um QWidget puro (diferente de QFrame) não
        # pinta o background definido via QSS quando usado como widget de
        # topo — o fundo fica preto em vez de Cores.FUNDO_PAGINA.
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_PAGINA};")

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(40, 30, 40, 30)
        layout_raiz.setSpacing(20)

        # Espaços elásticos iguais antes e depois do bloco de conteúdo
        # centralizam esse bloco verticalmente entre a margem superior e os
        # botões de navegação, em vez de deixar tudo colado no topo com uma
        # grande área vazia embaixo.
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

        # Cada etapa monta seu próprio título/cabeçalho e card(s); o wizard
        # só empilha as etapas — assim cada uma pode ter uma composição
        # visual diferente (um card só, vários cards, um banner) mantendo o
        # mesmo fundo e a mesma barra de navegação.
        self._etapas = [DadosAlunoStep(), AnamneseStep(), ObjetivoPrincipalStep()]

        self._stack = QStackedWidget()
        for etapa in self._etapas:
            self._stack.addWidget(etapa)
        layout_raiz.addWidget(self._stack)

        layout_raiz.addStretch(1)

        # Navegação -------------------------------------------------------
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

    # -- Navegação -----------------------------------------------------

    def _atualizar_botoes(self) -> None:
        # O texto fica sempre "Próximo >": o cadastro ainda vai ganhar mais
        # etapas, então a etapa mais recente nunca deve parecer o fim do
        # fluxo — mesmo sendo, por ora, a última realmente implementada (ao
        # avançar por ela, os dados são salvos por não haver próxima etapa
        # ainda; quando a etapa final de fato existir, ela é quem deve
        # assumir o rótulo "Salvar").
        self._botao_proximo.setText("Próximo >")

    def _anterior_clicado(self) -> None:
        self._label_erro_geral.hide()
        if self._etapa_atual == 0:
            self.voltar_para_home.emit()
            return
        self._etapa_atual -= 1
        self._stack.setCurrentIndex(self._etapa_atual)
        self._atualizar_botoes()

    def _proximo_clicado(self) -> None:
        self._label_erro_geral.hide()
        etapa_widget = self._etapas[self._etapa_atual]
        dados = etapa_widget.obter_dados_validados()
        if dados is None:
            return  # erros já exibidos junto de cada campo

        self._dados_coletados.update(dados)

        if self._etapa_atual < len(self._etapas) - 1:
            self._etapa_atual += 1
            self._stack.setCurrentIndex(self._etapa_atual)
            self._atualizar_botoes()
        else:
            self._salvar_aluno()

    def _salvar_aluno(self) -> None:
        try:
            self._aluno_service.criar_aluno(**self._dados_coletados)
        except Exception:
            self._label_erro_geral.setText(
                "Não foi possível salvar o aluno agora. Tente novamente."
            )
            self._label_erro_geral.show()
            return

        self.cadastro_concluido.emit()

    # -- Ciclo de vida ---------------------------------------------------

    def resetar(self) -> None:
        """Prepara o wizard para um novo cadastro do zero."""
        self._dados_coletados = {}
        self._etapa_atual = 0
        self._stack.setCurrentIndex(0)
        self._label_erro_geral.hide()
        for etapa in self._etapas:
            etapa.limpar()
        self._atualizar_botoes()
        QTimer.singleShot(0, self._etapas[0].focar_primeiro_campo)
