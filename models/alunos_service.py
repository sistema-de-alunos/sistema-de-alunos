import inspect
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from database.database import obter_conexao

_COLUNAS_CIRCUNFERENCIA = (
    "data", "ombro", "torax", "cintura", "abdominal", "quadril",
    "braco_e", "braco_e_contraido", "braco_d", "braco_d_contraido",
    "antebraco_e", "antebraco_d", "coxa_e", "coxa_d",
    "panturrilha_e", "panturrilha_d",
)
_COLUNAS_SESSAO_FOTOS = (
    "data", "foto_frente", "foto_costas", "foto_lado_direito", "foto_lado_esquerdo",
)

_COLUNAS_COMPOSICAO = (
    "data", "peso", "triceps", "peito", "axilar_media", "subescapular",
    "dobra_abdominal", "supra_iliaca", "coxa_dobra", "soma_dobras",
    "densidade_corporal", "percentual_gordura", "percentual_gordura_bruto",
    "massa_gorda", "massa_magra",
)


def _chave_alfabetica(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.casefold()


@dataclass(frozen=True)
class Aluno:
    id: int
    nome_completo: str
    idade: int
    sexo: str
    criado_em: str
    altura_m: Optional[float] = None
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
    medicamento_controlado: Optional[str] = None
    fazendo_dieta: Optional[str] = None
    consumo_alcool: Optional[str] = None
    fuma: Optional[str] = None
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
    foto_frente: Optional[str] = None
    foto_costas: Optional[str] = None
    foto_lado_direito: Optional[str] = None
    foto_lado_esquerdo: Optional[str] = None
    foto_perfil: Optional[str] = None
    foto_perfil_ajuste: Optional[str] = None


class AlunoService:
    def criar_aluno(
        self,
        nome_completo: str,
        idade: int,
        sexo: str,
        altura_m: Optional[float] = None,
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
        medicamento_controlado: Optional[str] = None,
        fazendo_dieta: Optional[str] = None,
        consumo_alcool: Optional[str] = None,
        fuma: Optional[str] = None,
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
        foto_frente: Optional[str] = None,
        foto_costas: Optional[str] = None,
        foto_lado_direito: Optional[str] = None,
        foto_lado_esquerdo: Optional[str] = None,
        foto_perfil: Optional[str] = None,
        foto_perfil_ajuste: Optional[str] = None,
    ) -> Aluno:
        nome_completo = nome_completo.strip()
        conexao = obter_conexao()
        try:
            cursor = conexao.execute(
                """
                INSERT INTO alunos (
                    nome_completo, idade, sexo, altura_m,
                    treinou_antes, tempo_treinamento, tempo_sem_atividade,
                    objetivo_principal, objetivo_outro,
                    frequencia_semanal, tempo_treino_dia,
                    doenca_tem, doenca_qual,
                    limitacao_tem, limitacao_qual,
                    dor_tem, dor_qual,
                    cirurgia_tem, cirurgia_qual,
                    medicamento_controlado, fazendo_dieta, consumo_alcool, fuma,
                    medida_ombro, medida_torax, medida_cintura,
                    medida_abdominal, medida_quadril,
                    medida_braco_e, medida_braco_e_contraido,
                    medida_braco_d, medida_braco_d_contraido,
                    medida_antebraco_e, medida_antebraco_d,
                    medida_coxa_d, medida_coxa_e,
                    medida_panturrilha_e, medida_panturrilha_d,
                    foto_frente, foto_costas,
                    foto_lado_direito, foto_lado_esquerdo, foto_perfil,
                    foto_perfil_ajuste
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
                """,
                (
                    nome_completo, idade, sexo, altura_m,
                    treinou_antes, tempo_treinamento, tempo_sem_atividade,
                    objetivo_principal, objetivo_outro,
                    frequencia_semanal, tempo_treino_dia,
                    doenca_tem, doenca_qual,
                    limitacao_tem, limitacao_qual,
                    dor_tem, dor_qual,
                    cirurgia_tem, cirurgia_qual,
                    medicamento_controlado, fazendo_dieta, consumo_alcool, fuma,
                    medida_ombro, medida_torax, medida_cintura,
                    medida_abdominal, medida_quadril,
                    medida_braco_e, medida_braco_e_contraido,
                    medida_braco_d, medida_braco_d_contraido,
                    medida_antebraco_e, medida_antebraco_d,
                    medida_coxa_d, medida_coxa_e,
                    medida_panturrilha_e, medida_panturrilha_d,
                    foto_frente, foto_costas,
                    foto_lado_direito, foto_lado_esquerdo, foto_perfil,
                    foto_perfil_ajuste,
                ),
            )
            conexao.commit()
            novo_id = cursor.lastrowid
        finally:
            conexao.close()

        aluno = self.buscar_por_id(novo_id)
        assert aluno is not None
        return aluno

    def atualizar_aluno(self, aluno_id: int, **campos) -> Optional["Aluno"]:
        if not campos:
            return self.buscar_por_id(aluno_id)

        colunas_validas = set(inspect.signature(self.criar_aluno).parameters)
        campos = {chave: valor for chave, valor in campos.items() if chave in colunas_validas}
        if not campos:
            return self.buscar_por_id(aluno_id)

        atribuicoes = ", ".join(f"{coluna} = ?" for coluna in campos)
        valores = list(campos.values()) + [aluno_id]

        conexao = obter_conexao()
        try:
            conexao.execute(
                f"UPDATE alunos SET {atribuicoes} WHERE id = ?", valores
            )
            conexao.commit()
        finally:
            conexao.close()

        return self.buscar_por_id(aluno_id)

    def existe_algum_aluno(self) -> bool:
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
                    """,
                    (f"%{termo_busca}%",),
                ).fetchall()
            else:
                linhas = conexao.execute(
                    "SELECT * FROM alunos"
                ).fetchall()
            alunos = [self._linha_para_aluno(linha) for linha in linhas]
            return sorted(alunos, key=lambda aluno: _chave_alfabetica(aluno.nome_completo))
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
            altura_m=linha["altura_m"],
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
            medicamento_controlado=linha["medicamento_controlado"],
            fazendo_dieta=linha["fazendo_dieta"],
            consumo_alcool=linha["consumo_alcool"],
            fuma=linha["fuma"],
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
            foto_frente=linha["foto_frente"],
            foto_costas=linha["foto_costas"],
            foto_lado_direito=linha["foto_lado_direito"],
            foto_lado_esquerdo=linha["foto_lado_esquerdo"],
            foto_perfil=linha["foto_perfil"],
            foto_perfil_ajuste=linha["foto_perfil_ajuste"],
        )


    def adicionar_avaliacoes_circunferencias(
        self, aluno_id: int, avaliacoes: List[Dict[str, Any]]
    ) -> None:
        if not avaliacoes:
            return

        colunas = ", ".join(_COLUNAS_CIRCUNFERENCIA)
        marcadores = ", ".join("?" for _ in _COLUNAS_CIRCUNFERENCIA)

        conexao = obter_conexao()
        try:
            for avaliacao in avaliacoes:
                valores = [avaliacao.get(coluna) for coluna in _COLUNAS_CIRCUNFERENCIA]
                conexao.execute(
                    f"""
                    INSERT INTO avaliacoes_circunferencias (aluno_id, {colunas})
                    VALUES (?, {marcadores})
                    """,
                    [aluno_id, *valores],
                )
            conexao.commit()
        finally:
            conexao.close()

    def listar_avaliacoes_circunferencias(self, aluno_id: int) -> List[Dict[str, Any]]:
        colunas = ", ".join(_COLUNAS_CIRCUNFERENCIA)
        conexao = obter_conexao()
        try:
            linhas = conexao.execute(
                f"""
                SELECT {colunas} FROM avaliacoes_circunferencias
                WHERE aluno_id = ? ORDER BY id ASC
                """,
                (aluno_id,),
            ).fetchall()
            return [dict(linha) for linha in linhas]
        finally:
            conexao.close()


    def adicionar_avaliacoes_composicao(
        self, aluno_id: int, avaliacoes: List[Dict[str, Any]]
    ) -> None:
        if not avaliacoes:
            return

        colunas = ", ".join(_COLUNAS_COMPOSICAO)
        marcadores = ", ".join("?" for _ in _COLUNAS_COMPOSICAO)

        conexao = obter_conexao()
        try:
            for avaliacao in avaliacoes:
                valores = [avaliacao.get(coluna) for coluna in _COLUNAS_COMPOSICAO]
                conexao.execute(
                    f"""
                    INSERT INTO avaliacoes_composicao_corporal (aluno_id, {colunas})
                    VALUES (?, {marcadores})
                    """,
                    [aluno_id, *valores],
                )
            conexao.commit()
        finally:
            conexao.close()


    def adicionar_sessoes_fotos(self, aluno_id: int, sessoes: List[Dict[str, Any]]) -> None:
        if not sessoes:
            return
        colunas = ", ".join(_COLUNAS_SESSAO_FOTOS)
        marcadores = ", ".join("?" for _ in _COLUNAS_SESSAO_FOTOS)
        conexao = obter_conexao()
        try:
            for sessao in sessoes:
                conexao.execute(
                    f"INSERT INTO sessoes_fotos (aluno_id, {colunas}) VALUES (?, {marcadores})",
                    [aluno_id, *(sessao.get(coluna) for coluna in _COLUNAS_SESSAO_FOTOS)],
                )
            conexao.commit()
        finally:
            conexao.close()

    def listar_sessoes_fotos(self, aluno_id: int) -> List[Dict[str, Any]]:
        colunas = ", ".join(_COLUNAS_SESSAO_FOTOS)
        conexao = obter_conexao()
        try:
            linhas = conexao.execute(
                f"SELECT {colunas} FROM sessoes_fotos WHERE aluno_id = ? ORDER BY id ASC",
                (aluno_id,),
            ).fetchall()
            return [dict(linha) for linha in linhas]
        finally:
            conexao.close()

    def listar_avaliacoes_composicao(self, aluno_id: int) -> List[Dict[str, Any]]:
        colunas = ", ".join(_COLUNAS_COMPOSICAO)
        conexao = obter_conexao()
        try:
            linhas = conexao.execute(
                f"""
                SELECT {colunas} FROM avaliacoes_composicao_corporal
                WHERE aluno_id = ? ORDER BY id ASC
                """,
                (aluno_id,),
            ).fetchall()
            return [dict(linha) for linha in linhas]
        finally:
            conexao.close()
