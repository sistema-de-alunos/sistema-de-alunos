"""Validações dos formulários de cadastro, com mensagens em linguagem simples.

Mantidas fora dos widgets para poderem ser reaproveitadas por futuras etapas
do cadastro (avaliação física, medidas, etc.) e testadas isoladamente.
"""

from typing import Optional, Tuple

IDADE_MINIMA = 5
IDADE_MAXIMA = 100

# A máscara de entrada da Etapa 1 (ver `_CampoAlturaMascarada` em
# cadastro_alunos.py) só produz valores entre 0.00 e 9.99 (1 dígito inteiro,
# sempre 0-9) -- a faixa abaixo é o recorte, dentro disso, coerente com
# altura humana real (rejeita "0.00"/"0.50"/"9.99", por exemplo).
ALTURA_MINIMA_M = 1.00
ALTURA_MAXIMA_M = 2.50

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


def validar_altura(altura_texto: str) -> Tuple[Optional[float], Optional[str]]:
    """Retorna (altura_m, None) se válida, ou (None, mensagem_de_erro).

    Formato oficial do campo: METROS.CENTÍMETROS (ex.: "1.75" = 1 metro e
    75 centímetros = 175 cm) -- NUNCA centímetros soltos ("175" é rejeitado
    pela faixa abaixo, não reinterpretado). Na tela, o ponto já chega pronto
    sozinho -- é a máscara de entrada em tempo real do próprio campo
    (`_CampoAlturaMascarada`) que transforma "186" digitado em "1.86"
    enquanto o personal digita, sem exigir "." nem "," dele. Esta função
    também aceita vírgula ("1,75") só por robustez (ex.: se o texto vier de
    outro lugar sem passar pela máscara) -- normalizada para ponto antes de
    converter, mas o valor matemático é sempre o mesmo (1,75 == 1.75 ==
    1.75 m). O valor retornado é em METROS; quem precisar de centímetros
    (ex.: a fórmula RFM da composição corporal) converte explicitamente com
    "× 100" no ponto de uso.
    """
    texto = (altura_texto or "").strip().replace(",", ".")
    if not texto:
        return None, "Informe a altura do aluno."
    try:
        altura_m = float(texto)
    except ValueError:
        return None, "Informe a altura em metros, no formato 1.75."

    if altura_m < ALTURA_MINIMA_M or altura_m > ALTURA_MAXIMA_M:
        return None, f"Informe uma altura entre {ALTURA_MINIMA_M:.2f} e {ALTURA_MAXIMA_M:.2f} m."
    return round(altura_m, 2), None


def validar_treinou_antes(valor: Optional[str]) -> Optional[str]:
    """Etapa 2 (Anamnese): exige que 'Sim' ou 'Não' tenha sido escolhido."""
    if valor not in ("Sim", "Não"):
        return "Selecione uma opção."
    return None


def validar_tempo_treinamento(valor: str) -> Optional[str]:
    """Etapa 2 (Anamnese): texto livre, mas obrigatório (espaços não contam)."""
    if not (valor or "").strip():
        return "Informe há quanto tempo treina."
    return None


def validar_tempo_sem_atividade(valor: str) -> Optional[str]:
    """Etapa 2 (Anamnese): texto livre, mas obrigatório (espaços não contam)."""
    if not (valor or "").strip():
        return "Informe o tempo sem atividade física."
    return None


OBJETIVO_OPCOES = ("emagrecimento", "hipertrofia", "condicionamento", "reabilitacao", "outro")


def validar_objetivo_principal(valor: Optional[str]) -> Optional[str]:
    """Etapa 3 (Anamnese): exige que um dos objetivos tenha sido escolhido."""
    if valor not in OBJETIVO_OPCOES:
        return "Selecione um objetivo."
    return None


FREQUENCIA_SEMANAL_OPCOES = ["3 dias", "4 dias", "5 dias"]

TEMPO_TREINO_OPCOES = ["30 minutos", "1 horas", "1:30 horas", "2 horas", "2:30 horas", "3+ horas"]


def validar_frequencia_semanal(valor: Optional[str]) -> Optional[str]:
    """Etapa 4 (Anamnese): exige uma das opções fixas de frequência semanal."""
    if valor not in FREQUENCIA_SEMANAL_OPCOES:
        return "Selecione uma opção."
    return None


def validar_tempo_treino_dia(valor: Optional[str]) -> Optional[str]:
    """Etapa 4 (Anamnese): exige uma das opções fixas de tempo de treino por dia."""
    if valor not in TEMPO_TREINO_OPCOES:
        return "Selecione uma opção."
    return None
