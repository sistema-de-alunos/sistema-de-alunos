"""Regras de acesso aos dados dos alunos, isolando a UI do SQL bruto."""

from dataclasses import dataclass
from typing import List, Optional

from database.database import obter_conexao


@dataclass(frozen=True)
class Aluno:
    id: int
    nome_completo: str
    idade: int
    sexo: str
    criado_em: str
    treinou_antes: Optional[str] = None
    tempo_treinamento: Optional[str] = None
    tempo_sem_atividade: Optional[str] = None
    objetivo_principal: Optional[str] = None
    objetivo_outro: Optional[str] = None
    frequencia_semanal: Optional[str] = None
    tempo_treino_dia: Optional[str] = None
    doenca_tem: Optional[str] = None
    doenca_qual: Optional[str] = None
    limitacao_tem: Optional[str] = None
    limitacao_qual: Optional[str] = None
    dor_tem: Optional[str] = None
    dor_qual: Optional[str] = None
    cirurgia_tem: Optional[str] = None
    cirurgia_qual: Optional[str] = None
    medida_ombro: Optional[float] = None
    medida_torax: Optional[float] = None
    medida_cintura: Optional[float] = None
    medida_abdominal: Optional[float] = None
    medida_quadril: Optional[float] = None
    medida_braco_e: Optional[float] = None
    medida_braco_e_contraido: Optional[float] = None
    medida_braco_d: Optional[float] = None
    medida_braco_d_contraido: Optional[float] = None
    medida_antebraco_e: Optional[float] = None
    medida_antebraco_d: Optional[float] = None
    medida_coxa_d: Optional[float] = None
    medida_coxa_e: Optional[float] = None
    medida_panturrilha_e: Optional[float] = None
    medida_panturrilha_d: Optional[float] = None


class AlunoService:
    """Operações de cadastro e consulta de alunos no banco local."""

    def criar_aluno(
        self,
        nome_completo: str,
        idade: int,
        sexo: str,
        treinou_antes: Optional[str] = None,
        tempo_treinamento: Optional[str] = None,
        tempo_sem_atividade: Optional[str] = None,
        objetivo_principal: Optional[str] = None,
        objetivo_outro: Optional[str] = None,
        frequencia_semanal: Optional[str] = None,
        tempo_treino_dia: Optional[str] = None,
        doenca_tem: Optional[str] = None,
        doenca_qual: Optional[str] = None,
        limitacao_tem: Optional[str] = None,
        limitacao_qual: Optional[str] = None,
        dor_tem: Optional[str] = None,
        dor_qual: Optional[str] = None,
        cirurgia_tem: Optional[str] = None,
        cirurgia_qual: Optional[str] = None,
        medida_ombro: Optional[float] = None,
        medida_torax: Optional[float] = None,
        medida_cintura: Optional[float] = None,
        medida_abdominal: Optional[float] = None,
        medida_quadril: Optional[float] = None,
        medida_braco_e: Optional[float] = None,
        medida_braco_e_contraido: Optional[float] = None,
        medida_braco_d: Optional[float] = None,
        medida_braco_d_contraido: Optional[float] = None,
        medida_antebraco_e: Optional[float] = None,
        medida_antebraco_d: Optional[float] = None,
        medida_coxa_d: Optional[float] = None,
        medida_coxa_e: Optional[float] = None,
        medida_panturrilha_e: Optional[float] = None,
        medida_panturrilha_d: Optional[float] = None,
    ) -> Aluno:
        nome_completo = nome_completo.strip()
        conexao = obter_conexao()
        try:
            cursor = conexao.execute(
                """
                INSERT INTO alunos (
                    nome_completo, idade, sexo,
                    treinou_antes, tempo_treinamento, tempo_sem_atividade,
                    objetivo_principal, objetivo_outro,
                    frequencia_semanal, tempo_treino_dia,
                    doenca_tem, doenca_qual,
                    limitacao_tem, limitacao_qual,
                    dor_tem, dor_qual,
                    cirurgia_tem, cirurgia_qual,
                    medida_ombro, medida_torax, medida_cintura,
                    medida_abdominal, medida_quadril,
                    medida_braco_e, medida_braco_e_contraido,
                    medida_braco_d, medida_braco_d_contraido,
                    medida_antebraco_e, medida_antebraco_d,
                    medida_coxa_d, medida_coxa_e,
                    medida_panturrilha_e, medida_panturrilha_d
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    nome_completo, idade, sexo,
                    treinou_antes, tempo_treinamento, tempo_sem_atividade,
                    objetivo_principal, objetivo_outro,
                    frequencia_semanal, tempo_treino_dia,
                    doenca_tem, doenca_qual,
                    limitacao_tem, limitacao_qual,
                    dor_tem, dor_qual,
                    cirurgia_tem, cirurgia_qual,
                    medida_ombro, medida_torax, medida_cintura,
                    medida_abdominal, medida_quadril,
                    medida_braco_e, medida_braco_e_contraido,
                    medida_braco_d, medida_braco_d_contraido,
                    medida_antebraco_e, medida_antebraco_d,
                    medida_coxa_d, medida_coxa_e,
                    medida_panturrilha_e, medida_panturrilha_d,
                ),
            )
            conexao.commit()
            novo_id = cursor.lastrowid
        finally:
            conexao.close()

        aluno = self.buscar_por_id(novo_id)
        assert aluno is not None  # acabou de ser inserido
        return aluno

    def existe_algum_aluno(self) -> bool:
        """Indica se há pelo menos um aluno cadastrado, ignorando filtros de busca."""
        conexao = obter_conexao()
        try:
            linha = conexao.execute("SELECT 1 FROM alunos LIMIT 1").fetchone()
            return linha is not None
        finally:
            conexao.close()

    def excluir_aluno(self, aluno_id: int) -> None:
        conexao = obter_conexao()
        try:
            conexao.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
            conexao.commit()
        finally:
            conexao.close()

    def listar_alunos(self, termo_busca: str = "") -> List[Aluno]:
        conexao = obter_conexao()
        try:
            termo_busca = (termo_busca or "").strip()
            if termo_busca:
                linhas = conexao.execute(
                    """
                    SELECT * FROM alunos
                    WHERE nome_completo LIKE ? COLLATE NOCASE
                    ORDER BY nome_completo ASC
                    """,
                    (f"%{termo_busca}%",),
                ).fetchall()
            else:
                linhas = conexao.execute(
                    "SELECT * FROM alunos ORDER BY nome_completo ASC"
                ).fetchall()
            return [self._linha_para_aluno(linha) for linha in linhas]
        finally:
            conexao.close()

    def buscar_por_id(self, aluno_id: int) -> Optional[Aluno]:
        conexao = obter_conexao()
        try:
            linha = conexao.execute(
                "SELECT * FROM alunos WHERE id = ?", (aluno_id,)
            ).fetchone()
            return self._linha_para_aluno(linha) if linha else None
        finally:
            conexao.close()

    @staticmethod
    def _linha_para_aluno(linha) -> Aluno:
        return Aluno(
            id=linha["id"],
            nome_completo=linha["nome_completo"],
            idade=linha["idade"],
            sexo=linha["sexo"],
            criado_em=linha["criado_em"],
            treinou_antes=linha["treinou_antes"],
            tempo_treinamento=linha["tempo_treinamento"],
            tempo_sem_atividade=linha["tempo_sem_atividade"],
            objetivo_principal=linha["objetivo_principal"],
            objetivo_outro=linha["objetivo_outro"],
            frequencia_semanal=linha["frequencia_semanal"],
            tempo_treino_dia=linha["tempo_treino_dia"],
            doenca_tem=linha["doenca_tem"],
            doenca_qual=linha["doenca_qual"],
            limitacao_tem=linha["limitacao_tem"],
            limitacao_qual=linha["limitacao_qual"],
            dor_tem=linha["dor_tem"],
            dor_qual=linha["dor_qual"],
            cirurgia_tem=linha["cirurgia_tem"],
            cirurgia_qual=linha["cirurgia_qual"],
            medida_ombro=linha["medida_ombro"],
            medida_torax=linha["medida_torax"],
            medida_cintura=linha["medida_cintura"],
            medida_abdominal=linha["medida_abdominal"],
            medida_quadril=linha["medida_quadril"],
            medida_braco_e=linha["medida_braco_e"],
            medida_braco_e_contraido=linha["medida_braco_e_contraido"],
            medida_braco_d=linha["medida_braco_d"],
            medida_braco_d_contraido=linha["medida_braco_d_contraido"],
            medida_antebraco_e=linha["medida_antebraco_e"],
            medida_antebraco_d=linha["medida_antebraco_d"],
            medida_coxa_d=linha["medida_coxa_d"],
            medida_coxa_e=linha["medida_coxa_e"],
            medida_panturrilha_e=linha["medida_panturrilha_e"],
            medida_panturrilha_d=linha["medida_panturrilha_d"],
        )
