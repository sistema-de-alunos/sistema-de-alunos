from typing import Optional, Tuple

IDADE_MINIMA = 5
IDADE_MAXIMA = 100

ALTURA_MINIMA_M = 1.00
ALTURA_MAXIMA_M = 2.50

SEXO_OPCOES = ["Masculino", "Feminino"]


def validar_nome_completo(nome: str) -> Optional[str]:
    nome = (nome or "").strip()
    if not nome:
        return "Informe o nome completo do aluno."
    if len(nome) < 3:
        return "Digite o nome completo do aluno."
    return None


def validar_idade(idade_texto: str) -> Tuple[Optional[int], Optional[str]]:
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
    if valor not in ("Sim", "Não"):
        return "Selecione uma opção."
    return None


def validar_tempo_treinamento(valor: str) -> Optional[str]:
    if not (valor or "").strip():
        return "Informe há quanto tempo treina."
    return None


def validar_tempo_sem_atividade(valor: str) -> Optional[str]:
    if not (valor or "").strip():
        return "Informe o tempo sem atividade física."
    return None


OBJETIVO_OPCOES = ("emagrecimento", "hipertrofia", "condicionamento", "reabilitacao", "outro")


def validar_objetivo_principal(valor: Optional[str]) -> Optional[str]:
    if valor not in OBJETIVO_OPCOES:
        return "Selecione um objetivo."
    return None


FREQUENCIA_SEMANAL_OPCOES = ["3 dias", "4 dias", "5 dias"]

TEMPO_TREINO_OPCOES = ["30 minutos", "1 horas", "1:30 horas", "2 horas", "2:30 horas", "3+ horas"]


def validar_frequencia_semanal(valor: Optional[str]) -> Optional[str]:
    if valor not in FREQUENCIA_SEMANAL_OPCOES:
        return "Selecione uma opção."
    return None


def validar_tempo_treino_dia(valor: Optional[str]) -> Optional[str]:
    if valor not in TEMPO_TREINO_OPCOES:
        return "Selecione uma opção."
    return None
