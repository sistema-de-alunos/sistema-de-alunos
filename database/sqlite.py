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
    """Cria as tabelas de avaliações (Etapas 6 e 7), uma linha por avaliação.

    Um aluno pode ter várias avaliações -- por isso cada uma vive em sua
    própria linha, referenciando o aluno por `aluno_id` (nunca um novo
    conjunto de colunas soltas na tabela `alunos`, que só guarda o cadastro
    básico, sem duplicação). `ON DELETE CASCADE` (com `PRAGMA foreign_keys =
    ON`, já ligado em `obter_conexao`) garante que excluir um aluno também
    remove suas avaliações -- sem isso ficariam linhas órfãs apontando para
    um `aluno_id` que não existe mais.
    """
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

    # Etapa 8: uma linha por sessão de fotos (data + as 4 posições).
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
    """Antes das sessões, as 4 fotos ficavam em colunas de `alunos`: elas
    viram a Sessão 1 (sem data) de quem ainda não tem sessão nenhuma -- só
    uma vez, já que o app não grava mais nessas colunas."""
    conexao.execute(
        """
        INSERT INTO sessoes_fotos (aluno_id, foto_frente, foto_costas, foto_lado_direito, foto_lado_esquerdo)
        SELECT id, foto_frente, foto_costas, foto_lado_direito, foto_lado_esquerdo FROM alunos
        WHERE COALESCE(foto_frente, foto_costas, foto_lado_direito, foto_lado_esquerdo) IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM sessoes_fotos WHERE sessoes_fotos.aluno_id = alunos.id)
        """
    )


def _garantir_colunas_anamnese(conexao: sqlite3.Connection) -> None:
    """Adiciona as colunas das etapas de Anamnese a bancos criados antes delas existirem.

    `CREATE TABLE IF NOT EXISTS` não altera uma tabela já existente, então um
    banco salvo por uma versão anterior do app fica sem essas colunas — daí a
    checagem via PRAGMA e o ALTER TABLE incremental abaixo.
    """
    colunas_existentes = {
        linha["name"] for linha in conexao.execute("PRAGMA table_info(alunos)")
    }

    # A altura da Etapa 1 passou de centímetros ("altura_cm") para o formato
    # metros.centímetros ("altura_m", ex.: 1.75) -- bancos criados no
    # intervalo curto entre as duas versões têm a coluna antiga. Renomeia em
    # vez de duplicar, convertendo os valores já salvos (cm -> m) em vez de
    # perdê-los.
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
        # Hábitos de vida (última tela da anamnese): "Sim"/"Não".
        "medicamento_controlado",
        "fazendo_dieta",
        "consumo_alcool",
        "fuma",
        # Etapa 8 (Registro de imagens) -- caminho do arquivo escolhido em
        # cada uma das 4 posições, não dado de anamnese, mas some junto às
        # demais colunas de texto opcionais pelo mesmo mecanismo incremental.
        "foto_frente",
        "foto_costas",
        "foto_lado_direito",
        "foto_lado_esquerdo",
        # Foto de perfil do card da lista (lápis ao lado da lixeira).
        "foto_perfil",
        "foto_perfil_ajuste",
    )
    # Medidas da Etapa 6 (avaliação física) e a altura da Etapa 1 são
    # numéricas -- REAL, não TEXT, para não perder o tipo ao ler de volta um
    # banco criado antes delas.
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
