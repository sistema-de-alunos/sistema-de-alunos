from core.qt_core import QStackedWidget
from gui.dialogs.cadastro_alunos import CadastroAlunoWizard
from gui.pages.home import PainelAlunosPage
from models.alunos_service import AlunoService


class UI_MainWindow:
    def setup_ui(self, parent):
        parent.setWindowTitle("Sistema de Alunos")
        parent.resize(1280, 720)
        parent.setMinimumSize(960, 600)

        self.aluno_service = AlunoService()

        self.stack = QStackedWidget()
        parent.setCentralWidget(self.stack)

        self.pagina_home = PainelAlunosPage(self.aluno_service)
        self.pagina_cadastro = CadastroAlunoWizard(self.aluno_service)

        self.stack.addWidget(self.pagina_home)
        self.stack.addWidget(self.pagina_cadastro)

        self.pagina_home.novo_aluno_solicitado.connect(self._abrir_cadastro)
        self.pagina_home.aluno_selecionado.connect(self._abrir_edicao_aluno)
        self.pagina_cadastro.voltar_para_home.connect(self._voltar_para_home)
        self.pagina_cadastro.cadastro_concluido.connect(self._aluno_salvo)

        self.stack.setCurrentWidget(self.pagina_home)

    def _abrir_cadastro(self) -> None:
        self.pagina_cadastro.resetar()
        self.stack.setCurrentWidget(self.pagina_cadastro)

    def _abrir_edicao_aluno(self, aluno_id: int) -> None:
        if self.pagina_cadastro.abrir_para_edicao(aluno_id):
            self.stack.setCurrentWidget(self.pagina_cadastro)
        else:
            self.pagina_home.recarregar()

    def _voltar_para_home(self) -> None:
        self.stack.setCurrentWidget(self.pagina_home)

    def _aluno_salvo(self) -> None:
        self.pagina_home.recarregar()
        self.stack.setCurrentWidget(self.pagina_home)
        self.pagina_home.mostrar_sucesso("Aluno salvo com sucesso!")
