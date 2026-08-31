"""Camada de conexão com o banco de dados local (SQLite).

Nenhuma informação trafega pela internet: o arquivo do banco fica salvo no
computador do usuário, dentro da pasta de dados do aplicativo, e continua
disponível entre uma abertura e outra do sistema.
"""

import os
import sqlite3
from pathlib import Path

NOME_PASTA_APP = "SistemaDeAlunos"
NOME_ARQUIVO_BANCO = "alunos.db"


def _pasta_dados_local() -> Path:
    """Retorna (e garante que exista) a pasta local onde o banco é salvo."""
    base = os.environ.get("APPDATA") or str(Path.home())
    pasta = Path(base) / NOME_PASTA_APP
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


CAMINHO_BANCO = _pasta_dados_local() / NOME_ARQUIVO_BANCO


def obter_conexao() -> sqlite3.Connection:
    """Abre uma conexão nova com o banco local.

    Cada chamada abre e fecha sua própria conexão para manter o uso simples
    e evitar problemas de concorrência entre a UI e as consultas.
    """
    conexao = sqlite3.connect(str(CAMINHO_BANCO))
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar_banco() -> None:
    """Cria as tabelas necessárias caso ainda não existam."""
    conexao = obter_conexao()
    try:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS alunos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_completo TEXT NOT NULL,
                idade INTEGER NOT NULL,
                sexo TEXT NOT NULL,
                treinou_antes TEXT,
                tempo_treinamento TEXT,
                tempo_sem_atividade TEXT,
                objetivo_principal TEXT,
                objetivo_outro TEXT,
                frequencia_semanal TEXT,
                tempo_treino_dia TEXT,
                doenca_tem TEXT,
                doenca_qual TEXT,
                limitacao_tem TEXT,
                limitacao_qual TEXT,
                dor_tem TEXT,
                dor_qual TEXT,
                cirurgia_tem TEXT,
                cirurgia_qual TEXT,
                criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        _garantir_colunas_anamnese(conexao)
        conexao.commit()
    finally:
        conexao.close()


def _garantir_colunas_anamnese(conexao: sqlite3.Connection) -> None:
    """Adiciona as colunas das etapas de Anamnese a bancos criados antes delas existirem.

    `CREATE TABLE IF NOT EXISTS` não altera uma tabela já existente, então um
    banco salvo por uma versão anterior do app fica sem essas colunas — daí a
    checagem via PRAGMA e o ALTER TABLE incremental abaixo.
    """
    colunas_existentes = {
        linha["name"] for linha in conexao.execute("PRAGMA table_info(alunos)")
    }
    colunas_novas = (
        "treinou_antes",
        "tempo_treinamento",
        "tempo_sem_atividade",
        "objetivo_principal",
        "objetivo_outro",
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
    )
    for coluna in colunas_novas:
        if coluna not in colunas_existentes:
            conexao.execute(f"ALTER TABLE alunos ADD COLUMN {coluna} TEXT")
