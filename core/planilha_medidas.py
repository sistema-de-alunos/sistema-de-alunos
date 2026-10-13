"""Planilha de medidas (.xlsx) de uma data, no formato dos modelos ADIPÔMETRO.

Usa só a biblioteca padrão: os modelos compactos em assets/planilhas já têm
layout, estilos e imagens (gerados por tools/gerar_modelos_planilha.py); aqui
só preenchemos a coluna C. As fórmulas vão junto com o valor já calculado, para
os números aparecerem em visualizadores que não recalculam (celular, prévia).
"""
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Dict, Optional
from xml.sax.saxutils import escape

_PASTA_MODELOS = Path(__file__).resolve().parent.parent / "assets" / "planilhas"
_PLANILHA_XML = "xl/worksheets/sheet1.xml"

_LINHAS_CIRCUNFERENCIAS = {
    "ombro": 3, "torax": 4, "cintura": 5, "abdominal": 6, "quadril": 7,
    "braco_e": 8, "braco_e_contraido": 9, "antebraco_e": 10,
    "braco_d": 11, "braco_d_contraido": 12, "antebraco_d": 13,
    "coxa_e": 14, "coxa_d": 15, "panturrilha_e": 16, "panturrilha_d": 17,
}
_LINHAS_DOBRAS = {
    "triceps": 22, "peito": 23, "axilar_media": 24, "subescapular": 25,
    "dobra_abdominal": 26, "supra_iliaca": 27, "coxa_dobra": 28,
}
_LINHAS_DATA = (2, 21, 33)
_LINHA_PESO = 30

# Exatamente como em cada modelo: coeficientes de Jackson & Pollock (7 dobras)
# e o piso do % de gordura (o feminino zera abaixo de 4,5; o masculino abaixo de 0).
_REGRAS_MODELO = {
    "Masculino": {
        "arquivo": "medidas_masculino.xlsx",
        "coeficientes": (1.112, 0.00043499, 0.00000055, 0.00028826),
        "piso_percentual": 0,
    },
    "Feminino": {
        "arquivo": "medidas_feminino.xlsx",
        "coeficientes": (1.097, 0.00046971, 0.00000056, 0.00012828),
        "piso_percentual": 4.5,
    },
}


def nome_arquivo_medidas(nome_aluno: str, data: date) -> str:
    nome = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", nome_aluno or "").strip(" .")
    nome = re.sub(r"\s+", "_", nome) or "Aluno"
    return f"Medidas_{nome}_{data:%d-%m-%Y}.xlsx"


def _composicao(regras: dict, idade: Optional[int], peso: Optional[float], dobras: list) -> dict:
    """Mesma conta das fórmulas gravadas na planilha; vazio onde a fórmula dá ""."""
    if idade is None or peso is None or any(valor is None for valor in dobras):
        return {}
    intercepto, coef_s, coef_s2, coef_idade = regras["coeficientes"]
    soma = sum(dobras)
    densidade = (intercepto - coef_s * soma) + (coef_s2 * soma * soma) - (coef_idade * idade)
    bruto = ((4.95 / densidade) - 4.5) * 100
    massa_gorda = peso * (bruto / 100)
    return {
        38: densidade,
        37: bruto,
        36: 0 if bruto < regras["piso_percentual"] else bruto,
        35: massa_gorda,
        34: peso - massa_gorda,
    }


def _formulas(regras: dict, idade: int) -> Dict[int, str]:
    intercepto, coef_s, coef_s2, coef_idade = regras["coeficientes"]
    return {
        38: (
            f'IF(OR(COUNT(C22:C28)<7,C30=""),"",'
            f"({intercepto}-{coef_s:.8f}*SUM(C22:C28))+({coef_s2:.8f}*SUM(C22:C28)*SUM(C22:C28))"
            f"-({coef_idade:.8f}*{idade}))"
        ),
        37: 'IFERROR(((4.95/C38)-4.5)*100,"")',
        36: f'IF(C37="","",IF(C37<{regras["piso_percentual"]},0,C37))',
        35: 'IF(C37="","",C30*(C37/100))',
        34: 'IF(C35="","",C30-C35)',
    }


def _definir_celula(xml: str, linha: int, valor=None, formula: Optional[str] = None) -> str:
    referencia = f"C{linha}"

    def substituir(achado):
        estilo = achado.group(1) or ""
        if formula is None:
            return f'<c r="{referencia}"{estilo}><v>{valor!r}</v></c>'
        if valor is None:
            return f'<c r="{referencia}"{estilo} t="str"><f>{escape(formula)}</f><v></v></c>'
        return f'<c r="{referencia}"{estilo}><f>{escape(formula)}</f><v>{valor!r}</v></c>'

    xml, trocas = re.subn(rf'<c r="{referencia}"( s="\d+")?[^>]*?/>', substituir, xml)
    if trocas != 1:
        raise ValueError(f"Célula {referencia} não encontrada no modelo da planilha.")
    return xml


def gerar_planilha_medidas(
    destino,
    *,
    sexo: str,
    idade: Optional[int],
    data: date,
    circunferencias: Dict[str, Optional[float]],
    dobras: Dict[str, Optional[float]],
    peso: Optional[float],
) -> None:
    regras = _REGRAS_MODELO.get(sexo)
    if regras is None:
        raise ValueError("A planilha só existe para sexo Masculino ou Feminino.")

    with zipfile.ZipFile(_PASTA_MODELOS / regras["arquivo"]) as modelo:
        arquivos = {item: modelo.read(item) for item in modelo.namelist()}
    xml = arquivos[_PLANILHA_XML].decode("utf-8")

    serial_data = (data - date(1899, 12, 30)).days
    for linha in _LINHAS_DATA:
        xml = _definir_celula(xml, linha, serial_data)

    valores = {}
    for chave, linha in _LINHAS_CIRCUNFERENCIAS.items():
        valores[linha] = circunferencias.get(chave)
    for chave, linha in _LINHAS_DOBRAS.items():
        valores[linha] = dobras.get(chave)
    valores[_LINHA_PESO] = peso
    for linha, valor in valores.items():
        if valor is not None:
            xml = _definir_celula(xml, linha, float(valor))

    if idade is not None:
        resultados = _composicao(regras, idade, peso, [dobras.get(chave) for chave in _LINHAS_DOBRAS])
        for linha, formula in _formulas(regras, idade).items():
            xml = _definir_celula(xml, linha, resultados.get(linha), formula)

    arquivos[_PLANILHA_XML] = xml.encode("utf-8")
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as saida:
        for item, conteudo in arquivos.items():
            saida.writestr(item, conteudo)
