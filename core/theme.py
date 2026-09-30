"""Paleta de cores e constantes visuais compartilhadas pela interface.

Centralizar essas definições evita duplicar códigos de cor em cada widget e
mantém a aparência consistente enquanto novas telas forem adicionadas.
"""


class Cores:
    FUNDO = "#F5F7FA"
    FUNDO_PAGINA = "#DCE8EB"
    SUPERFICIE = "#FFFFFF"
    BORDA = "#E1E4E8"

    FUNDO_LISTA = "#E8F2F4"
    BORDA_LISTA = "#DFDFDF"

    TEXTO_PRIMARIO = "#1F2937"
    TEXTO_SECUNDARIO = "#6B7280"
    TEXTO_DESCRICAO = "#374151"  # meio-termo: mais destaque que o secundário, sem virar título

    AZUL_PRIMARIO = "#2F6FED"
    AZUL_ESCURO = "#1E4FBF"
    AZUL_HOVER = "#1A45AC"

    ERRO = "#D64545"
    ERRO_FUNDO = "#FDEEEE"
    SUCESSO = "#1F9254"
    SUCESSO_FUNDO = "#EAF7EF"

    DESABILITADO_FUNDO = "#E5E7EB"
    DESABILITADO_TEXTO = "#9CA3AF"

    SCROLL_THUMB = "#B7C4C8"
    SCROLL_THUMB_HOVER = "#93A3A8"


class Fontes:
    FAMILIA = "Segoe UI"
    TAMANHO_TITULO = 22
    TAMANHO_SUBTITULO = 13
    TAMANHO_LABEL = 13
    TAMANHO_TEXTO = 14


# Barra de rolagem arredondada do app inteiro (aplicada em `main.py` via
# `QApplication.setStyleSheet`): trilho e alça em pílula, sem as setas
# quadradas do estilo nativo do Windows.
ESTILO_BARRA_ROLAGEM = f"""
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
    border-radius: 5px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 2px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background-color: {Cores.SCROLL_THUMB};
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{ min-height: 24px; }}
QScrollBar::handle:horizontal {{ min-width: 24px; }}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background-color: {Cores.SCROLL_THUMB_HOVER};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0px;
    height: 0px;
    border: none;
    background: none;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}
"""
