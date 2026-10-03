import os
import sqlite3
from pathlib import Path

NOME_PASTA_APP = "SistemaDeAlunos"
NOME_ARQUIVO_BANCO = "alunos.db"


def _pasta_dados_local() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    pasta = Path(base) / NOME_PASTA_APP
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


CAMINHO_BANCO = _pasta_dados_local() / NOME_ARQUIVO_BANCO


def obter_conexao() -> sqlite3.Connection:
    conexao = sqlite3.connect(str(CAMINHO_BANCO))
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def inicializar_banco() -> None:
    conexao = obter_conexao()
    try:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS alunos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_completo TEXT NOT NULL,
                idade INTEGER NOT NULL,
                sexo TEXT NOT NULL,
                altura_m REAL,
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
                medicamento_controlado TEXT,
                fazendo_dieta TEXT,
                consumo_alcool TEXT,
                fuma TEXT,
                medida_ombro REAL,
                medida_torax REAL,
                medida_cintura REAL,
                medida_abdominal REAL,
                medida_quadril REAL,
                medida_braco_e REAL,
                medida_braco_e_contraido REAL,
                medida_braco_d REAL,
                medida_braco_d_contraido REAL,
                medida_antebraco_e REAL,
                medida_antebraco_d REAL,
                medida_coxa_d REAL,
                medida_coxa_e REAL,
                medida_panturrilha_e REAL,
                medida_panturrilha_d REAL,
                foto_frente TEXT,
                foto_costas TEXT,
                foto_lado_direito TEXT,
                foto_lado_esquerdo TEXT,
                foto_perfil TEXT,
                foto_perfil_ajuste TEXT,
                criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        _garantir_colunas_anamnese(conexao)
        _criar_tabelas_avaliacoes(conexao)
        _migrar_fotos_para_sessoes(conexao)
        conexao.commit()
    finally:
        conexao.close()


def _criar_tabelas_avaliacoes(conexao: sqlite3.Connection) -> None:
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS avaliacoes_circunferencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
            data TEXT,
            ombro REAL,
            torax REAL,
            cintura REAL,
            abdominal REAL,
            quadril REAL,
            braco_e REAL,
            braco_e_contraido REAL,
            braco_d REAL,
            braco_d_contraido REAL,
            antebraco_e REAL,
            antebraco_d REAL,
            coxa_e REAL,
            coxa_d REAL,
            panturrilha_e REAL,
            panturrilha_d REAL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conexao.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_circunferencias_aluno_id
        ON avaliacoes_circunferencias(aluno_id)
        """
    )

    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS avaliacoes_composicao_corporal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
            data TEXT,
            peso REAL,
            triceps REAL,
            peito REAL,
            axilar_media REAL,
            subescapular REAL,
            dobra_abdominal REAL,
            supra_iliaca REAL,
            coxa_dobra REAL,
            soma_dobras REAL,
            densidade_corporal REAL,
            percentual_gordura REAL,
            percentual_gordura_bruto REAL,
            massa_gorda REAL,
            massa_magra REAL,
            criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conexao.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_composicao_corporal_aluno_id
        ON avaliacoes_composicao_corporal(aluno_id)
        """
    )

    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS sessoes_fotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
            data TEXT,
            foto_frente TEXT,
            foto_costas TEXT,
            foto_lado_direito TEXT,
            foto_lado_esquerdo TEXT,
            criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    conexao.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sessoes_fotos_aluno_id
        ON sessoes_fotos(aluno_id)
        """
    )


def _migrar_fotos_para_sessoes(conexao: sqlite3.Connection) -> None:
    conexao.execute(
        """
        INSERT INTO sessoes_fotos (aluno_id, foto_frente, foto_costas, foto_lado_direito, foto_lado_esquerdo)
        SELECT id, foto_frente, foto_costas, foto_lado_direito, foto_lado_esquerdo FROM alunos
        WHERE COALESCE(foto_frente, foto_costas, foto_lado_direito, foto_lado_esquerdo) IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM sessoes_fotos WHERE sessoes_fotos.aluno_id = alunos.id)
        """
    )


def _garantir_colunas_anamnese(conexao: sqlite3.Connection) -> None:
    colunas_existentes = {
        linha["name"] for linha in conexao.execute("PRAGMA table_info(alunos)")
    }

    if "altura_cm" in colunas_existentes and "altura_m" not in colunas_existentes:
        conexao.execute("ALTER TABLE alunos RENAME COLUMN altura_cm TO altura_m")
        conexao.execute("UPDATE alunos SET altura_m = altura_m / 100.0 WHERE altura_m IS NOT NULL")
        colunas_existentes.discard("altura_cm")
        colunas_existentes.add("altura_m")

    colunas_novas_texto = (
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
        "medicamento_controlado",
        "fazendo_dieta",
        "consumo_alcool",
        "fuma",
        "foto_frente",
        "foto_costas",
        "foto_lado_direito",
        "foto_lado_esquerdo",
        "foto_perfil",
        "foto_perfil_ajuste",
    )
    colunas_novas_numericas = (
        "altura_m",
        "medida_ombro",
        "medida_torax",
        "medida_cintura",
        "medida_abdominal",
        "medida_quadril",
        "medida_braco_e",
        "medida_braco_e_contraido",
        "medida_braco_d",
        "medida_braco_d_contraido",
        "medida_antebraco_e",
        "medida_antebraco_d",
        "medida_coxa_d",
        "medida_coxa_e",
        "medida_panturrilha_e",
        "medida_panturrilha_d",
    )
    for coluna in colunas_novas_texto:
        if coluna not in colunas_existentes:
            conexao.execute(f"ALTER TABLE alunos ADD COLUMN {coluna} TEXT")
    for coluna in colunas_novas_numericas:
        if coluna not in colunas_existentes:
            conexao.execute(f"ALTER TABLE alunos ADD COLUMN {coluna} REAL")
