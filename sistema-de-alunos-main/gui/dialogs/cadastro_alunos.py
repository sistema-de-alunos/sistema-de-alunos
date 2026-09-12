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

import inspect
from pathlib import Path
from typing import Dict, Optional

from core.qt_core import (
    QByteArray,
    QButtonGroup,
    QColor,
    QComboBox,
    QDate,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QIcon,
    QKeySequence,
    QLabel,
    QLineEdit,
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
        # `self.campo` normalmente É o QLineEdit/QComboBox (Nome/Idade/Sexo
        # etc.) -- mas pode ser um wrapper que só EMBRULHA um deles junto de
        # outro widget ao lado (ex.: o sufixo fixo "m" da Altura). Nesse
        # caso, estiliza o campo de verdade lá dentro, não o wrapper (que
        # não tem borda/fundo próprios) -- comportamento aditivo, não muda
        # nada para quem já passava o QLineEdit/QComboBox direto.
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
            # A causa do dropdown "invisível" é a QComboBox herdar a paleta
            # escura do sistema para o popup (QAbstractItemView) enquanto o
            # campo fechado usa cores claras definidas aqui. Sem estilizar
            # explicitamente QAbstractItemView (e seus itens/hover/seleção),
            # o Qt usa a paleta padrão do SO para a lista suspensa, que no
            # Windows costuma ficar com texto claro sobre fundo claro.
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


class _CampoAlturaMascarada(QLineEdit):
    """QLineEdit com máscara de entrada EM TEMPO REAL para a altura, no
    formato METROS.CENTÍMETROS -- o personal digita só números ("186") e o
    campo já mostra "1.86" a cada tecla, sem precisar digitar "." nem ",".

    A ideia (mesmo princípio de máscara de valor monetário: dígitos entram
    pela direita, o separador decimal é sempre inserido pela própria
    máscara): a cada edição, extrai só os dígitos já digitados (ignorando
    o "." que a própria máscara pôs ali antes -- ele nunca conta como
    dígito) e reformata do zero -- os 2 últimos dígitos são sempre as casas
    decimais, o que sobrar (no máximo 1, altura cabe em 0-9 metros e
    poucos) é a parte inteira:

        ""    -> ""
        "1"   -> "1"
        "18"  -> "1.8"
        "186" -> "1.86"
        "1867"-> "1.86" (4º dígito ignorado -- só 3 fazem sentido pra altura)

    Conectado a `textEdited` (não `textChanged`): esse sinal só dispara
    numa edição de verdade do usuário, nunca por causa do nosso próprio
    `setText` de reformatação -- é o que evita o loop infinito "edita ->
    reformata -> dispara sinal de novo -> reformata de novo -> ..." sem
    precisar bloquear sinais manualmente.
    """

    _MAX_DIGITOS = 3  # 1 casa inteira + 2 decimais -- ver docstring acima

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxLength(4)  # "d.dd" -- teto redundante, a máscara já limita sozinha
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

        # setText() dispara textChanged, mas não textEdited (ver docstring
        # da classe) -- reentrada seria só um problema se estivéssemos
        # ouvindo textChanged aqui.
        self.setText(novo_texto)
        self.setCursorPosition(len(novo_texto))


class DadosAlunoStep(QWidget):
    """Etapa 1 do cadastro: nome completo, idade, sexo e altura."""

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

        # Altura do aluno (m) -- dado permanente do cadastro (como idade e
        # sexo), não uma medida por avaliação. Usada pelo cálculo de
        # composição corporal na Etapa 7 (método RFM, ver ComposicaoCorporalStep).
        # Formato oficial: METROS.CENTÍMETROS (ex.: "1.75" = 1,75 m = 175 cm,
        # ver core.validators.validar_altura) -- o personal digita só
        # números ("186") e `_CampoAlturaMascarada` já mostra "1.86" em
        # tempo real (ver essa classe acima). O "m" ao lado é só indicação
        # de unidade, um QLabel fixo, NUNCA parte do texto digitado/validado
        # no QLineEdit (por isso os dois em um wrapper próprio, e não direto
        # em `_CampoFormulario` -- ver o suporte a wrapper em `_marcar_campo`).
        self._campo_altura = _CampoAlturaMascarada()
        self._campo_altura.setPlaceholderText("1.75")
        # Ao sair do campo, normaliza pro padrão oficial (2 casas decimais)
        # os casos incompletos que a máscara sozinha não fecha -- ex.: o
        # personal digitou só "1" (mostra "1") e trocou de campo antes de
        # completar os 3 dígitos; aqui vira "1.00". Reusa `validar_altura`
        # em vez de duplicar a formatação.
        self._campo_altura.editingFinished.connect(self._formatar_altura)

        # Sem sufixo "m" ao lado (removido -- aparecia desalinhado/quebrado
        # visualmente): o campo vai direto pro `_CampoFormulario`, igual a
        # Nome/Idade/Sexo acima, ocupando sozinho a largura inteira do
        # cartão. Não é preciso reservar espaço pra unidade em lugar nenhum
        # -- o rótulo "Altura:" já deixa a unidade implícita, mesmo padrão
        # de "Idade:" (anos) e "Peso (kg)" nas outras etapas.
        self._grupo_altura = _CampoFormulario(
            "Altura:",
            self._campo_altura,
            tamanho_fonte_label=15,
            tamanho_fonte_campo=16,
        )
        layout_cartao.addWidget(self._grupo_altura)

        layout_raiz.addWidget(cartao)

        # Tab entre os campos segue a ordem natural em que foram criados.
        self.setTabOrder(self._campo_nome, self._campo_idade)
        self.setTabOrder(self._campo_idade, self._campo_sexo)
        self.setTabOrder(self._campo_sexo, self._campo_altura)

    def obter_dados_validados(self):
        """Valida os campos; retorna um dict com os dados ou None se inválido."""
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

    def _formatar_altura(self) -> None:
        """Normaliza a altura pro padrão oficial ao sair do campo -- sempre
        2 casas decimais e ponto, nunca o "1,7"/"1.8" cru que o personal
        pode ter digitado (ver especificação em `validar_altura`). Não
        mexe no texto se o valor ainda for inválido/incompleto -- o erro
        (se houver) só aparece ao tentar avançar, em `obter_dados_validados`.
        """
        altura_m, erro = validar_altura(self._campo_altura.text())
        if erro is None:
            self._campo_altura.setText(f"{altura_m:.2f}")

    def limpar(self) -> None:
        self._campo_nome.clear()
        self._campo_idade.clear()
        self._campo_sexo.setCurrentIndex(0)
        self._campo_altura.clear()
        self._grupo_nome.limpar_erro()
        self._grupo_idade.limpar_erro()
        self._grupo_sexo.limpar_erro()
        self._grupo_altura.limpar_erro()

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


def _cabecalho_bloco_medidas(texto: str, *, centralizado: bool = False) -> QFrame:
    """Faixa azul escura de topo de um bloco de medidas (ex.: "Circunferência
    Parte Superior (MASC)") -- mesmo tom do banner usado no topo da etapa,
    mas arredondada só em cima para se fundir com o cartão que a envolve.
    Por padrão o texto fica à esquerda e centralizado verticalmente pelas
    margens simétricas (12px em cima/embaixo) do layout de uma linha só;
    `centralizado=True` (usado pela Etapa 7) também centraliza o texto
    horizontalmente, sem afetar quem já chama esta função sem o parâmetro.
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
    """Etapa 6 do cadastro: circunferências do aluno, em avaliações
    dinâmicas, com boneco anatômico interativo ao lado.

    "Avaliações dinâmicas" é o mesmo mecanismo já usado pela Etapa 7 --
    ver `_criar_tabela_widgets`/`_adicionar_coluna_tabela`: a tabela
    começa com uma única coluna (uma avaliação), e cada clique no botão
    "+" acrescenta outra, sem tocar nas colunas já existentes.

    O boneco não guarda estado próprio de avaliação: ele só reflete, em
    tempo real, quais REGIÕES têm ao menos uma medida preenchida em
    QUALQUER avaliação (coluna) -- preencher ou apagar uma medida em
    qualquer coluna já atualiza o destaque sozinho, sem seleção separada
    para sincronizar. Clicar numa região do boneco foca o campo daquela
    região na avaliação mais recente (`self._coluna_ativa`) -- a que o
    personal provavelmente está preenchendo agora.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Quantidade ATUAL de colunas (avaliações) -- começa em 1 (nunca
        # várias colunas vazias pré-criadas) e cresce a cada clique no
        # botão "+" (`_adicionar_nova_avaliacao`).
        self._num_colunas = _NUM_COLUNAS_INICIAL
        # Índice da última coluna criada -- ver docstring da classe.
        self._coluna_ativa = 0

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

        # Card com a tabela de circunferências (esquerda) + boneco
        # interativo (direita).
        cartao = _criar_cartao()
        # Antes, o cartão nunca precisava disto: sem o QScrollArea abaixo, o
        # tamanho natural da tabela sempre excedia o espaço disponível, e o
        # cartão acabava ocupando tudo por pura falta de alternativa. Agora
        # que a tabela pode ficar compacta e rolar, o cartão precisa de
        # Expanding explícito para continuar preenchendo a altura disponível
        # -- do contrário ele encolheria para o tamanho natural do boneco
        # (bem menor) e sobraria um vão vazio embaixo.
        cartao.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout_cartao = QHBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(24)

        self._tabela_circunferencias, self._campos_circunferencias = _criar_tabela_widgets(
            _LINHAS_CIRCUNFERENCIAS
        )

        # Botão "+" -- único mecanismo desta etapa para criar uma nova
        # avaliação: um clique acrescenta uma coluna contendo TODOS os
        # campos de circunferência de uma vez (nunca um botão por campo,
        # nunca uma coluna "solta" só para a data). Fica no cabeçalho do
        # card, ao lado da linha "Datas:" -- mesmo estilo/posição já usados
        # pelo botão equivalente da Etapa 7.
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

        # QScrollArea: numa janela pequena, as 16 linhas da tabela (data +
        # 15 medidas) podem exceder a altura disponível -- rolar o excesso
        # evita que o card fique espremido ou corte conteúdo (mesma ideia
        # já usada pela coluna esquerda da Etapa 7).
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

        # Conecta a coluna inicial (0) ao recálculo do destaque do boneco --
        # mesma conexão que cada coluna nova recebe em
        # `_adicionar_nova_avaliacao`. "datas" fica de fora de propósito:
        # não corresponde a nenhuma região do boneco (ver _REGIAO_POR_CHAVE).
        self._conectar_coluna_boneco(
            [(chave, self._campos_circunferencias[chave][0]) for chave in _REGIAO_POR_CHAVE]
        )
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

    # -- Avaliações dinâmicas: coluna nova ---------------------------------

    def _conectar_coluna_boneco(self, pares_chave_widget) -> None:
        """Liga o campo de UMA medida (de UMA coluna/avaliação) ao
        recálculo do destaque do boneco -- usada tanto pela coluna inicial
        (`__init__`) quanto por cada coluna nova (`_adicionar_nova_avaliacao`).
        """
        for _chave, widget in pares_chave_widget:
            widget.textChanged.connect(self._recalcular_destaques)

    def _adicionar_nova_avaliacao(self) -> None:
        """Botão "+": cria uma coluna nova contendo TODOS os campos de
        circunferência de uma vez -- nunca uma coluna "solta" só para a
        data. Os dados das colunas já existentes não são tocados.
        """
        novos = _adicionar_coluna_tabela(
            self._tabela_circunferencias, self._campos_circunferencias, _LINHAS_CIRCUNFERENCIAS
        )
        self._conectar_coluna_boneco(
            [(chave, widget) for chave, widget in novos if chave in _REGIAO_POR_CHAVE]
        )

        self._num_colunas += 1
        self._coluna_ativa = self._num_colunas - 1

        # Rola até a coluna recém-criada -- sem isto, com muitas colunas já
        # existentes, a nova nasceria fora da área visível.
        barra = self._tabela_circunferencias.horizontalScrollBar()
        barra.setValue(barra.maximum())

    def _recalcular_destaques(self) -> None:
        # Uma região acende se QUALQUER avaliação (coluna) tem ao menos uma
        # medida preenchida para ela -- o boneco mostra o histórico
        # completo do aluno, não só a avaliação mais recente.
        regioes_ativas = {
            regiao
            for chave, regiao in _REGIAO_POR_CHAVE.items()
            if any(campo.text().strip() for campo in self._campos_circunferencias[chave])
        }
        # Os dois bonecos usam os mesmos ids de região (ver
        # IDS_REGIOES_MASCULINO/IDS_REGIOES_FEMININO) — atualizar os dois
        # mantém o que não está visível em dia, então trocar de sexo em
        # `ao_entrar` nunca mostra um boneco com destaques desatualizados.
        self._corpo_masculino.definir_regioes_selecionadas(regioes_ativas)
        self._corpo_feminino.definir_regioes_selecionadas(regioes_ativas)

    def _focar_campo_da_regiao(self, regiao_id: str) -> None:
        """Interação inversa: clicar no boneco foca o campo daquela região
        na avaliação mais recente (`self._coluna_ativa`), pronto para o
        personal digitar."""
        for chave, id_regiao in _REGIAO_POR_CHAVE.items():
            if id_regiao == regiao_id:
                campo = self._campos_circunferencias[chave][self._coluna_ativa]
                campo.setFocus()
                campo.selectAll()
                return

    def obter_dados_validados(self):
        """Sem campo obrigatório: sempre retorna as avaliações preenchidas
        até agora -- uma lista por medida, uma posição por avaliação/coluna
        (mesmo formato já usado pela Etapa 7 para dobras/peso/composição).
        """

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
        # Volta ao estado inicial de 1 coluna -- sem isto, um novo cadastro
        # herdaria as colunas extras que o personal tivesse criado no
        # cadastro anterior.
        _remover_colunas_extras_tabela(self._tabela_circunferencias, self._campos_circunferencias)
        self._num_colunas = _NUM_COLUNAS_INICIAL
        self._coluna_ativa = 0
        for widgets in self._campos_circunferencias.values():
            for widget in widgets:
                _limpar_widget(widget)
        self._recalcular_destaques()


# -- Etapa 7: Composição corporal -----------------------------------------

# Caminho do arquivo já existente no projeto (raiz do repositório, ao lado de
# main.py) -- reaproveitado como está, sem gerar/duplicar a imagem.
_CAMINHO_IMAGEM_MUSCULO_GORDURA = str(
    Path(__file__).resolve().parent.parent.parent / "musculogordura.png"
)

# Teto genérico para as circunferências (cm) -- mesmo limite já usado pelo
# QDoubleValidator da versão anterior desta tabela, reaproveitado aqui.
_LIMITE_MEDIDA = 300.0

# (chave, rótulo exibido na linha da tabela, tipo de célula, teto numérico).
# tipo: "data" (QDateEdit dd/MM/aaaa) | "numero" (QLineEdit com validador,
# aceita vírgula ou ponto) | "resultado" (QLabel calculado, somente leitura).
# "datas" é sempre a primeira linha de cada tabela.
#
# Tabela ÚNICA de circunferências da Etapa 6 (`AvaliacaoFisicaStep`), com
# avaliações dinâmicas (uma coluna por avaliação, criada sob demanda pelo
# botão "+"). Mesmas 15 medidas que antes viviam em dois cards estáticos de
# campo único (Circunferência Parte Superior/Inferior + Braços) -- chaves e
# rótulos preservados (ver `_REGIAO_POR_CHAVE`, que o boneco anatômico
# interativo também usa para destacar regiões preenchidas). NÃO confundir
# com as dobras cutâneas REAIS (mm) usadas no cálculo de composição
# corporal (protocolo de Jackson & Pollock de 7 dobras, Etapa 7) -- essas
# são uma tabela própria e independente, ver `_LINHAS_DOBRAS_REAIS` abaixo.
# Nenhuma medida daqui entra nesse cálculo.
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

# Teto plausível para uma dobra cutânea isolada, em milímetros -- generoso o
# bastante para qualquer dobra real (a soma das 7 raramente passa de ~200mm
# em protocolos clínicos), mas ainda bloqueia digitação de valores absurdos
# (ex.: "999").
_LIMITE_DOBRA_MM = 100.0

# As 7 dobras cutâneas do protocolo de Jackson & Pollock (JP7) -- em
# MILÍMETROS, nunca confundir com as circunferências (cm) da tabela acima.
# Chaves, rótulos E ORDEM reproduzem exatamente a planilha de referência
# (ADIPÔMETRO-----MASCULINO.xlsx, linhas 76-82: Tríceps, Peito, Axilar
# média, Subescapular, Abdominal, Supra-iliaca, Coxa -- inclusive a grafia
# "Supra-iliaca" sem acento, igual à planilha). A ordem não muda o
# resultado (a soma é comutativa), só a leitura/preenchimento na tela.
# "dobra_abdominal"/"coxa_dobra" (em vez de "abdominal"/"coxa_d"/"coxa_e")
# evita colidir com as chaves já usadas pelas circunferências/Avaliação
# Física, que são medidas DIFERENTES do mesmo nome comum ("Abdominal",
# "Coxa").
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

# Linhas de fato exibidas na tabela "Dobras Cutâneas (mm)" da Etapa 7: a
# própria linha "Datas:" (tipo "data", editável) na frente das 7 dobras.
# Diferente de antes -- quando essa data só espelhava a já digitada na
# extinta tabela "Circunferências (Reavaliação)", removida desta etapa --,
# agora cada avaliação da Etapa 7 tem sua PRÓPRIA data, independente da
# Etapa 6 (as duas etapas nunca copiam valores uma para a outra). Usada só
# para MONTAR a tabela (`_criar_tabela_widgets`/`_adicionar_coluna_tabela`)
# -- `_CHAVES_DOBRAS_7` acima continua definida só a partir das 7 dobras
# reais, sem "datas", então o cálculo JP7 nunca tenta somar uma data como
# se fosse uma dobra.
_LINHAS_DOBRAS_COM_DATA = [("datas", "Datas:", "data", None)] + list(_LINHAS_DOBRAS_REAIS)

_LINHAS_PESO = [
    ("peso", "Peso (kg)", "numero", _LIMITE_MEDIDA),
]
# "datas" aqui é "resultado" (não "data" editável) de propósito: a data de
# cada avaliação já é digitada uma única vez, na tabela de Dobras Cutâneas
# (`_LINHAS_DOBRAS_COM_DATA`) -- esta apenas espelha a mesma data em cada
# coluna (ver `_recalcular_composicao`), sem virar uma segunda fonte de
# verdade que o personal precisaria preencher (e manter sincronizada) de
# novo aqui.
#
# Linhas e ORDEM reproduzem exatamente a seção "Composição Corporal" da
# planilha de referência (ADIPÔMETRO-----MASCULINO.xlsx, linhas 87-92:
# Datas, Massa Magra, Massa Gorda, % Gordura Corporal, Densidade Corporal
# -- a planilha tem uma 2ª linha de "% Gordura Corporal", a calculada sem
# proteção, mas usa o mesmo rótulo da protegida; aqui ela não vira outra
# linha na tela -- fica só na dica/tooltip do campo, ver
# `_recalcular_composicao`). Nada de "Peso Corporal" ou "Soma das 7
# Dobras" aqui: a planilha não tem essas linhas nesta seção (peso já tem
# sua própria linha logo acima, ver `_LINHAS_PESO`; a soma é só uma conta
# interna da fórmula de densidade, nunca um resultado próprio) -- ver
# especificação, seção 1 e 15 ("não inventar campos desnecessários").
# Esta ORDEM DE EXIBIÇÃO é a da planilha (resultados primeiro, densidade
# por último); o FLUXO DE CÁLCULO internamente continua
# soma -> densidade -> % -> proteção -> massa gorda -> massa magra (ver
# `_calcular_composicao_jp7`) -- são coisas independentes.
_LINHAS_COMPOSICAO_CORPORAL = [
    ("datas", "Datas:", "resultado", None),
    ("massa_magra", "Massa Magra (kg)", "resultado", None),
    ("massa_gorda", "Massa Gorda (kg)", "resultado", None),
    ("percentual_gordura", "% Gordura Corporal", "resultado", None),
    ("densidade_corporal", "Densidade Corporal (g/cm³)", "resultado", None),
]

# A Etapa 7 é uma tabela de reavaliações DINÂMICA (ver especificação): cada
# coluna é uma avaliação independente do aluno, criada sob demanda pelo
# botão "+" (`ComposicaoCorporalStep._adicionar_nova_avaliacao`) -- nunca
# um número fixo pré-criado. Começa com uma única coluna; `self._num_colunas`
# (em `ComposicaoCorporalStep`) é a contagem atual, usada em vez desta
# constante em todo lugar que precisa iterar "todas as colunas existentes".
_NUM_COLUNAS_INICIAL = 1
# Largura mínima de uma coluna de DADOS (não a de rótulos, ver
# `_LARGURA_ROTULO_TABELA` abaixo) -- com poucas colunas elas se esticam
# para preencher o cartão (QHeaderView.Stretch, ver `_criar_tabela_widgets`)
# igual já acontecia antes; a partir daqui elas param de encolher e a
# tabela passa a rolar horizontalmente (nunca comprimir os campos --
# especificação, seção 13).
_LARGURA_MINIMA_COLUNA_DADOS = 130
_ALTURA_LINHA_TABELA = 36
# Largura fixa do cabeçalho vertical (coluna de rótulos) -- igual em todas as
# tabelas desta etapa, para que as colunas de dados de todas elas (Dobras
# Cutâneas, Peso, Composição corporal) fiquem alinhadas verticalmente.
_LARGURA_ROTULO_TABELA = 190

# Sentinela para "nenhuma data preenchida ainda" -- QDateEdit não tem um
# estado nulo nativo, então usamos setSpecialValueText: sempre que a data do
# campo é exatamente esta, o widget mostra um espaço em branco no lugar de
# uma data real (ver `_criar_campo_data`).
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
    QDateEdit {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 2px;
        font-size: 13px;
        font-weight: 600;
        color: {Cores.TEXTO_PRIMARIO};
    }}
    QDateEdit:focus {{ background-color: {Cores.FUNDO}; border: 1px solid {Cores.AZUL_PRIMARIO}; }}
    QDateEdit::drop-down {{ border: none; width: 18px; }}
"""
_ESTILO_CAMPO_DATA_ERRO = f"""
    QDateEdit {{
        background-color: {Cores.ERRO_FUNDO};
        border: 1px solid {Cores.ERRO};
        border-radius: 4px;
        padding: 2px;
        font-size: 13px;
        font-weight: 600;
        color: {Cores.TEXTO_PRIMARIO};
    }}
    QDateEdit::drop-down {{ border: none; width: 18px; }}
"""


def _marcar_campo_erro(campo: QWidget, com_erro: bool) -> None:
    """Alterna a borda vermelha de erro num campo desta etapa (QLineEdit
    numérico ou QDateEdit) -- mesma ideia de `_CampoFormulario._marcar_campo`
    usada nas demais etapas, só que os campos aqui vivem dentro de células de
    tabela em vez de um `_CampoFormulario` próprio.
    """
    if isinstance(campo, QDateEdit):
        campo.setStyleSheet(_ESTILO_CAMPO_DATA_ERRO if com_erro else _ESTILO_CAMPO_DATA_NORMAL)
    else:
        campo.setStyleSheet(_ESTILO_CAMPO_NUMERICO_ERRO if com_erro else _ESTILO_CAMPO_NUMERICO_NORMAL)


def _criar_validador_numerico(maximo: float, casas_decimais: int = 1) -> QRegularExpressionValidator:
    """Só deixa passar dígitos e, opcionalmente, UMA casa decimal separada
    por vírgula OU ponto -- letra nenhuma chega a ser digitada (a tecla é
    simplesmente ignorada). A conversão pra número (`_texto_para_numero`, já
    usada pela Etapa 6) normaliza os dois separadores para o mesmo padrão
    antes de qualquer cálculo, então "10,5" e "10.5" viram o mesmo valor.
    """
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
    # Sem placeholder "0,0": numa tabela de 4 colunas quase sempre vazias,
    # um texto de exemplo em todas as células vira ruído visual e pode ser
    # lido de relance como "zero já preenchido" -- a própria célula em
    # branco (com a borda da tabela) já deixa claro que está vazia.
    _marcar_campo_erro(campo, com_erro=False)
    return campo


class _CampoDataMascarada(QDateEdit):
    """QDateEdit com a digitação corrigida -- em tudo mais (calendário
    popup, `.date()`, `.dateChanged`, o valor interno sempre um `QDate` de
    verdade, a validação de dia/mês/ano/ano bissexto -- datas impossíveis
    como 31/02 ou mês 13 são corrigidas automaticamente pelo próprio Qt
    conforme o personal digita, nunca ficam armazenadas) é o `QDateEdit`
    nativo do Qt, sem reimplementar nada disso. Dois bugs foram isolados e
    corrigidos (reproduzem com qualquer QDateEdit, não são específicos
    deste projeto):

    1) `setSpecialValueText(" ")` (usado pra mostrar o campo "vazio"
       enquanto a data ainda é a sentinela -- ver `_DATA_SENTINELA`
       abaixo): quando o valor atual ESTÁ no mínimo (exatamente o caso de
       um campo vazio), a digitação inteira quebra -- a primeira tecla não
       é registrada e a data nunca sai do valor mínimo. Corrigido em
       `focusInEvent`/`focusOutEvent`: o texto especial só fica ligado
       enquanto o campo não está sendo editado -- some assim que o campo
       recebe foco, de QUALQUER forma (clique, Tab, ou a janela/etapa
       simplesmente aparecer com este campo já sendo o foco atual --
       `Qt.ActiveWindowFocusReason`) e volta ao perder o foco sem nada
       digitado. Uma versão anterior restringia essa limpeza a só alguns
       motivos de foco (clique/Tab), excluindo justamente
       `ActiveWindowFocusReason` -- exatamente o motivo que o Qt usa
       quando este campo já é o foco corrente no momento em que a janela
       fica ativa (ex.: primeira vez que uma etapa com "Datas:" aparece).
       Sem tratar esse caso, o personal via a digitação quebrar bem no
       campo que mais precisa funcionar de primeira, obrigando-o a usar
       clique/scroll manual em cada seção -- daí não restringir mais por
       motivo algum.

    2) Apagar uma seção (dia/mês/ano) até ficar vazia com Backspace/Delete
       deixa essa seção "suja": a primeira tecla digitada ali depois some
       igual ao bug 1 (mesma causa raiz -- Qt trata uma seção vazia "no
       meio" do campo diferente de um campo totalmente vazio do zero).
       Corrigido em `keyPressEvent`: sempre que Backspace/Delete ou
       Ctrl+A esvaziam a seção atual, a correção reresete o campo inteiro
       e volta pra seção do Dia -- equivalente a "começar a digitar uma
       data nova do zero" (que já funciona perfeitamente), satisfazendo
       "apagar; corrigir; Backspace; selecionar o conteúdo; substituir a
       data; digitar uma nova data por cima" (especificação, seção 3).
    """

    def focusInEvent(self, evento) -> None:
        self.setSpecialValueText("")
        self.setSelectedSection(QDateEdit.DaySection)
        super().focusInEvent(evento)

    def focusOutEvent(self, evento) -> None:
        super().focusOutEvent(evento)
        if self.date() == _DATA_SENTINELA:
            self.setSpecialValueText(" ")

    def keyPressEvent(self, evento) -> None:
        if evento.matches(QKeySequence.SelectAll):
            # "Selecionar o conteúdo; substituir a data" (especificação,
            # seção 3) -- Ctrl+A não tem uma "seleção" tradicional num
            # QDateEdit (não é texto livre); tratamos como "limpar tudo e
            # já deixar pronto pra digitar uma data nova do zero".
            self.setDate(_DATA_SENTINELA)
            self.setSelectedSection(QDateEdit.DaySection)
            evento.accept()
            return
        super().keyPressEvent(evento)
        if evento.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            if self.sectionText(self.currentSection()) == "":
                self.setDate(_DATA_SENTINELA)
                self.setSelectedSection(QDateEdit.DaySection)


def _criar_campo_data() -> QDateEdit:
    campo = _CampoDataMascarada()
    campo.setDisplayFormat("dd/MM/yyyy")
    # Calendário nativo do Qt pra seleção visual (clicar no campo ou na
    # setinha abre o popup com navegação de mês/ano) -- ver especificação,
    # seção 4. Selecionar um dia no calendário atualiza `.date()`/o texto
    # exibido exatamente como digitar; a digitação numérica corrigida
    # acima e o calendário são só dois jeitos de preencher o mesmo campo.
    campo.setCalendarPopup(True)
    campo.setAlignment(Qt.AlignCenter)
    campo.setMinimumDate(_DATA_SENTINELA)
    # Texto mostrado quando a data ainda é a sentinela -- ou seja, campo
    # "vazio" pro usuário, mesmo o QDateEdit sempre guardando uma QDate real.
    # (Ligado/desligado durante a edição por `_CampoDataMascarada` acima.)
    campo.setSpecialValueText(" ")
    campo.setDate(_DATA_SENTINELA)
    _marcar_campo_erro(campo, com_erro=False)
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
    """Widget de UMA célula de dado, de acordo com o tipo da linha (mesmos
    três tipos de `_LINHAS_*` em todo o arquivo) -- usada tanto na
    construção inicial da tabela (`_criar_tabela_widgets`) quanto ao
    acrescentar uma coluna nova depois (`_adicionar_coluna_tabela`), pra
    uma coluna criada pelo botão "+" nascer EXATAMENTE igual às originais.
    """
    if tipo == "data":
        return _criar_campo_data()
    if tipo == "resultado":
        return _criar_label_resultado()
    return _criar_campo_numerico(maximo)


def _criar_tabela_widgets(especificacoes, num_colunas: int = _NUM_COLUNAS_INICIAL):
    """Tabela real (QTableWidget) cujas células são widgets de verdade --
    `QDateEdit`, `QLineEdit` validado ou `QLabel` calculado -- via
    `setCellWidget`, em vez de texto solto: é isso que impede digitar letra
    num campo numérico e mostra a data já formatada como dd/mm/aaaa. Devolve
    (tabela, matriz), onde `matriz[chave]` é a lista de widgets daquela
    linha, um por coluna, na mesma ordem de `especificacoes`.

    Começa com `num_colunas` (1 por padrão -- especificação, seção 1);
    colunas extras são acrescentadas depois, sob demanda, por
    `_adicionar_coluna_tabela` (nunca criadas vazias de antemão).
    """
    rotulos = [rotulo for _chave, rotulo, _tipo, _maximo in especificacoes]
    tabela = QTableWidget(len(especificacoes), num_colunas)
    tabela.setVerticalHeaderLabels(rotulos)
    tabela.horizontalHeader().hide()
    tabela.verticalHeader().setFixedWidth(_LARGURA_ROTULO_TABELA)
    tabela.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    tabela.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
    tabela.verticalHeader().setDefaultSectionSize(_ALTURA_LINHA_TABELA)
    # Stretch + largura mínima: com poucas colunas elas se esticam pra
    # preencher o cartão (visual de sempre); a partir do ponto em que não
    # cabe mais um mínimo de `_LARGURA_MINIMA_COLUNA_DADOS` por coluna, o Qt
    # para de encolher e passa a rolar horizontalmente sozinho (por isso o
    # scroll horizontal abaixo agora fica "as needed", não mais desligado --
    # especificação, seção 13).
    tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    tabela.horizontalHeader().setMinimumSectionSize(_LARGURA_MINIMA_COLUNA_DADOS)
    # A edição acontece sempre através do próprio widget da célula (o
    # QLineEdit/QDateEdit já é interativo) -- não faz sentido o
    # QTableWidget também tentar abrir seu próprio editor por cima.
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

    # Sem QScrollArea própria (a coluna inteira já rola, ver
    # ComposicaoCorporalStep) -- a tabela deve ter exatamente a altura do
    # seu conteúdo, nunca mais nem menos.
    tabela.setFixedHeight(tabela.verticalHeader().length() + 2 * tabela.frameWidth() + 2)
    return tabela, matriz


def _adicionar_coluna_tabela(
    tabela: QTableWidget, matriz: Dict[str, list], especificacoes
) -> list:
    """Acrescenta UMA coluna nova a uma tabela já construída (mesmo tipo de
    widget de cada linha, igual `_criar_tabela_widgets` faria) -- usada
    pelo botão "+" (`ComposicaoCorporalStep._adicionar_nova_avaliacao`).

    Devolve a lista `[(chave, widget), ...]` dos widgets recém-criados
    (mesma ordem de `especificacoes`), pra quem chamou conectar os sinais
    de recálculo só nessa coluna nova -- as colunas já existentes (e seus
    dados) não são tocadas.
    """
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
    """Devolve uma tabela ao estado inicial de 1 coluna só -- usada por
    `ComposicaoCorporalStep.limpar()` ao começar um novo cadastro (ver
    especificação, seção 1: a Etapa 7 sempre abre com 1 coluna).
    """
    while tabela.columnCount() > 1:
        tabela.removeColumn(tabela.columnCount() - 1)
    for lista_widgets in matriz.values():
        del lista_widgets[1:]


def _valor_data(campo: QDateEdit) -> Optional[str]:
    """dd/MM/aaaa se preenchido (diferente da sentinela), None se vazio."""
    if campo.date() == _DATA_SENTINELA:
        return None
    return campo.date().toString("dd/MM/yyyy")


def _formatar_numero(valor: float, casas: int = 1) -> str:
    """Mesmo padrão vírgula da interface (ver `_criar_validador_numerico`)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _limpar_widget(widget: QWidget) -> None:
    """Restaura um widget de célula (data/número/resultado) ao estado vazio,
    de acordo com seu tipo -- usado por `ComposicaoCorporalStep.limpar()`.
    """
    if isinstance(widget, QDateEdit):
        widget.setDate(_DATA_SENTINELA)
        # Se o campo já tinha sido editado antes (ver `_CampoDataMascarada`),
        # o texto especial "vazio" pode estar desligado -- sem isto, limpar
        # voltaria a data pra sentinela mas continuaria MOSTRANDO
        # "01/01/2000" em vez de em branco.
        widget.setSpecialValueText(" ")
    elif isinstance(widget, QLabel):
        widget.setText("—")
        widget.setToolTip("")
    else:
        widget.clear()


def _criar_card_tabela(
    titulo: str, *widgets: QWidget, widget_extra_cabecalho: Optional[QWidget] = None
) -> QFrame:
    """Cartão com faixa azul (título centralizado) + conteúdo empilhado --
    empacota uma ou mais tabelas de avaliação (widgets QTableWidget) sob um
    único cabeçalho.

    `widget_extra_cabecalho` é opcional -- usado pelo botão "+" de nova
    avaliação dos cards de Circunferências (Etapa 6) e Dobras Cutâneas
    (Etapa 7): fica alinhado à direita do cabeçalho, sem deslocar o título
    (que continua centralizado). Quem não passa esse argumento tem o
    cabeçalho EXATAMENTE igual a antes (`_cabecalho_bloco_medidas` sem
    alterações).
    """
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
        # Dois addStretch (antes E depois do título) mantêm o título
        # centralizado na faixa -- mesmo efeito visual de
        # `centralizado=True` -- enquanto o botão fica sozinho, colado à
        # direita, sem puxar o título pro lado.
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
    """QLabel cujo pixmap acompanha o redimensionamento do widget mantendo
    a proporção original -- usada para `musculogordura.png` ao lado da
    tabela, sem esticar a imagem horizontal/verticalmente de forma
    independente (mesma ideia de `_retangulo_imagem` em corpo_interativo.py,
    só que via QLabel/QPixmap.scaled em vez de paintEvent manual).
    """

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


# -- % de gordura corporal: protocolo de Jackson & Pollock de 7 dobras ----
#
# Reproduz exatamente a planilha de referência ADIPÔMETRO-----MASCULINO.xlsx
# (aba "Planilha1", seções "Dobras Cutâneas" linhas 76-82 e "Composição
# Corporal" linhas 88-92) -- NÃO usa RFM, cintura/altura nem qualquer
# circunferência: usa exclusivamente SEXO, IDADE, PESO e as 7 DOBRAS
# CUTÂNEAS (mm) de `_LINHAS_DOBRAS_REAIS` (Tríceps, Peito, Axilar média,
# Subescapular, Abdominal, Supra-iliaca, Coxa). As circunferências da
# tabela ao lado (Ombro/Tórax/Cintura/.../Panturrilha) continuam existindo
# só para acompanhamento -- nenhuma delas entra neste cálculo.
#
# Fluxo (equivalente às fórmulas das células C88:C92 da planilha, coluna
# por reavaliação):
#
#   S = soma das 7 dobras (mm)                        -- SUM(C76:C82)
#
#   Densidade corporal (C92):
#     Homem:  DC = 1.112   - 0.00043499×S + 0.00000055×S² - 0.00028826×idade
#     Mulher: DC = 1.097   - 0.00046971×S + 0.00000056×S² - 0.00012828×idade
#
#   % Gordura calculada (C91, equação de Siri) = ((4.95 / DC) - 4.5) × 100
#     (mesma forma de (495/DC)-450 -- só escrita com DC já em g/cm³)
#   % Gordura protegida (C90) = 0, se % Gordura calculada < 0; senão a
#     própria % Gordura calculada -- protege contra percentual negativo
#     num caso-limite. O valor bruto NÃO é apagado, só não alimenta as
#     massas abaixo.
#   Massa gorda (C89) = peso × (% Gordura protegida / 100)
#     ATENÇÃO: na planilha original essa célula referencia C91 (a
#     calculada, SEM proteção) em vez de C90 -- esse é o bug que este
#     sistema corrige; aqui sempre se usa a protegida.
#   Massa magra (C88) = peso - massa gorda
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
    """Composição corporal pelo protocolo JP7 + Siri (ver comentário acima).

    `dobras` é um dict chave (ver `_CHAVES_DOBRAS_7`) -> valor em mm. Retorna
    None se faltar sexo, idade, peso OU qualquer uma das 7 dobras, ou se o
    sexo não tiver equação JP7 definida (só Masculino/Feminino têm
    coeficientes clínicos publicados -- um cadastro antigo com "Outro" ou
    "Prefiro não informar", opções hoje removidas da Etapa 1, ver
    SEXO_OPCOES, cai nesse caso). Nunca calcula parcialmente nem assume 0
    para dado ausente.

    O percentual de gordura (Siri) pode sair negativo num caso-limite --
    isso é esperado da fórmula, não um erro de entrada (mesmo caso-limite
    que a planilha de referência trata nas linhas 90/91 de "% Gordura
    Corporal"). O valor bruto é preservado em "percentual" (pode vir
    negativo; nunca apagado/escondido), mas quem alimenta massa gorda/magra
    (e a tela) é sempre "percentual_protegido" (nunca menor que 0) -- a
    proteção é calculada aqui dentro, ANTES da massa gorda/magra, nunca
    depois (diferente da planilha original, cuja célula de massa gorda
    referencia a % calculada sem proteção -- ver comentário acima).
    """
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
    # Proteção contra percentual negativo (especificação, seção 7): o valor
    # bruto acima continua em "percentual" -- só não é usado dali pra
    # frente. Massa gorda e massa magra usam exclusivamente o protegido.
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
    """Etapa 7 do cadastro: dobras cutâneas, peso e composição corporal.

    Vem logo depois da Avaliação Física (Etapa 6, que cuida só das
    circunferências -- as duas etapas são independentes: nenhuma copia
    valores para a outra). A imagem músculo x gordura é a mesma nos dois
    casos, mas o CÁLCULO da composição corporal depende do sexo e da idade
    do aluno (protocolo de Jackson & Pollock de 7 dobras, ver
    `_calcular_composicao_jp7`) -- por isso, assim como a Etapa 6, esta
    etapa usa `ao_entrar` para ler esses dois dados já cadastrados na
    Etapa 1. A altura NÃO entra neste cálculo (a planilha de referência
    também não usa altura na Composição Corporal, só no IMC, calculado à
    parte) -- continua cadastrada normalmente na Etapa 1, só não é lida
    aqui. Circunferências também não entram neste cálculo (só as 7 dobras
    cutâneas, o peso e a idade/sexo).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Preenchidos por `ao_entrar` com sexo e idade já cadastrados na
        # Etapa 1 -- entram no protocolo JP7 (ver _calcular_composicao_jp7).
        # Diferente de peso/dobras, não são por coluna: o aluno tem um único
        # sexo/idade para todas as reavaliações desta etapa.
        self._sexo: Optional[str] = None
        self._idade: Optional[int] = None

        # Quantidade ATUAL de colunas (reavaliações) -- começa em 1 (nunca
        # várias colunas vazias pré-criadas, ver especificação, seção 1) e
        # cresce a cada clique no botão "+" (`_adicionar_nova_avaliacao`).
        # Fonte de verdade única pra "quantas colunas existem agora" em
        # `_recalcular_composicao`/`obter_dados_validados` -- em vez do
        # número fixo que existia antes.
        self._num_colunas = _NUM_COLUNAS_INICIAL

        # Mesmo ajuste da Etapa 6 (ver comentário lá): sem isto o
        # QStackedWidget do wizard trava a altura desta etapa no sizeHint,
        # ignorando o stretch que o wizard já reserva para o conteúdo.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        # Cabeçalho -- mesmo banner azul das demais etapas da anamnese.
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

        subtitulo_cabecalho = QLabel("Etapa 7: Composição corporal")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        # Card com tabelas (esquerda) + imagem músculo x gordura (direita) --
        # mesma divisão em duas colunas da Etapa 6 (tabela + boneco).
        cartao = _criar_cartao()
        cartao.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout_cartao = QHBoxLayout(cartao)
        layout_cartao.setContentsMargins(28, 24, 28, 24)
        layout_cartao.setSpacing(24)

        painel_esquerdo = QWidget()
        painel_esquerdo.setStyleSheet("background: transparent;")
        coluna_esquerda = QVBoxLayout(painel_esquerdo)
        coluna_esquerda.setContentsMargins(0, 0, 4, 0)
        # 28px entre os dois cards (Dobras Cutâneas / Composição corporal) --
        # nitidamente maior que o spacing interno de cada card (14px), para
        # lerem como blocos independentes dentro da mesma seção.
        coluna_esquerda.setSpacing(28)

        # Mensagem de validação ao avançar (ver `obter_dados_validados`) --
        # mesmo estilo do banner de erro geral do wizard, só que local a esta
        # etapa; hide() não reserva espaço, então não aparece vazio normalmente.
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

        # Dobras cutâneas de verdade (mm) -- únicas medidas usadas no
        # cálculo de composição corporal (protocolo JP7, ver
        # `_calcular_composicao_jp7`), com sua PRÓPRIA linha de "Datas:" na
        # frente (`_LINHAS_DOBRAS_COM_DATA`): esta etapa não tem mais uma
        # tabela de circunferências para espelhar a data dali (removida --
        # circunferências pertencem só à Etapa 6), então cada avaliação
        # daqui precisa da sua própria data, independente.
        self._tabela_dobras_reais, self._campos_dobras_reais = _criar_tabela_widgets(
            _LINHAS_DOBRAS_COM_DATA
        )

        # Botão "+" -- único mecanismo desta etapa para criar uma nova
        # avaliação: um clique cria a coluna nova, sincronizada, nas 3
        # seções restantes de uma vez (`_adicionar_nova_avaliacao`), nunca
        # um botão por seção. Fica no cabeçalho do card de Dobras Cutâneas
        # -- primeiro card da etapa, o mesmo que começa com a linha
        # "Datas:". Compacto (28x28, só o "+") pra não ocupar espaço à toa.
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

        # Peso fica numa tabela própria (linha separada da lista de dobras),
        # mas com a mesma largura de rótulo -- as colunas de dados de ambas
        # ficam alinhadas mesmo sendo dois QTableWidget diferentes.
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

        # As 3 tabelas desta etapa têm sempre o mesmo número de colunas,
        # criadas em sincronia (`_adicionar_nova_avaliacao`) -- por isso dá
        # pra manter o scroll horizontal das 3 alinhado mesmo rolando pra
        # ver colunas mais à direita.
        self._tabelas_reavaliacao = (
            self._tabela_dobras_reais,
            self._tabela_peso,
            self._tabela_composicao,
        )
        for tabela in self._tabelas_reavaliacao:
            tabela.horizontalScrollBar().valueChanged.connect(
                lambda valor, origem=tabela: self._sincronizar_scroll_horizontal(origem, valor)
            )

        # Data / Densidade / % Gordura / Massa Gorda / Massa Magra são
        # sempre recalculados a partir da Data, do Peso e das 7 Dobras da
        # MESMA coluna (mesma avaliação) -- qualquer mudança num desses
        # campos já atualiza os resultados na hora, sem precisar de um
        # botão "calcular" separado. Mesma conexão usada tanto na coluna
        # inicial (aqui) quanto em cada coluna nova
        # (`_adicionar_nova_avaliacao`) -- ver `_conectar_coluna_calculo`.
        coluna_inicial = _NUM_COLUNAS_INICIAL - 1  # sempre 0 -- só por clareza
        self._conectar_coluna_calculo(
            [(chave, self._campos_dobras_reais[chave][coluna_inicial])
             for chave, _r, _t, _m in _LINHAS_DOBRAS_COM_DATA],
            [(chave, self._campos_peso[chave][coluna_inicial]) for chave, _r, _t, _m in _LINHAS_PESO],
        )

        # Campo obrigatório (ver `obter_dados_validados`): corrigir o valor
        # já limpa o erro daquele campo específico e esconde a mensagem
        # geral, em vez de deixá-la presa na tela mesmo após corrigido.
        self._campos_peso["peso"][0].textChanged.connect(self._limpar_erro_validacao)
        self._campos_dobras_reais["datas"][0].dateChanged.connect(self._limpar_erro_validacao)

        self._recalcular_composicao()

        # QScrollArea (mesmo motivo da Etapa 6): numa janela pequena, as duas
        # tabelas empilhadas podem exceder a altura disponível -- rolar o
        # excesso evita que a coluna fique espremida ou corte conteúdo.
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

        # A imagem preenche a altura toda do cartão (QSizePolicy.Expanding);
        # como o pixmap é sempre reescalado centralizado dentro desse
        # espaço, ela fica alinhada ao centro vertical da coluna da tabela.
        self._imagem_musculo_gordura = _ImagemProporcional(_CAMINHO_IMAGEM_MUSCULO_GORDURA)
        layout_cartao.addWidget(self._imagem_musculo_gordura, stretch=2)

        layout_raiz.addWidget(cartao, stretch=1)

    def ao_entrar(self, dados_coletados: dict) -> None:
        """Chamado pelo wizard toda vez que essa etapa é exibida -- lê sexo
        e idade já cadastrados na Etapa 1 (entram no protocolo JP7, ver
        `_calcular_composicao_jp7`) e recalcula com os valores atuais.
        """
        self._sexo = dados_coletados.get("sexo")
        self._idade = dados_coletados.get("idade")
        self._recalcular_composicao()

    # -- Reavaliações dinâmicas: coluna nova sincronizada -----------------

    def _conectar_coluna_calculo(self, widgets_dobras, widgets_peso) -> None:
        """Liga os sinais de UMA coluna (dobras+data/peso) ao recálculo
        automático da composição corporal -- usada tanto pela coluna
        inicial (`__init__`) quanto por cada coluna nova
        (`_adicionar_nova_avaliacao`), sempre a mesma lógica. Cada
        argumento é uma lista `[(chave, widget), ...]` da MESMA coluna
        (mesmo formato devolvido por `_adicionar_coluna_tabela`).

        Dentro de `widgets_dobras`, a data usa `dateChanged` (é um
        QDateEdit); as 7 dobras usam `textChanged` como o peso.
        """
        for chave, widget in widgets_dobras:
            if chave == "datas":
                widget.dateChanged.connect(self._recalcular_composicao)
            else:
                widget.textChanged.connect(self._recalcular_composicao)
        for _chave, widget in widgets_peso:
            widget.textChanged.connect(self._recalcular_composicao)

    def _sincronizar_scroll_horizontal(self, origem: QTableWidget, valor: int) -> None:
        """Mantém as 4 tabelas rolando juntas -- ver comentário em
        `__init__` (`_tabelas_reavaliacao`). `blockSignals` evita o
        cascateamento A->B->A que geraria um loop infinito.
        """
        for tabela in self._tabelas_reavaliacao:
            if tabela is origem:
                continue
            barra = tabela.horizontalScrollBar()
            if barra.value() != valor:
                barra.blockSignals(True)
                barra.setValue(valor)
                barra.blockSignals(False)

    def _adicionar_nova_avaliacao(self) -> None:
        """Botão "+": cria uma coluna nova, sincronizada, nas 3 seções da
        Etapa 7 de uma vez só -- nunca uma coluna "solta" só numa seção, e
        a Composição corporal SEMPRE recebe a coluna nova automaticamente,
        sem ação extra do personal. Os dados das colunas já existentes não
        são tocados.
        """
        novos_dobras = _adicionar_coluna_tabela(
            self._tabela_dobras_reais, self._campos_dobras_reais, _LINHAS_DOBRAS_COM_DATA
        )
        novos_peso = _adicionar_coluna_tabela(self._tabela_peso, self._campos_peso, _LINHAS_PESO)
        # Composição corporal é só resultado (QLabel, sem sinal próprio) --
        # ainda assim precisa da coluna nova AQUI, no mesmo clique, pra
        # `_recalcular_composicao` abaixo ter onde escrever o resultado
        # dessa avaliação.
        _adicionar_coluna_tabela(
            self._tabela_composicao, self._campos_composicao, _LINHAS_COMPOSICAO_CORPORAL
        )
        self._conectar_coluna_calculo(novos_dobras, novos_peso)

        self._num_colunas += 1
        self._recalcular_composicao()

        # Rola até a coluna recém-criada (nas 3 tabelas, via
        # `_sincronizar_scroll_horizontal`) -- sem isto, com muitas colunas
        # já existentes, a nova nasceria fora da área visível.
        barra = self._tabela_dobras_reais.horizontalScrollBar()
        barra.setValue(barra.maximum())

    # -- Composição corporal: cálculo automático -------------------------
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
            # A data não é digitada de novo aqui -- só espelha a da tabela
            # de Dobras Cutâneas daquela mesma coluna (ver comentário em
            # `_LINHAS_COMPOSICAO_CORPORAL`), sempre no formato dd/MM/aaaa.
            data = _valor_data(campos_datas[coluna])
            labels_data[coluna].setText(data if data else "—")

            peso = _texto_para_numero(campos_peso[coluna].text())
            dobras = {
                chave: _texto_para_numero(self._campos_dobras_reais[chave][coluna].text())
                for chave in _CHAVES_DOBRAS_7
            }

            # Nunca "0 kg"/"0%"/"0,00%" inventado, nunca cálculo parcial --
            # junta TODOS os motivos de não dar pra calcular ainda (dado
            # ausente) antes de decidir, igual às demais etapas do wizard.
            faltando = []
            if not self._sexo:
                faltando.append("o sexo (Etapa 1)")
            elif self._sexo not in _CONSTANTES_JP7:
                # Sexo preenchido, mas com um valor fora de Masculino/Feminino
                # (só possível em cadastro antigo -- a Etapa 1 atual só
                # oferece essas duas opções, ver SEXO_OPCOES). O protocolo
                # JP7 só tem coeficientes para Masculino/Feminino.
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

            # `faltando` vazio garante sexo/idade/peso/as 7 dobras presentes
            # -- `_calcular_composicao_jp7` não pode retornar None aqui.
            resultado = _calcular_composicao_jp7(self._sexo, self._idade, peso, dobras)

            labels_magra[coluna].setText(f"{_formatar_numero(resultado['massa_magra'], 2)} kg")
            labels_gorda[coluna].setText(f"{_formatar_numero(resultado['massa_gorda'], 2)} kg")
            # A tela sempre mostra o percentual PROTEGIDO (nunca negativo --
            # especificação, seções 5 e 8): é o mesmo valor usado em massa
            # gorda/magra acima. O bruto calculado não é apagado (ver
            # `_calcular_composicao_jp7`) -- quando os dois divergem (caso
            # negativo protegido para 0), fica disponível na dica do campo.
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

    # -- Validação ao avançar ---------------------------------------------

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
        """Exige data e peso da primeira avaliação (coluna 0) -- sem eles
        não há um registro de composição corporal utilizável. As demais
        medidas (dobras cutâneas) e as colunas de avaliações futuras
        continuam opcionais (mesmo espírito "sem preenchimento
        obrigatório" da Etapa 6): o personal pode completá-las ao longo do
        acompanhamento, em visitas seguintes -- só não recebem um
        resultado de composição corporal calculado enquanto isso.
        """
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
        # Resultados agora são colunas calculadas ("resultado"), não mais
        # digitadas -- recalcula pelo mesmo método usado ao vivo em
        # `_recalcular_composicao` (mesma fonte de verdade:
        # `_calcular_composicao_jp7`), em vez de ler o texto já formatado
        # ("22,80%"/"—") do QLabel. Só reporta um resultado quando
        # sexo/idade/peso/as 7 dobras estão presentes (mesmo critério "tudo
        # ou nada" usado ao vivo na tela) -- nunca um valor parcial salvo.
        massa_magra = []
        massa_gorda = []
        percentual_gordura = []
        percentual_gordura_bruto = []
        densidade_corporal = []
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
            else:
                massa_magra.append(round(resultado["massa_magra"], 2))
                massa_gorda.append(round(resultado["massa_gorda"], 2))
                # Percentual PROTEGIDO (nunca negativo -- especificação,
                # seções 5 e 8): é o que efetivamente gerou massa gorda/magra
                # acima. O bruto calculado pela fórmula (pode ser negativo
                # num caso-limite) não é apagado -- vai à parte em
                # "percentual_gordura_bruto", igual às duas linhas de
                # "% Gordura Corporal" da planilha.
                percentual_gordura.append(round(resultado["percentual_protegido"], 2))
                percentual_gordura_bruto.append(round(resultado["percentual"], 2))
                densidade_corporal.append(round(resultado["densidade"], 4))

        composicao_corporal = {
            # Mesma data da tabela de Dobras Cutâneas (ver comentário em
            # `_LINHAS_COMPOSICAO_CORPORAL`) -- não é lida de novo daqui, é
            # o mesmo dado, só espelhado. Estrutura (chaves e ordem) igual à
            # seção "Composição Corporal" da planilha de referência -- sem
            # "peso_corporal"/"soma_dobras": a planilha não tem essas linhas
            # aqui (peso já tem sua própria linha/chave, ver "peso" no
            # dict retornado abaixo; soma é só conta interna da densidade).
            "datas": dobras_cutaneas["datas"],
            "massa_magra": massa_magra,
            "massa_gorda": massa_gorda,
            "percentual_gordura": percentual_gordura,
            "percentual_gordura_bruto": percentual_gordura_bruto,
            "densidade_corporal": densidade_corporal,
        }

        return {
            "dobras_cutaneas": dobras_cutaneas,
            "peso": peso,
            "composicao_corporal": composicao_corporal,
        }

    def limpar(self) -> None:
        # Volta ao estado inicial de 1 coluna -- sem isto, um novo cadastro
        # herdaria as colunas extras que o personal tivesse criado no
        # cadastro anterior.
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

        for matriz in (
            self._campos_dobras_reais,
            self._campos_peso,
            self._campos_composicao,
        ):
            for widgets in matriz.values():
                for widget in widgets:
                    _limpar_widget(widget)
        self._limpar_erro_validacao()


# -- Etapa 8: Registro de imagens -----------------------------------------

# (chave salva/lida em `_dados_coletados` e na coluna do banco, título
# exibido no card) -- ordem de exibição na grade 2x2, igual ao modelo da
# especificação (frente/costas na primeira linha, lados na segunda).
_SLOTS_FOTOS = [
    ("foto_frente", "Imagem de frente"),
    ("foto_costas", "Imagem de costa"),
    ("foto_lado_direito", "Imagem do lado direito"),
    ("foto_lado_esquerdo", "Imagem do lado esquerdo"),
]

_FILTRO_ARQUIVOS_IMAGEM = "Imagens (*.png *.jpg *.jpeg *.webp)"


class _AreaFotoClicavel(QLabel):
    """Área de foto de um card da Etapa 8: mostra "+" centralizado enquanto
    vazia, ou a foto já escolhida (redimensionada mantendo a proporção
    original, sem deformar -- mesma técnica de `_ImagemProporcional`, via
    QPixmap.scaled a cada resize). Clicar emite `clicada` tanto vazia quanto
    já preenchida -- é o que permite substituir uma foto sem criar um
    segundo card (especificação, seção 7).
    """

    clicada = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._caminho: Optional[str] = None
        self._pixmap_original: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        # Mínimo baixo de propósito: quem manda no tamanho é o card pai
        # (`_CardFotoAluno`/`_GradeFotos`, formato retangular vertical) --
        # um mínimo maior aqui competiria com aquele tamanho fixo na janela
        # pequena e voltaria a achatar o card para um formato mais quadrado.
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
            # Arquivo inválido/corrompido -- mantém a foto anterior (se
            # havia) em vez de trocar por um card vazio sem avisar.
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
            # clear() antes de setText(): setPixmap(QPixmap() nulo) reseta o
            # texto internamente no QLabel -- setar nessa ordem faria o "+"
            # sumir de novo assim que este método é chamado de novo (ex.: no
            # primeiro resizeEvent dispersado pelo próprio layout).
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
    """Um dos quatro cards da Etapa 8 -- título + `_AreaFotoClicavel`.

    Mesmo padrão visual dos demais cartões internos do cadastro (fundo
    claro, borda suave, cantos arredondados -- ver `_BotaoObjetivo`), só
    que sem estado de seleção: aqui o card só existe vazio ou com uma foto.
    """

    solicitar_imagem = Signal()

    def __init__(self, titulo: str, parent=None):
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
        # Margens/espaçamento internos enxutos -- é o que sobra de área pra
        # foto de fato (especificação: "a área interna destinada à imagem
        # também deve ficar maior"), sem cortar o respiro do título.
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

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


# Retângulo VERTICAL (mais alto que largo, como uma foto de corpo inteiro)
# -- largura:altura ≈ 4:5 (um pouco mais "cheio" que o 3:4 original: mesma
# altura disponível rende um card perceptivelmente maior sem parecer
# quadrado). A LARGURA é sempre DERIVADA da altura por essa razão -- nunca
# um piso independente: um piso de largura à parte (desalinhado da razão)
# é exatamente o que faria o card ficar quadrado numa janela pequena, onde
# a altura disponível encolhe mas a largura mínima não acompanharia.
_RAZAO_LARGURA_ALTURA_CARD_FOTO = 4 / 5
# Piso puro de segurança (card ínfimo/zero em vez de encolher janela
# afora) -- bem abaixo do menor valor real já visto na janela mínima do
# app (960x600, ver `ui_main.py`), então não força os cards a
# transbordarem do painel numa janela pequena; ele só entraria em ação se
# o mínimo da janela fosse reduzido bem mais no futuro.
_ALTURA_MINIMA_CARD_FOTO = 100
_ALTURA_MAXIMA_CARD_FOTO = 420  # teto de bom senso p/ monitores bem altos
_ESPACAMENTO_GRADE_FOTOS = 18
_MARGEM_PAINEL_FOTOS = 20


class _PainelFotosAluno(QFrame):
    """Painel branco com a grade 2x2 dos 4 cards de foto.

    Ao contrário do cartão padrão do cadastro (`_criar_cartao()`, sempre
    esticado à largura inteira da etapa pelo QVBoxLayout que o contém),
    este painel ACOMPANHA o tamanho real do conteúdo: sua LARGURA é sempre
    recalculada a partir da própria ALTURA (livre para crescer/encolher com
    a janela, via stretch no layout da etapa -- ver `ImagensAlunoStep`) já
    somando as margens internas, então não sobra faixa de branco vazio nas
    laterais como no cartão padrão (especificação: "o container deve
    acompanhar melhor o tamanho real dos quatro cards"). Por isso precisa
    ser adicionado ao layout da etapa com alinhamento horizontal central
    (`Qt.AlignHCenter`) -- sem stretch nem alinhamento vertical, então a
    altura continua livre (fill), só a largura passa a ser a nossa.

    A altura de cada card é sempre metade da altura disponível (dividida
    pelas 2 linhas da grade) -- ela já usa o espaço vertical inteiro, sem
    sobra --, e a LARGURA é sempre DERIVADA dela pela razão acima, nunca o
    contrário (especificação: "não aumentar automaticamente a largura").
    """

    def __init__(self, cards, parent=None):
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
        self._cards = list(cards)

        self._grade = QGridLayout(self)
        self._grade.setContentsMargins(
            _MARGEM_PAINEL_FOTOS, _MARGEM_PAINEL_FOTOS,
            _MARGEM_PAINEL_FOTOS, _MARGEM_PAINEL_FOTOS,
        )
        self._grade.setHorizontalSpacing(_ESPACAMENTO_GRADE_FOTOS)
        self._grade.setVerticalSpacing(_ESPACAMENTO_GRADE_FOTOS)
        for indice, card in enumerate(self._cards):
            self._grade.addWidget(card, indice // 2, indice % 2)

        self._recalcular()

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self._recalcular()

    def _recalcular(self) -> None:
        espaco_v = self._grade.verticalSpacing()
        altura_disponivel = self.height() - 2 * _MARGEM_PAINEL_FOTOS - espaco_v
        altura_celula = altura_disponivel / 2
        if altura_celula <= 0:
            return  # ainda sem geometria real (antes do primeiro layout)

        altura = max(altura_celula, _ALTURA_MINIMA_CARD_FOTO)
        altura = min(altura, _ALTURA_MAXIMA_CARD_FOTO)
        largura = altura * _RAZAO_LARGURA_ALTURA_CARD_FOTO

        tamanho = QSize(int(largura), int(altura))
        for card in self._cards:
            card.setFixedSize(tamanho)

        # Fecha a própria largura exatamente ao redor dos 2 cards + espaço
        # entre eles + margens -- nunca mais larga que isso (é o que tira o
        # vazio nas laterais do painel).
        espaco_h = self._grade.horizontalSpacing()
        largura_painel = int(largura) * 2 + espaco_h + 2 * _MARGEM_PAINEL_FOTOS
        self.setFixedWidth(largura_painel)


class ImagensAlunoStep(QWidget):
    """Etapa 8 (última) do cadastro: as quatro fotos do aluno.

    Sem validação obrigatória -- diferente das etapas anteriores, nenhuma
    foto é exigida para concluir o cadastro (especificação, seção 12: só
    os quatro espaços + seleção + exibição + salvamento, nada além disso).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(18)

        # Cabeçalho — mesmo banner azul das demais etapas de Anamnese, só
        # muda o subtítulo.
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

        subtitulo_cabecalho = QLabel("Etapa 8: Registro de imagens")
        subtitulo_cabecalho.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: white; font-size: {Fontes.TAMANHO_TEXTO}px; font-weight: 500;"
        )
        layout_cabecalho.addWidget(subtitulo_cabecalho)

        layout_raiz.addWidget(cabecalho)

        # Painel com a grade 2x2 dos quatro espaços de foto ------------------
        self._cards: Dict[str, _CardFotoAluno] = {}
        for chave, titulo in _SLOTS_FOTOS:
            card = _CardFotoAluno(titulo)
            card.solicitar_imagem.connect(
                lambda chave=chave: self._selecionar_imagem(chave)
            )
            self._cards[chave] = card

        # stretch (não addStretch) + Qt.AlignHCenter: a altura continua
        # livre para preencher o espaço vertical sobrando (dando ao painel
        # a altura de que ele precisa pra calcular o tamanho dos cards),
        # mas a LARGURA passa a ser a do próprio painel (auto-ajustada em
        # `_PainelFotosAluno._recalcular`), centralizada em vez de esticada
        # -- é isso que tira o vazio nas laterais do container.
        # Sem espaçador extra depois do painel: o próprio wizard já reserva
        # uma margem confortável entre o fim da etapa atual e os botões de
        # navegação (`CadastroAlunoWizard`, addStretch antes da barra de
        # botões) -- repetir esse respiro aqui só encolheria os cards à toa.
        painel = _PainelFotosAluno(self._cards.values())
        layout_raiz.addWidget(painel, 1, Qt.AlignHCenter)

    def _selecionar_imagem(self, chave: str) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar imagem", "", _FILTRO_ARQUIVOS_IMAGEM
        )
        if caminho:
            self._cards[chave].definir_imagem(caminho)

    def obter_dados_validados(self):
        """Sem campos obrigatórios nesta etapa -- sempre retorna um dict
        (nunca None), com a foto de cada posição ou None para a que ainda
        não foi escolhida."""
        return {chave: self._cards[chave].caminho_imagem for chave, _ in _SLOTS_FOTOS}

    def limpar(self) -> None:
        for card in self._cards.values():
            card.definir_imagem(None)


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
            ComposicaoCorporalStep(),
            ImagensAlunoStep(),
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
        # A Etapa 8 (Registro de imagens) é a última de fato -- avançar por
        # ela salva o cadastro (ver `_proximo_clicado`), então só ela troca
        # o rótulo do botão para "Salvar"; todas as anteriores continuam
        # "Próximo >".
        ultima_etapa = self._etapa_atual == len(self._etapas) - 1
        self._botao_proximo.setText("Salvar" if ultima_etapa else "Próximo >")

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
        # Filtra para os parâmetros que `criar_aluno` de fato aceita: etapas
        # mais novas (ex.: Composição Corporal) podem coletar dados que
        # ainda não têm coluna própria no cadastro do aluno -- eles
        # continuam disponíveis em `self._dados_coletados` durante a sessão
        # do wizard (nada se perde ao navegar entre etapas), só não são
        # enviados a um parâmetro que `criar_aluno` não reconhece.
        parametros_aceitos = set(inspect.signature(self._aluno_service.criar_aluno).parameters)
        dados_para_salvar = {
            chave: valor
            for chave, valor in self._dados_coletados.items()
            if chave in parametros_aceitos
        }
        try:
            self._aluno_service.criar_aluno(**dados_para_salvar)
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
