from core.qt_core import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    Qt,
    QScrollArea,
    QTimer,
    QVBoxLayout,
    QWidget,
    Signal,
)
from core.theme import Cores, Fontes
from gui.dialogs.foto_perfil import FotoPerfilDialog
from gui.widgets.aluno_card import AlunoCard
from gui.widgets.barra_pesquisa import BarraPesquisa
from gui.widgets.botao_principal import BotaoPrimario


class PainelAlunosPage(QWidget):
    novo_aluno_solicitado = Signal()
    aluno_selecionado = Signal(int)

    def __init__(self, aluno_service, parent=None):
        super().__init__(parent)
        self._aluno_service = aluno_service
        self._termo_busca = ""

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_PAGINA};")

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(40, 30, 40, 30)
        layout_raiz.setSpacing(18)

        titulo = QLabel("Painel de Alunos")
        titulo.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: {Fontes.TAMANHO_TITULO}px; font-weight: 700;"
        )
        layout_raiz.addWidget(titulo)

        self._barra_pesquisa = BarraPesquisa()
        self._barra_pesquisa.setFixedWidth(520)
        self._barra_pesquisa.pesquisa_alterada.connect(self._on_pesquisa_alterada)
        layout_raiz.addWidget(self._barra_pesquisa)

        layout_novo_aluno = QHBoxLayout()
        self._botao_novo_aluno = BotaoPrimario("+ Novo Aluno")
        self._botao_novo_aluno.setFixedWidth(320)
        self._botao_novo_aluno.setMinimumHeight(52)
        self._botao_novo_aluno.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {Cores.AZUL_PRIMARIO};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 0 34px;
                font-size: 15px;
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
        self._botao_novo_aluno.clicked.connect(self.novo_aluno_solicitado.emit)
        layout_novo_aluno.addWidget(self._botao_novo_aluno)
        layout_novo_aluno.addStretch()
        layout_raiz.addLayout(layout_novo_aluno)

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

        self._label_sucesso = QLabel("")
        self._label_sucesso.setWordWrap(True)
        self._label_sucesso.setStyleSheet(
            f"""
            background-color: {Cores.SUCESSO_FUNDO};
            color: {Cores.SUCESSO};
            border-radius: 8px;
            padding: 10px 14px;
            font-size: {Fontes.TAMANHO_LABEL}px;
            """
        )
        self._label_sucesso.hide()
        layout_raiz.addWidget(self._label_sucesso)

        self._area_conteudo = QVBoxLayout()
        self._area_conteudo.setSpacing(12)
        layout_raiz.addLayout(self._area_conteudo, stretch=1)

        self.recarregar()


    def _on_pesquisa_alterada(self, texto: str) -> None:
        self._termo_busca = texto
        self.recarregar()

    def recarregar(self) -> None:
        self._limpar_area_conteudo()

        label_carregando = QLabel("Carregando alunos...")
        label_carregando.setStyleSheet(f"color: {Cores.TEXTO_SECUNDARIO}; font-size: 13px;")
        self._area_conteudo.addWidget(label_carregando)

        QTimer.singleShot(0, self._carregar_alunos)

    def _carregar_alunos(self) -> None:
        try:
            tem_algum_aluno = self._aluno_service.existe_algum_aluno()
            alunos = self._aluno_service.listar_alunos(self._termo_busca)
        except Exception:
            self._mostrar_erro(
                "Não foi possível carregar os alunos cadastrados. Tente novamente."
            )
            return

        self._limpar_area_conteudo()

        self._barra_pesquisa.setVisible(tem_algum_aluno)
        self._botao_novo_aluno.setVisible(tem_algum_aluno)

        if not tem_algum_aluno:
            if self._termo_busca:
                self._termo_busca = ""
                self._barra_pesquisa.blockSignals(True)
                self._barra_pesquisa.clear()
                self._barra_pesquisa.blockSignals(False)
            self._montar_estado_vazio()
        elif not alunos:
            self._montar_estado_sem_resultado()
        else:
            self._montar_lista(alunos)


    def _limpar_area_conteudo(self) -> None:
        while self._area_conteudo.count():
            item = self._area_conteudo.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _criar_moldura_lista(self) -> QFrame:
        moldura = QFrame()
        moldura.setObjectName("molduraLista")
        moldura.setStyleSheet(
            f"""
            QFrame#molduraLista {{
                background-color: {Cores.FUNDO_LISTA};
                border: 1px solid {Cores.BORDA_LISTA};
                border-radius: 16px;
            }}
            """
        )
        return moldura

    def _montar_estado_vazio(self) -> None:
        moldura = self._criar_moldura_lista()
        layout = QVBoxLayout(moldura)
        layout.setContentsMargins(40, 50, 40, 50)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        titulo = QLabel("Nenhum aluno cadastrado")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_PRIMARIO}; font-size: 19px; font-weight: 700;"
        )
        layout.addWidget(titulo)

        subtitulo = QLabel("Cadastre seu primeiro aluno para começar.")
        subtitulo.setAlignment(Qt.AlignCenter)
        subtitulo.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_SECUNDARIO}; font-size: 14px;"
        )
        layout.addWidget(subtitulo)

        layout.addSpacing(16)

        botao = BotaoPrimario("+ Novo Aluno")
        botao.setFixedWidth(200)
        botao.clicked.connect(self.novo_aluno_solicitado.emit)
        layout.addWidget(botao, alignment=Qt.AlignCenter)

        self._area_conteudo.addWidget(moldura)

    def _montar_estado_sem_resultado(self) -> None:
        moldura = self._criar_moldura_lista()
        layout = QVBoxLayout(moldura)
        layout.setContentsMargins(40, 50, 40, 50)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("Nenhum aluno encontrado para essa busca.")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"background: transparent; border: none; "
            f"color: {Cores.TEXTO_SECUNDARIO}; font-size: 14px;"
        )
        layout.addWidget(label)

        self._area_conteudo.addWidget(moldura)

    def _montar_lista(self, alunos) -> None:
        moldura = self._criar_moldura_lista()
        layout_moldura = QVBoxLayout(moldura)
        layout_moldura.setContentsMargins(16, 16, 16, 16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"""
            QScrollArea {{ background: transparent; border: none; }}
            """
        )

        conteudo = QWidget()
        conteudo.setStyleSheet("background: transparent; border: none;")
        layout_lista = QVBoxLayout(conteudo)
        layout_lista.setContentsMargins(0, 0, 4, 0)
        layout_lista.setSpacing(10)

        for aluno in alunos:
            card = AlunoCard(
                aluno.id, aluno.nome_completo, aluno.foto_perfil, aluno.foto_perfil_ajuste
            )
            card.clicado.connect(self.aluno_selecionado.emit)
            card.excluir_solicitado.connect(self._confirmar_exclusao)
            card.editar_foto_solicitado.connect(self._editar_foto_perfil)
            layout_lista.addWidget(card)

        layout_lista.addStretch()
        scroll.setWidget(conteudo)

        layout_moldura.addWidget(scroll)
        self._area_conteudo.addWidget(moldura)


    def _confirmar_exclusao(self, aluno_id: int) -> None:
        caixa = QMessageBox(self)
        caixa.setWindowTitle("Excluir aluno")
        caixa.setIcon(QMessageBox.Warning)
        caixa.setText("Excluir aluno?")
        caixa.setInformativeText(
            "Tem certeza de que deseja excluir este aluno? Essa ação não poderá ser desfeita."
        )
        botao_cancelar = caixa.addButton("Cancelar", QMessageBox.RejectRole)
        botao_excluir = caixa.addButton("Excluir", QMessageBox.DestructiveRole)
        caixa.setDefaultButton(botao_cancelar)
        caixa.exec()

        if caixa.clickedButton() != botao_excluir:
            return

        try:
            self._aluno_service.excluir_aluno(aluno_id)
        except Exception:
            self._mostrar_erro("Não foi possível excluir o aluno agora. Tente novamente.")
            return

        self.recarregar()
        self.mostrar_sucesso("Aluno excluído com sucesso.")


    def _editar_foto_perfil(self, aluno_id: int) -> None:
        aluno = self._aluno_service.buscar_por_id(aluno_id)
        if aluno is None:
            return
        dialogo = FotoPerfilDialog(aluno.foto_perfil, aluno.foto_perfil_ajuste, self)
        if not dialogo.exec():
            return

        try:
            self._aluno_service.atualizar_aluno(
                aluno_id, foto_perfil=dialogo.caminho, foto_perfil_ajuste=dialogo.ajuste_texto
            )
        except Exception:
            self._mostrar_erro("Não foi possível salvar a foto agora. Tente novamente.")
            return

        self.recarregar()
        self.mostrar_sucesso(
            "Foto de perfil atualizada." if dialogo.caminho else "Foto de perfil removida."
        )


    def _mostrar_erro(self, mensagem: str) -> None:
        self._label_sucesso.hide()
        self._label_erro.setText(mensagem)
        self._label_erro.show()
        self._limpar_area_conteudo()

    def mostrar_sucesso(self, mensagem: str) -> None:
        self._label_erro.hide()
        self._label_sucesso.setText(mensagem)
        self._label_sucesso.show()
        QTimer.singleShot(4000, self._label_sucesso.hide)
