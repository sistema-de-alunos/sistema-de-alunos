from core.qt_core import *
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QVBoxLayout
)
from PySide6.QtGui import QFont


class UI_MainWindow(object):
    def setup_ui(self, parent):
        if not parent.objectName():
            parent.setObjectName("MainWindow")

        parent.resize(1280, 720)
        parent.setMinimumSize(960, 540)

        # Widget central
        self.central_frame = QFrame()
        self.central_frame.setStyleSheet("""
            QFrame{
                background-color: #F5F7FA;
            }
        """)

        parent.setCentralWidget(self.central_frame)


        # Layout principal
        self.layout = QVBoxLayout(self.central_frame)
        self.layout.setContentsMargins(40, 30, 40, 30)
        self.layout.setSpacing(20)

        # Título
        self.lblTitulo = QLabel("Painel de Alunos")

        fonte = QFont()
        fonte.setPointSize(20)
        fonte.setBold(True)

        self.lblTitulo.setFont(fonte)
        self.lblTitulo.setStyleSheet("""
            QLabel{
                color:#183C90;
            }
        """)

        self.layout.addWidget(self.lblTitulo)

        # Barra de pesquisa
        self.txtPesquisa = QLineEdit()
        self.txtPesquisa.setPlaceholderText("Buscar aluno...")

        self.txtPesquisa.setFixedHeight(40)
        self.txtPesquisa.setFixedSize(450, 40)
        self.txtPesquisa.setStyleSheet("""
            QLineEdit{
                background:white;
                border:1px solid #D9D9D9;
                border-radius:10px;
                padding-left:12px;
                font-size:14px;
            }
        """)

        self.layout.addWidget(self.txtPesquisa)


        # Botão Novo Aluno
        self.btnNovoAluno = QPushButton("Novo Aluno")

        self.btnNovoAluno.setFixedHeight(60)

        self.btnNovoAluno.setStyleSheet("""
            QPushButton{
                background:#4C56D6;
                color:white;
                border:none;
                border-radius:12px;
                font-size:16px;
                font-weight:bold;
            }

            QPushButton:hover{
                background:#3B46B1;
            }
        """)

        self.layout.addWidget(self.btnNovoAluno)

        # Espaço para a lista futuramente
        self.layout.addStretch()