"""Validações dos formulários de cadastro, com mensagens em linguagem simples.

Mantidas fora dos widgets para poderem ser reaproveitadas por futuras etapas
do cadastro (avaliação física, medidas, etc.) e testadas isoladamente.
"""

from typing import Optional, Tuple

IDADE_MINIMA = 5
IDADE_MAXIMA = 100

SEXO_OPCOES = ["Masculino", "Feminino", "Outro", "Prefiro não informar"]


def validar_nome_completo(nome: str) -> Optional[str]:
    """Retorna a mensagem de erro, ou None se o nome for válido."""
    nome = (nome or "").strip()
    if not nome:
        return "Informe o nome completo do aluno."
    if len(nome) < 3:
        return "Digite o nome completo do aluno."
    return None


def validar_idade(idade_texto: str) -> Tuple[Optional[int], Optional[str]]:
    """Retorna (idade, None) se válida, ou (None, mensagem_de_erro)."""
    texto = (idade_texto or "").strip()
    if not texto:
        return None, "Informe a idade do aluno."
    if not texto.isdigit():
        return None, "Informe a idade usando apenas números."

    idade = int(texto)
    if idade < IDADE_MINIMA or idade > IDADE_MAXIMA:
        return None, f"Informe uma idade entre {IDADE_MINIMA} e {IDADE_MAXIMA} anos."
    return idade, None


def validar_sexo(sexo: str) -> Optional[str]:
    if not sexo or sexo not in SEXO_OPCOES:
        return "Selecione uma opção."
    return None


def validar_treinou_antes(valor: Optional[str]) -> Optional[str]:
    """Etapa 2 (Anamnese): exige que 'Sim' ou 'Não' tenha sido escolhido."""
    if valor not in ("Sim", "Não"):
        return "Selecione uma opção."
    return None


OBJETIVO_OPCOES = ("emagrecimento", "hipertrofia", "condicionamento", "reabilitacao", "outro")


def validar_objetivo_principal(valor: Optional[str]) -> Optional[str]:
    """Etapa 3 (Anamnese): exige que um dos objetivos tenha sido escolhido."""
    if valor not in OBJETIVO_OPCOES:
        return "Selecione um objetivo."
    return None
