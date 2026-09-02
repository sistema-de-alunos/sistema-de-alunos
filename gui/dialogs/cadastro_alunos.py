"""Tela 2 — Cadastro de aluno, organizado como etapas navegáveis.

`CadastroAlunoWizard` controla a navegação e acumula os dados coletados em
cada etapa. Cada etapa é um QWidget independente responsável pelo seu
próprio conteúdo visual (título/cabeçalho + card(s)) — o wizard só cuida do
fundo da página, da barra de navegação e de empilhar as etapas. Para
adicionar uma nova etapa no futuro basta criar um QWidget com o mesmo
formato — método `obter_dados_validados()` e `limpar()` — e incluí-lo na
lista `self._etapas`. Uma etapa também pode, opcionalmente, definir
`ao_entrar(dados_coletados)` para reagir a dados de etapas anteriores toda
vez que é exibida (usado pela etapa de Avaliação Física para escolher o
boneco anatômico de acordo com o sexo já cadastrado).
"""

from typing import Dict, Optional, Tuple

from core.qt_core import (
    QByteArray,
    QButtonGroup,
    QColor,
    QComboBox,
    QDoubleValidator,
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
    QScrollArea,
    QSize,
    QSizePolicy,
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
    FREQUENCIA_SEMANAL_OPCOES,
    SEXO_OPCOES,
    TEMPO_TREINO_OPCOES,
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
    """Agrupa label + campo + mensagem de erro, com estilo consistente.

    `tamanho_fonte_label`/`tamanho_fonte_campo` são opcionais — os padrões
    reproduzem exatamente o tamanho já usado pelo resto do sistema, então
    quem não os informa (Etapa 2 e Etapa 4, por exemplo) continua com a
    aparência de sempre. Existem só para a Etapa 1 pedir textos um pouco
    maiores sem duplicar toda esta classe.
    """

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
        if isinstance(self.campo, QLineEdit):
            self.campo.setStyleSheet(
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
    """Reforça a paleta clara na view do popup (mesmo ajuste já usado no combo de sexo).

    Sem isso, em alguns temas do Windows o QSS do QComboBox não é suficiente
    para sobrescrever a paleta padrão herdada pela lista suspensa.
    """
    paleta_popup = campo.view().palette()
    paleta_popup.setColor(QPalette.Base, QColor(Cores.SUPERFICIE))
    paleta_popup.setColor(QPalette.Text, QColor(Cores.TEXTO_PRIMARIO))
    paleta_popup.setColor(QPalette.Highlight, QColor(Cores.AZUL_PRIMARIO))
    paleta_popup.setColor(QPalette.HighlightedText, QColor("white"))
    campo.view().setPalette(paleta_popup)


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

        # Layout mais compacto que o padrão "20px entre tudo" das demais
        # etapas: aqui cada vão é calibrado à mão (título colado na
        # descrição, um respiro um pouco maior antes do cartão) em vez de um
        # espaçamento uniforme — é o que dá a sensação de hierarquia sem
        # sobrar vazio entre os blocos.
        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        # Título com destaque maior que o resto do sistema (por isso o
        # tamanho é literal aqui, e não Fontes.TAMANHO_TITULO — esse mesmo
        # texto de estilo é reaproveitado pelo banner "Anamnese" das etapas
        # 2 a 6, que não deve mudar de tamanho).
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
        # Margens/spacing reduzidos (eram 28,32,28,28 com 24 entre campos):
        # o card ainda "respira", só não sobra tanto vazio acima/abaixo dos
        # três campos nem entre eles.
        layout_cartao = QVBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 20, 28, 20)
        layout_cartao.setSpacing(16)

        # tamanho_fonte_label/campo um pouco maiores que o padrão (13/15px)
        # só nesta etapa — _CampoFormulario mantém os tamanhos originais
        # para quem não passa esses argumentos (Etapa 2 e Etapa 4).
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
        self._grupo_sexo = _CampoFormulario(
            "Sexo:",
            self._campo_sexo,
            tamanho_fonte_label=15,
            tamanho_fonte_campo=16,
        )
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
        self._grupo_tempo_treinamento.limpar_erro()
        self._grupo_tempo_parado.limpar_erro()

        if self._botao_sim.isChecked():
            treinou_antes = "Sim"
        elif self._botao_nao.isChecked():
            treinou_antes = "Não"
        else:
            treinou_antes = None

        erro_treinou = validar_treinou_antes(treinou_antes)

        tempo_treinamento = self._campo_tempo_treinamento.text().strip()
        erro_tempo_treinamento = validar_tempo_treinamento(tempo_treinamento)

        tempo_sem_atividade = self._campo_tempo_parado.text().strip()
        erro_tempo_parado = validar_tempo_sem_atividade(tempo_sem_atividade)

        # Verifica os três campos antes de decidir: assim todos os erros
        # aparecem de uma vez, em vez de o usuário corrigir um e só então
        # descobrir o próximo (mesmo padrão das demais etapas do wizard).
        valido = True
        primeiro_campo_invalido = None
        if erro_treinou:
            self._label_erro_treinou.setText(erro_treinou)
            self._label_erro_treinou.show()
            valido = False
            primeiro_campo_invalido = self._botao_sim
        if erro_tempo_treinamento:
            self._grupo_tempo_treinamento.mostrar_erro(erro_tempo_treinamento)
            valido = False
            primeiro_campo_invalido = primeiro_campo_invalido or self._campo_tempo_treinamento
        if erro_tempo_parado:
            self._grupo_tempo_parado.mostrar_erro(erro_tempo_parado)
            valido = False
            primeiro_campo_invalido = primeiro_campo_invalido or self._campo_tempo_parado

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
        self._grupo_tempo_treinamento.limpar_erro()
        self._grupo_tempo_parado.limpar_erro()


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
        # Guardados como atributos para poder alternar para a variante de
        # erro (borda vermelha) e voltar, sem duplicar o QSS.
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
        # Desmarcar "Outro" (ou voltar a digitar) invalida o erro anterior —
        # sem isto ele ficaria preso na tela mesmo depois de corrigido.
        self._botao_outro.toggled.connect(lambda _: self._limpar_erro_outro())
        self._campo_outro.textChanged.connect(self._limpar_erro_outro)

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

    def _limpar_erro_outro(self) -> None:
        self._label_erro_outro.hide()
        self._campo_outro.setStyleSheet(self._estilo_campo_outro_normal)

    def obter_dados_validados(self):
        """Valida a etapa; retorna um dict com os dados ou None se inválida."""
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
        # setExclusive(False) permite desmarcar todos temporariamente: sob
        # exclusividade normal, um QButtonGroup não deixa um botão marcado
        # ser desmarcado sem marcar outro no lugar.
        self._grupo_objetivo.setExclusive(False)
        for botao in self._botoes_objetivo.values():
            botao.setChecked(False)
        self._grupo_objetivo.setExclusive(True)
        self._campo_outro.clear()
        self._label_erro_objetivo.hide()
        self._limpar_erro_outro()


# -- Etapa 4: Frequência e tempo de treino --------------------------------


class FrequenciaTreinoStep(QWidget):
    """Etapa 4 do cadastro: frequência semanal e tempo de treino por dia.

    Os dois campos são QComboBox com opções fixas (sem digitação livre) e já
    abrem com um valor padrão selecionado, então sempre há uma seleção
    válida — não existe estado "vazio" para o usuário deixar passar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        # Cabeçalho — mesmo banner azul das demais etapas da anamnese.
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

        # Card "Frequência semanal?" ------------------------------------
        self._campo_frequencia = QComboBox()
        for opcao in FREQUENCIA_SEMANAL_OPCOES:
            self._campo_frequencia.addItem(opcao, userData=opcao)
        _aplicar_paleta_clara_popup(self._campo_frequencia)
        self._grupo_frequencia = _CampoFormulario(
            "Frequência semanal?", self._campo_frequencia
        )
        layout_raiz.addWidget(self._empacotar_em_cartao(self._grupo_frequencia))

        # Card "Tempo de Treino por dia?" ---------------------------------
        self._campo_tempo_treino = QComboBox()
        for opcao in TEMPO_TREINO_OPCOES:
            self._campo_tempo_treino.addItem(opcao, userData=opcao)
        _aplicar_paleta_clara_popup(self._campo_tempo_treino)
        self._grupo_tempo_treino = _CampoFormulario(
            "Tempo de Treino por dia?", self._campo_tempo_treino
        )
        layout_raiz.addWidget(self._empacotar_em_cartao(self._grupo_tempo_treino))

        # Sem conteúdo suficiente para preencher a altura reservada pelo
        # QStackedWidget, o espaço sobrando seria redistribuído entre
        # cabeçalho e cards (mesmo motivo do stretch na Etapa 3).
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
        """Valida a etapa; retorna um dict com os dados ou None se inválida."""
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


# -- Etapa 5: Histórico de saúde e limitações ------------------------------


class _PerguntaSaude(QWidget):
    """Uma linha 'pergunta + Sim/Não', com campo 'Qual?' que só aparece com Sim.

    O campo fica oculto por padrão (sem reservar espaço — QHBoxLayout não
    aloca espaço para widgets escondidos) e alterna de visibilidade sozinho,
    ligado ao próprio estado do botão "Sim": marcou Sim → aparece; marcou Não
    (o que desmarca o Sim, já que o grupo é exclusivo) → some.
    """

    def __init__(self, texto_pergunta: str, parent=None):
        super().__init__(parent)

        # QVBoxLayout raiz (linha de controles + label de erro abaixo, este
        # oculto por padrão) em vez do QHBoxLayout único de antes: mesmo
        # espaçamento/alinhamento da linha original, só ganhando espaço para
        # a mensagem de erro sem interferir no layout das outras linhas.
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

        # QButtonGroup garante a seleção única (Sim OU Não, nunca os dois).
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._grupo.addButton(self._botao_sim)
        self._grupo.addButton(self._botao_nao)

        self._campo_qual = QLineEdit()
        self._campo_qual.setPlaceholderText("Qual?")
        # Guardados como atributos para alternar entre a borda normal e a de
        # erro sem duplicar o QSS a cada troca de estado.
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

        self._botao_sim.toggled.connect(self._campo_qual.setVisible)
        # Selecionar Sim/Não de novo ou corrigir o texto invalida o erro
        # anterior — sem isto ele ficaria preso na tela mesmo já corrigido.
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
        """Valida a linha; retorna True se ok, exibindo erro caso contrário."""
        self.limpar_erro()
        tem, qual = self.obter_resposta()

        if tem not in ("Sim", "Não"):
            self._mostrar_erro("Selecione uma opção.")
            return False

        if tem == "Sim" and not qual:
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
        """Foca o primeiro controle inválido da linha (Sim/Não ou 'Qual?')."""
        if self._botao_sim.isChecked() and not self._campo_qual.text().strip():
            self._campo_qual.setFocus()
        else:
            self._botao_sim.setFocus()

    def obter_resposta(self):
        """Retorna (tem, qual): tem é 'Sim'/'Não'/None; qual só é preenchido se tem == 'Sim'."""
        if self._botao_sim.isChecked():
            tem = "Sim"
        elif self._botao_nao.isChecked():
            tem = "Não"
        else:
            tem = None

        qual = self._campo_qual.text().strip() if tem == "Sim" else None
        return tem, qual

    def limpar(self) -> None:
        # setExclusive(False) permite desmarcar os dois temporariamente: sob
        # exclusividade normal, um QButtonGroup não deixa um botão marcado
        # ser desmarcado sem marcar outro no lugar.
        self._grupo.setExclusive(False)
        self._botao_sim.setChecked(False)
        self._botao_nao.setChecked(False)
        self._grupo.setExclusive(True)
        self._campo_qual.clear()
        self.limpar_erro()


# (chave usada nos dados coletados, texto da pergunta) de cada linha da etapa
_PERGUNTAS_SAUDE = [
    ("doenca", "Doença/Problema de saúde?"),
    ("limitacao", "Limitação de movimento?"),
    ("dor", "Dor em algum movimento?"),
    ("cirurgia", "Cirurgia?"),
]


class HistoricoSaudeStep(QWidget):
    """Etapa 5 do cadastro: doenças, limitações de movimento, dor e cirurgias."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        # Cabeçalho — mesmo banner azul das demais etapas da anamnese.
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

        # Card único com as quatro perguntas, uma por linha.
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
        # Mesmo motivo do stretch nas etapas 3 e 4: sem ele, o espaço restante
        # da altura do QStackedWidget infla o cabeçalho e o card à toa.
        layout_raiz.addStretch(1)

    def obter_dados_validados(self):
        """Valida a etapa: cada pergunta exige Sim/Não e, se Sim, o campo 'Qual?'."""
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


# -- Etapa 6: Avaliação física ----------------------------------------------


class _LinhaMedida(QWidget):
    """Uma linha da tabela de medidas: rótulo + campo numérico (cm)."""

    def __init__(self, texto_label: str, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        label = QLabel(texto_label)
        label.setFixedWidth(150)
        label.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 600;"
        )
        layout.addWidget(label)

        self.campo = QLineEdit()
        self.campo.setPlaceholderText("cm")
        # Desliga o frame nativo do QLineEdit (o "sunken panel" que o estilo
        # do Windows desenha por baixo do widget). Com ele ligado, o estilo
        # nativo soma sua própria borda 3D (mais clara embaixo/à direita,
        # para simular profundidade) por cima da borda de 4 lados definida
        # no QSS abaixo -- em telas com escala fracionária (125%/150%), essa
        # borda nativa clara some contra o fundo branco exatamente no lado de
        # baixo, dando a impressão de "borda inferior aberta". Desativando o
        # frame nativo, a única borda desenhada passa a ser a do QSS, igual
        # e fechada nos 4 lados.
        self.campo.setFrame(False)
        # 96px (e não os 80px originais) -- com padding 10px de cada lado e
        # fonte 16px em negrito, "120" (o maior valor plausível, ver
        # QDoubleValidator abaixo) quase encostava na borda; centralizado
        # (não mais alinhado à direita) fica claramente separado do rótulo à
        # esquerda mesmo já com o espaçamento maior do layout.
        self.campo.setFixedWidth(96)
        self.campo.setAlignment(Qt.AlignCenter)
        validador = QDoubleValidator(0.0, 300.0, 1, self.campo)
        validador.setNotation(QDoubleValidator.StandardNotation)
        self.campo.setValidator(validador)
        # Valor digitado precisa ser lido de relance: fonte maior e em negrito
        # (14px normal ficava fraco/pequeno ao lado do rótulo em negrito),
        # padding simétrico (só padding-left sem padding-right empurrava o
        # texto right-aligned quase até a borda) e borda um pouco mais forte
        # pra marcar bem a caixa contra o fundo branco do cartão.
        self.campo.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {Cores.SUPERFICIE};
                border: 1.5px solid {Cores.BORDA};
                border-radius: 8px;
                padding: 0 10px;
                font-size: 16px;
                font-weight: 700;
                color: {Cores.TEXTO_PRIMARIO};
                min-height: 36px;
            }}
            QLineEdit:focus {{ border: 1.5px solid {Cores.AZUL_PRIMARIO}; }}
            """
        )
        layout.addWidget(self.campo)
        layout.addStretch(1)


def _cabecalho_bloco_medidas(texto: str) -> QFrame:
    """Faixa azul escura de topo de um bloco de medidas (ex.: "Circunferência
    Parte Superior (MASC)") -- mesmo tom do banner usado no topo da etapa,
    mas arredondada só em cima para se fundir com o cartão que a envolve.
    O texto fica à esquerda e centralizado verticalmente pelas margens
    simétricas (12px em cima/embaixo) do layout de uma linha só.
    """
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
    layout.addWidget(titulo)
    return cabecalho


def _criar_bloco_medidas(titulo: str) -> Tuple[QFrame, QVBoxLayout]:
    """Card independente de um bloco de medidas (cabeçalho azul + linhas
    abaixo) -- reaproveita o mesmo cartão branco/borda das demais etapas
    para o corpo do bloco ficar visualmente ligado ao cabeçalho azul.
    Devolve o frame (para empilhar na coluna da tabela) e o layout interno
    onde cada `_LinhaMedida` do bloco deve ser adicionada.
    """
    bloco = _criar_cartao()
    layout_bloco = QVBoxLayout(bloco)
    layout_bloco.setContentsMargins(0, 0, 0, 0)
    layout_bloco.setSpacing(0)
    layout_bloco.addWidget(_cabecalho_bloco_medidas(titulo))

    corpo = QWidget()
    corpo.setStyleSheet("background: transparent;")
    layout_linhas = QVBoxLayout(corpo)
    layout_linhas.setContentsMargins(20, 16, 20, 16)
    # Mesmo 16px de antes entre linhas -- só a divisão em blocos mudou, o
    # espaçamento entre rótulo+campo de cada medida permanece igual.
    layout_linhas.setSpacing(16)
    layout_bloco.addWidget(corpo)

    return bloco, layout_linhas


def _texto_para_numero(texto: str) -> Optional[float]:
    texto = (texto or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


# (chave, rótulo exibido, id da região correspondente no boneco). Mais de uma
# linha pode apontar para a mesma região -- "Braço (E)" e "Braço (E)
# Contraído" são medidas diferentes do mesmo músculo, e o boneco só precisa
# saber que aquela região está sendo avaliada.
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
    """Etapa 6 do cadastro: medidas corporais com boneco anatômico interativo.

    O boneco não guarda estado próprio de avaliação: ele só reflete, em
    tempo real, quais campos de medida têm valor preenchido. Preencher ou
    apagar uma medida já atualiza o destaque sozinho — não existe uma
    seleção separada para sincronizar.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Vertical=Ignored (e não Preferred, o padrão) -- sem isto, o
        # QStackedWidget do wizard (`CadastroAlunoWizard._stack`) nunca
        # cresce além do sizeHint desta etapa, mesmo com os dois
        # `addStretch(1)` do wizard tendo espaço sobrando numa janela
        # grande: alguma combinação de layouts aninhados aqui dentro (o
        # QScrollArea da tabela + o QStackedWidget interno do boneco) faz o
        # cálculo de distribuição de espaço do Qt tratar o sizeHint desta
        # etapa como fixo, ignorando o `stretch=1` que o wizard já passa
        # pra ela -- Ignored faz o Qt desconsiderar esse sizeHint "preso" e
        # deixar o stretch mandar de verdade. `minimumSizeHint` (o piso de
        # ~400px comentado mais abaixo, no QScrollArea) continua valendo
        # normalmente -- Ignored não remove esse piso, só o teto artificial.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        # Cabeçalho — mesmo banner azul das demais etapas da anamnese.
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

        subtitulo_cabecalho = QLabel("Etapa 6: Avaliação física")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        # Card com tabela de medidas (esquerda) + boneco interativo (direita).
        cartao = _criar_cartao()
        # Antes, o cartão nunca precisava disto: sem o QScrollArea acima, o
        # tamanho natural da tabela (~1000px) sempre excedia o espaço
        # disponível, e o cartão acabava ocupando tudo por pura falta de
        # alternativa. Agora que a tabela pode ficar compacta e rolar, o
        # cartão precisa de Expanding explícito para continuar preenchendo a
        # altura disponível -- do contrário ele encolheria para o tamanho
        # natural do boneco (bem menor) e sobraria um vão vazio embaixo.
        cartao.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout_cartao = QHBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(24)

        # As 18 linhas (label + campo) empilhadas somam ~1000px de altura --
        # bem mais do que cabe numa janela normal (960x600, o mínimo do
        # app). Sem isto, o QVBoxLayout abaixo empurra sua altura mínima
        # inteira pra cima até o QStackedWidget do wizard e daí até a janela
        # principal: a tela só "funcionava" quando maximizada/fullscreen
        # porque só aí sobrava altura de tela suficiente para acomodar esse
        # mínimo -- em qualquer janela menor, as linhas ficavam espremidas
        # abaixo do próprio tamanho mínimo (é aí que a borda inferior dos
        # QLineEdit some: o conteúdo é cortado pela borda da janela/card,
        # não um problema de estilo). Um QScrollArea rola o EXCESSO em vez
        # de forçar a janela toda a crescer -- a tabela some no scroll só
        # quando realmente não há espaço, mas nunca fica cortada/espremida.
        painel_tabela = QWidget()
        painel_tabela.setStyleSheet("background: transparent;")
        coluna_tabela = QVBoxLayout(painel_tabela)
        coluna_tabela.setContentsMargins(0, 0, 4, 0)
        # 28px aqui -- não é mais o espaço entre linhas (isso agora é o
        # spacing de `layout_linhas` dentro de cada bloco, ver
        # `_criar_bloco_medidas`), e sim o vão entre os dois cards
        # (Parte Superior / Parte Inferior) empilhados nesta coluna: precisa
        # ser nitidamente maior que o espaço entre linhas de um mesmo bloco
        # para os dois cards lerem como blocos independentes, sem
        # desperdiçar espaço.
        coluna_tabela.setSpacing(28)

        self._campos: Dict[str, QLineEdit] = {}

        def _preencher_bloco(layout_linhas, linhas):
            for chave, texto_label, _regiao in linhas:
                linha = _LinhaMedida(texto_label)
                linha.campo.textChanged.connect(self._recalcular_destaques)
                self._campos[chave] = linha.campo
                layout_linhas.addWidget(linha)

        # Dois cards independentes (cabeçalho azul + linhas), em vez da
        # antiga divisão em três rótulos dentro de uma tabela única --
        # "Braços" passa a fazer parte do bloco superior, junto do resto das
        # medidas de cima, igual à referência do personal.
        bloco_superior, linhas_superior = _criar_bloco_medidas(
            "Circunferência Parte Superior (MASC)"
        )
        _preencher_bloco(linhas_superior, _LINHAS_PARTE_SUPERIOR + _LINHAS_BRACOS)
        coluna_tabela.addWidget(bloco_superior)

        bloco_inferior, linhas_inferior = _criar_bloco_medidas(
            "Circunferência Parte Inferior (MASC)"
        )
        _preencher_bloco(linhas_inferior, _LINHAS_PARTE_INFERIOR)
        coluna_tabela.addWidget(bloco_inferior)

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

        # Um boneco por sexo, cada um com sua própria imagem/pasta de
        # máscaras (proporções diferentes — ver gui/widgets/corpo_interativo.py).
        # `ao_entrar` escolhe qual página mostrar de acordo com o sexo já
        # cadastrado na Etapa 1.
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

        # Sexo ainda não informado (ex.: etapa nunca visitada) cai aqui até
        # `ao_entrar` decidir — mantém os dois bonecos como alternativa
        # explícita em vez de um terceiro placeholder "sem sexo".
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

        # stretch=1 (e sem addStretch depois) -- com o cartão já Expanding,
        # ele deve consumir o espaço vertical sobrando abaixo do cabeçalho;
        # um addStretch aqui competiria por esse mesmo espaço e voltaria a
        # deixar o cartão pequeno e colado no topo, com vão vazio embaixo.
        layout_raiz.addWidget(cartao, stretch=1)

        self._recalcular_destaques()

    def ao_entrar(self, dados_coletados: dict) -> None:
        """Chamado pelo wizard toda vez que essa etapa é exibida.

        Escolhe o boneco de acordo com o sexo já preenchido na Etapa 1 — o
        masculino não deve controlar o feminino nem vice-versa.
        """
        sexo = dados_coletados.get("sexo")
        if sexo == "Masculino":
            pagina = self._corpo_masculino
        elif sexo == "Feminino":
            pagina = self._corpo_feminino
        else:
            pagina = self._placeholder_corpo
        self._pilha_corpo.setCurrentWidget(pagina)

    def _recalcular_destaques(self) -> None:
        regioes_ativas = {
            _REGIAO_POR_CHAVE[chave]
            for chave, campo in self._campos.items()
            if campo.text().strip()
        }
        # Os dois bonecos usam os mesmos ids de região (ver
        # IDS_REGIOES_MASCULINO/IDS_REGIOES_FEMININO) — atualizar os dois
        # mantém o que não está visível em dia, então trocar de sexo em
        # `ao_entrar` nunca mostra um boneco com destaques desatualizados.
        self._corpo_masculino.definir_regioes_selecionadas(regioes_ativas)
        self._corpo_feminino.definir_regioes_selecionadas(regioes_ativas)

    def _focar_campo_da_regiao(self, regiao_id: str) -> None:
        """Interação inversa (item 14): clicar no boneco foca o primeiro
        campo daquela região na tabela, pronto para o personal digitar."""
        for chave, id_regiao in _REGIAO_POR_CHAVE.items():
            if id_regiao == regiao_id:
                campo = self._campos[chave]
                campo.setFocus()
                campo.selectAll()
                return

    def obter_dados_validados(self):
        """Sem campo obrigatório: sempre retorna as medidas preenchidas até agora."""
        return {
            f"medida_{chave}": _texto_para_numero(campo.text())
            for chave, campo in self._campos.items()
        }

    def limpar(self) -> None:
        for campo in self._campos.values():
            campo.clear()


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

        # Espaços elásticos antes e depois do bloco de conteúdo centralizam
        # esse bloco verticalmente entre a margem superior e os botões de
        # navegação, em vez de deixar tudo colado no topo com uma grande
        # área vazia embaixo -- mas com stretch bem menor que o do
        # `self._stack` logo abaixo (12 contra 1 de cada um): numa janela
        # grande, o QStackedWidget do wizard herda o tamanho mínimo da
        # etapa MAIS "rígida" que ele guarda (a Anamnese, cujo formulário
        # sem QScrollArea não encolhe) mesmo quando a etapa atual é outra
        # -- com os três itens (espaçador, stack, espaçador) brigando pelo
        # espaço sobrando em pé de igualdade (stretch=1 cada), esse piso
        # praticamente sempre "ganhava" e a etapa atual (cabeçalho + card)
        # ficava travada nesse tamanho mesmo em telas bem maiores, com o
        # boneco/tabela da Etapa 6 sempre pequenos. Dar ao `_stack` a
        # fatia MAIOR do espaço sobrando (em vez de 1/3 igual pra cada um
        # dos três) é o que faz esse piso deixar de dominar cedo o
        # bastante pra etapa atual (a que pede Expanding, ex.: Etapa 6)
        # realmente crescer com a janela -- o preço é os espaçadores de
        # centralização ficarem proporcionalmente menores nas etapas mais
        # simples/curtas, mas ainda existem (não travam a 0).
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
        self._etapas = [
            DadosAlunoStep(),
            AnamneseStep(),
            ObjetivoPrincipalStep(),
            FrequenciaTreinoStep(),
            HistoricoSaudeStep(),
            AvaliacaoFisicaStep(),
        ]

        self._stack = QStackedWidget()
        for etapa in self._etapas:
            self._stack.addWidget(etapa)
        layout_raiz.addWidget(self._stack, stretch=12)

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
        self._notificar_entrada_etapa()

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
            self._notificar_entrada_etapa()
        else:
            self._salvar_aluno()

    def _notificar_entrada_etapa(self) -> None:
        """Avisa a etapa que acabou de ficar visível, se ela quiser reagir a
        dados de etapas anteriores (ver `ao_entrar` no topo do arquivo)."""
        etapa_atual = self._etapas[self._etapa_atual]
        ao_entrar = getattr(etapa_atual, "ao_entrar", None)
        if ao_entrar is not None:
            ao_entrar(self._dados_coletados)

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
