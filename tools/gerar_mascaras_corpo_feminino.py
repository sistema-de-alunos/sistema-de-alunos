"""Gera as máscaras de região do boneco FEMININO (`assets/corpos/corpomulher.png`).

Irmã de `tools/gerar_mascaras_corpo.py` (o gerador do boneco masculino) —
mesma técnica (segmentação watershed a partir de sementes calibradas
visualmente), duplicada aqui em vez de importada porque, como o cabeçalho
daquele arquivo já avisa, cada imagem tem sua própria pose/proporções e
precisa de sementes recalibradas do zero; só a INFRAESTRUTURA do algoritmo
(silhueta, elevação, salvar_mascara, polígono de recorte) é idêntica. Ver os
comentários de `gerar_mascaras_corpo.py` para a explicação completa de cada
etapa — aqui só o que é específico do corpo feminino é comentado.

FERRAMENTA DE DESENVOLVIMENTO -- não é executada pelo app; numpy/scipy/
scikit-image/Pillow são dependência só deste script (ver `tools/requirements.txt`).
Rode de novo apenas se `assets/corpos/corpomulher.png` for substituída.

COMO RECALIBRAR: mesmo fluxo do script masculino -- rode, abra
`assets/corpos/watershed_debug_feminino.png` (cada região com uma cor), ajuste
as coordenadas problemáticas em `SEMENTES` (frações 0-1 da imagem) e rode de
novo.
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.filters import gaussian, sobel
from skimage.segmentation import watershed
from skimage.morphology import (
    disk as morph_disk,
    binary_closing as m_close,
    binary_dilation as m_dilate,
    binary_opening as m_open,
    remove_small_objects,
)
from skimage.draw import disk as draw_disk

RAIZ = Path(__file__).resolve().parent.parent
IMAGEM = RAIZ / "assets" / "corpos" / "corpomulher.png"
PASTA_SAIDA = RAIZ / "assets" / "corpos" / "mascaras_feminino"

# Metade do raio usado no masculino (80): aqui só precisa fechar os
# traços finos do próprio desenho (estrias musculares, tendões do punho,
# dedos) -- um raio maior que isso soldava por engano o vão real entre
# axila e quadril (a concavidade da cintura), estourando o contorno de
# "hip"/"waist" num bloco de cantos retos (visível comparando a máscara
# gerada com raios 40 e 80 lado a lado; 80 já achata a lateral do quadril
# numa faixa reta constante por várias linhas, 40 mantém a curva orgânica).
RAIO_FECHAMENTO_SILHUETA = 40
SIGMA_BLUR_ELEVACAO = 3.0
# Mesmo ajuste feito no script masculino, e pela mesma razão: a fronteira
# quadril/coxa na virilha tinha gradiente fraco e o watershed com
# COMPACTNESS baixo produzia uma fronteira caótica/serrilhada (confirmado
# comparando visualmente 4e-4 x 1e-3 sobre esta imagem) em vez de acompanhar
# a curva anatômica real -- ver o comentário longo em
# `gerar_mascaras_corpo.py` junto de COMPACTNESS para a explicação completa.
COMPACTNESS = 1e-3
COR_VERDE = (46, 204, 113)  # Cores.SUCESSO (core/theme.py) -- mesma do masculino

# Sementes (frações 0-1 de largura/altura) calibradas visualmente sobre
# corpomulher.png (1024x1536, figura de frente, mesma pose/enquadramento do
# corpohomem.png). Convenção anatômica igual à do masculino: "right_*"/
# "left_*" são o lado DIREITO/ESQUERDO da PESSOA -- invertidos (esquerda/
# direita) para quem olha a imagem de frente. Proporções diferem do
# masculino (busto, cintura mais estreita, quadril mais largo, pernas
# praticamente sem vão entre si) -- por isso todas as coordenadas foram
# recalibradas do zero sobre esta imagem, não copiadas do outro script.
SEMENTES = {
    "ignore_face": [(0.50, 0.06)],
    "ignore_neck": [(0.50, 0.155)],
    "shoulder": [(0.335, 0.195), (0.665, 0.195)],
    # Semente extra no meio do esterno (mesmo motivo do masculino: sem ela
    # "abdomen" sobe pelo sulco entre os dois lóbulos do peitoral).
    "chest": [(0.44, 0.27), (0.565, 0.27), (0.50, 0.215)],
    "abdomen": [
        (0.465, 0.315), (0.535, 0.315),
        (0.465, 0.345), (0.535, 0.345),
        (0.465, 0.375), (0.535, 0.375),
    ],
    "waist": [(0.385, 0.335), (0.615, 0.335)],
    "hip": [
        (0.50, 0.415), (0.50, 0.445),
        (0.40, 0.42), (0.60, 0.42),
        (0.365, 0.45), (0.635, 0.45),
    ],
    "right_arm": [(0.34, 0.24), (0.33, 0.28), (0.32, 0.31)],
    "left_arm": [(0.66, 0.24), (0.67, 0.28), (0.68, 0.31)],
    "right_forearm": [(0.27, 0.35), (0.24, 0.39), (0.20, 0.43)],
    "left_forearm": [(0.73, 0.35), (0.76, 0.39), (0.80, 0.43)],
    "ignore_hand_right": [(0.18, 0.50), (0.18, 0.46), (0.24, 0.46), (0.16, 0.52)],
    "ignore_hand_left": [(0.82, 0.50), (0.82, 0.46), (0.76, 0.46), (0.84, 0.52)],
    "right_thigh": [(0.41, 0.50), (0.39, 0.55), (0.42, 0.60)],
    "left_thigh": [(0.585, 0.50), (0.605, 0.55), (0.575, 0.60)],
    "right_calf": [(0.41, 0.70), (0.40, 0.76), (0.40, 0.81)],
    "left_calf": [(0.595, 0.70), (0.605, 0.76), (0.60, 0.81)],
    "ignore_foot_right": [(0.385, 0.92)],
    "ignore_foot_left": [(0.615, 0.92)],
}

# Ao contrário do masculino, esta imagem não tem um vão de fundo real entre
# o antebraço pendurado e o quadril (checado diretamente: a silhueta SEM
# fechamento nenhum já sai contígua ali -- gray>=100 o caminho todo), então
# não existe aqui o "vão que o fechamento solda por engano" que motivou
# `ZONAS_EXCLUSAO_FECHAMENTO` no script masculino. Por isso não há zona de
# exclusão nesta versão -- ver `RAIO_FECHAMENTO_SILHUETA` abaixo.
ZONAS_EXCLUSAO_FECHAMENTO: list = []

# Trava lateral (fração x mín, máx) na linha média -- as pernas femininas
# praticamente se tocam da virilha até o joelho (sem vão de fundo real como
# no masculino), então o watershed sozinho não teria como separar
# coxa/panturrilha esquerda da direita: nenhuma das duas tem razão
# anatômica pra cruzar a linha média do corpo, então essa trava geométrica
# faz a separação (mesma técnica já usada no masculino, aqui necessária
# para TODAS as pernas, não só como reforço pontual). "hip" não entra aqui
# -- ver `RAIO_FECHAMENTO_SILHUETA` abaixo para o motivo.
LIMITE_LATERAL = {
    "right_thigh": (0.0, 0.50),
    "left_thigh": (0.50, 1.0),
    "right_calf": (0.0, 0.50),
    "left_calf": (0.50, 1.0),
}

LIMITE_SUPERIOR: dict = {}

# HISTÓRICO: "right_forearm" tinha um recorte retangular aqui (subtraindo
# um retângulo `(x_máximo, y_mín, y_máx)` direto da máscara final) para
# esconder um "bico" fino que vazava pro fundo escuro entre o cotovelo e o
# tronco -- exatamente o tipo de "aproximação por retângulo" que não pode
# mais existir. Com COMPACTNESS = 1e-3 (ver acima) o próprio contorno já
# sai sem esse bico -- confirmado no perfil de largura por linha: a região
# cresce gradualmente (24px -> 52px -> 88px -> 100px, entre y=0.33 e 0.37),
# sem nenhum salto súbito -- então o recorte retangular não é mais
# necessário. Removido; nada substitui.
JANELA_NOTCH_LATERAL: dict = {}


# "waist" também não usa o resultado bruto do watershed aqui -- mesmo motivo
# do masculino (ver o comentário grande em `gerar_mascaras_corpo.py`): nesta
# ilustração o flanco do tronco (axila -> lateral das costelas -> oblíquo)
# é uma superfície lisa, quase sem textura própria que separe esse musculo
# do peitoral/abdômen vizinhos -- sem uma borda de gradiente forte pra
# seguir, o watershed caiu na regra de distância entre sementes e vazou tanto
# pra dentro (sobre chest/abdomen) quanto pra fora (até a axila do braço).
#
# PRIMEIRA TENTATIVA (descartada): um polígono fixo (`POLIGONO_CINTURA_LADO`)
# contornado a olho, direto sobre `corpomulher.png`. Duas calibrações desse
# polígono (y=0.205 e depois y=0.300 pro topo) foram testadas e as DUAS
# davam coordenadas plausíveis (dentro da silhueta, entre tórax e quadril) e
# AINDA ASSIM ficavam anatomicamente erradas -- confirmado só depois de
# renderizar o `CorpoInterativoWidget` de verdade (`w.grab()`) e OLHAR o
# resultado, não calculando bounding box: o verde ficava sentado em cima do
# próprio reto abdominal/oblíquo interno, sem alcançar a borda lateral real
# do tronco, com bordas retas de polígono em vez de acompanhar a curva
# orgânica da pele. Bounding box correto não é prova de posição anatômica
# correta -- um polígono pode estar 100% dentro da faixa "entre tórax e
# quadril" e ainda cobrir o pedaço errado dessa faixa.
#
# SOLUÇÃO ATUAL: em vez de coordenadas fixas, a faixa da cintura é derivada
# da própria silhueta do tronco, linha por linha (`_faixa_lateral_cintura`)
# -- ela gruda na borda externa REAL do corpo em cada altura (que a silhueta
# já conhece) e se estende uma largura fixa pra dentro, então acompanha
# automaticamente qualquer curva (estreita na cintura, alarga perto do
# quadril) sem depender de pontos desenhados a olho. Ainda cortada por
# `corpo_mask_cintura` e pelas regiões vizinhas já decididas (mesma ideia de
# antes) -- isso dá o recorte fino contra tórax/abdômen/quadril/braço; a
# faixa só precisa ser uma superestimativa generosa da região lateral.
_VIZINHAS_CINTURA = ("chest", "abdomen", "hip", "right_arm", "left_arm")

# SEGUNDO AJUSTE (depois de comparar com o app real de novo): os valores
# antigos (Y0=0.270, Y1=0.440, largura=0.090) pareciam razoáveis olhando só
# o contorno externo, mas media a largura REAL do torso linha a linha
# (`m40`, silhueta padrão) e o erro apareceu nos números, não só no olho:
# no ponto mais estreito do tronco (~y=0.33, a cintura de verdade) o torso
# INTEIRO mede ~160px de largura, mas a faixa antiga reivindicava 90px de
# CADA lado -- 180px, mais que o torso inteiro naquela altura. Sobrava
# quase nada pro abdômen no centro, e o resultado visual era um bloco
# grosso em vez de uma faixa fina lateral (mesmo sem tocar braço/fundo).
#
# Intervalo vertical: reduzido para a faixa onde o torso realmente fica
# "achatado" (largura quase constante e mínima -- medido diretamente:
# y=0.312 a 0.350 é onde a largura fica dentro de 6% do mínimo absoluto).
# Y0/Y1 abaixo dão uma margem pequena pra fora desse platô central, não o
# intervalo tórax->quadril inteiro como antes -- isso é o que cria o "vão"
# visível entre tórax/cintura/quadril (a cintura precisa PARECER uma faixa
# estreita, não preencher todo o espaço disponível entre as duas).
_CINTURA_Y0, _CINTURA_Y1 = 0.300, 0.365

# Largura (fração da largura da imagem) da faixa, medida a partir da borda
# externa do tronco pra dentro. Reduzida de 0.090 pra 0.038 (~39px): no
# ponto mais estreito do torso (~160px de largura total), isso deixa ~82px
# pro abdômen no centro -- perto de metade/metade entre oblíquo (cintura) e
# reto abdominal, em vez de a cintura sozinha reivindicar quase tudo.
_CINTURA_LARGURA_FAIXA = 0.038

# Raio de dilatação aplicado às regiões de braço/antebraço antes de excluí-
# las do tronco (ver `_faixa_lateral_cintura`): sem isso, a franja de
# antialiasing/1-2px de ruído na fronteira braço-tronco do watershed cruzava
# pra dentro do torso e picotava a borda externa detectada linha a linha.
_CINTURA_DILATACAO_EXCLUSAO_BRACO = 3


def _faixa_lateral_cintura(h: int, w: int, corpo_mask_cintura: np.ndarray, rotulos_ws: np.ndarray, nome_para_id: dict) -> np.ndarray:
    """Faixa lateral (os dois flancos) derivada da silhueta real do tronco.

    Isola o tronco (silhueta ampla menos braço/antebraço, maior componente
    conexo -- ver comentário grande acima) e, para cada linha dentro de
    [_CINTURA_Y0, _CINTURA_Y1], marca uma faixa de _CINTURA_LARGURA_FAIXA a
    partir da borda externa detectada NAQUELA linha, dos dois lados. Como a
    borda é recalculada linha a linha a partir da silhueta de verdade, a
    faixa acompanha organicamente qualquer curva (estreita na cintura,
    alarga perto do quadril) em vez de seguir pontos fixos desenhados a
    olho.
    """
    excl_bracos = np.zeros((h, w), dtype=bool)
    for nome in ("right_arm", "left_arm", "right_forearm", "left_forearm"):
        excl_bracos |= rotulos_ws == nome_para_id[nome]
    excl_bracos = m_dilate(excl_bracos, morph_disk(_CINTURA_DILATACAO_EXCLUSAO_BRACO))

    tronco = corpo_mask_cintura & ~excl_bracos
    rotulos_tronco, n_componentes = ndimage.label(tronco, structure=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
    if n_componentes == 0:
        return np.zeros((h, w), dtype=bool)
    tamanhos = ndimage.sum(tronco, rotulos_tronco, range(1, n_componentes + 1))
    tronco_principal = rotulos_tronco == (int(np.argmax(tamanhos)) + 1)

    largura_px = int(_CINTURA_LARGURA_FAIXA * w)
    faixa = np.zeros((h, w), dtype=bool)
    y0, y1 = int(_CINTURA_Y0 * h), int(_CINTURA_Y1 * h)
    for y in range(y0, y1):
        xs = np.where(tronco_principal[y])[0]
        if xs.size == 0:
            continue
        esquerda, direita = xs[0], xs[-1]
        faixa[y, esquerda : esquerda + largura_px] = True
        faixa[y, max(esquerda, direita - largura_px) : direita] = True
    return faixa


# HISTÓRICO (raio + retângulos removidos nesta revisão -- ver por quê
# abaixo): a máscara auxiliar usada ao recortar "waist" (`corpo_mask_cintura`
# em `main()`) precisava recuperar o flanco do tronco (axila -> lateral das
# costelas), sombreado o bastante nesta ilustração para cair abaixo do
# limiar `gray<100` mesmo sendo pele de verdade -- com a silhueta padrão
# (raio 40) essa faixa ficava fora e cortava quase toda a máscara de
# "waist". A tentativa anterior usava um FECHAMENTO com raio grande (90)
# restrito a retângulos fixos "permitidos" nos flancos -- mas, renderizando
# o `CorpoInterativoWidget` de verdade (não só olhando a máscara isolada),
# esses retângulos apareciam como blocos verdes flutuando ao lado do tronco,
# sem tocar o contorno real: com raio 90, o fechamento preenche o retângulo
# inteiro (mais largo que 2×raio) uma vez que ele cabe dentro do alcance de
# fechamento -- não recupera só a sombra, vira ele mesmo um retângulo.
#
# CORREÇÃO: em vez de fechamento+retângulo, dilata a própria silhueta
# padrão (já com o contorno orgânico correto) por uma margem pequena. Isso
# recupera pele próxima à borda real do corpo (a franja sombreada) mantendo
# a forma orgânica da silhueta -- nunca cria um blob desconectado, porque
# cada pixel adicionado é, por construção, vizinho de um pixel que já era
# corpo de verdade. `_faixa_lateral_cintura` usa esta versão só para achar a
# borda externa do tronco por linha; o resultado ainda é sempre recortado
# pelas regiões vizinhas já decididas (`_VIZINHAS_CINTURA`), então uma
# margem generosa demais não invade tórax/abdômen/quadril/braço.
RAIO_RECUPERAR_SOMBRA_CINTURA = 25


def calcular_silhueta(
    gray: np.ndarray,
    raio_fechamento: int = RAIO_FECHAMENTO_SILHUETA,
) -> np.ndarray:
    h, w = gray.shape
    bg_candidato = gray < 100
    estrutura = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    rotulos_fundo, _ = ndimage.label(bg_candidato, structure=estrutura)
    rotulos_borda = (
        set(rotulos_fundo[0, :]) | set(rotulos_fundo[-1, :])
        | set(rotulos_fundo[:, 0]) | set(rotulos_fundo[:, -1])
    )
    rotulos_borda.discard(0)
    corpo_bruto = ~np.isin(rotulos_fundo, list(rotulos_borda))
    corpo_bruto = ndimage.binary_fill_holes(corpo_bruto)

    corpo_fechado = m_close(corpo_bruto, morph_disk(raio_fechamento))

    zona_exclusao = np.zeros((h, w), dtype=bool)
    for (x0, x1, y0, y1) in ZONAS_EXCLUSAO_FECHAMENTO:
        zona_exclusao[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = True

    fechamento_extra = corpo_fechado & ~zona_exclusao

    return corpo_bruto | fechamento_extra


FECHAMENTO_EXTRA: dict = {
    "waist": 7,
}


def salvar_mascara(
    caminho: Path, binaria: np.ndarray, corpo_mask: np.ndarray, h: int, w: int, raio_fechamento: int = 4
) -> None:
    binaria = m_close(binaria, morph_disk(raio_fechamento))
    binaria = remove_small_objects(binaria, min_size=250)
    binaria = m_open(binaria, morph_disk(1))

    alfa = gaussian(binaria.astype(np.float64), sigma=1.2)
    alfa = np.clip(alfa / max(alfa.max(), 1e-6), 0, 1)

    dist_dentro = ndimage.distance_transform_edt(binaria)
    anel_borda = (dist_dentro > 0) & (dist_dentro <= 3)
    alfa[anel_borda] = np.maximum(alfa[anel_borda], 0.92)

    alfa *= corpo_mask

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = COR_VERDE
    rgba[..., 3] = (alfa * 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(caminho)


def main() -> None:
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    img = Image.open(IMAGEM).convert("RGB")
    arr = np.array(img).astype(np.float64)
    h, w, _ = arr.shape
    gray = arr.mean(axis=2)

    corpo_mask = calcular_silhueta(gray)
    # Ver `RAIO_RECUPERAR_SOMBRA_CINTURA`: dilata a silhueta padrão (já com
    # contorno orgânico correto) por uma margem pequena, em vez do
    # fechamento+retângulo antigo -- recupera a franja sombreada do flanco
    # sem nunca criar um blob desconectado do corpo.
    corpo_mask_cintura = m_dilate(corpo_mask, morph_disk(RAIO_RECUPERAR_SOMBRA_CINTURA))

    elevacao = sobel(gaussian(gray / 255.0, sigma=SIGMA_BLUR_ELEVACAO))

    nomes = list(SEMENTES.keys())
    nome_para_id = {nome: i + 1 for i, nome in enumerate(nomes)}
    marcadores = np.zeros((h, w), dtype=np.int32)
    for nome, pontos in SEMENTES.items():
        idx = nome_para_id[nome]
        for (fx, fy) in pontos:
            cy, cx = int(round(fy * h)), int(round(fx * w))
            rr, cc = draw_disk((cy, cx), 9, shape=(h, w))
            marcadores[rr, cc] = idx

    rotulos_ws = watershed(elevacao, markers=marcadores, mask=corpo_mask, compactness=COMPACTNESS)

    mascara_cintura_final = None  # preenchida ao processar "waist", usada por "hip" logo abaixo

    for nome in nomes:
        if nome.startswith("ignore"):
            continue
        idx = nome_para_id[nome]
        if nome == "waist":
            vizinhas = np.zeros_like(corpo_mask)
            for vizinha in _VIZINHAS_CINTURA:
                vizinhas |= rotulos_ws == nome_para_id[vizinha]
            faixa = _faixa_lateral_cintura(h, w, corpo_mask_cintura, rotulos_ws, nome_para_id)
            binaria = faixa & corpo_mask_cintura & ~vizinhas
            mascara_cintura_final = binaria
        elif nome == "hip":
            # Sem o polígono manual que "waist" usa, o resultado bruto do
            # watershed para "hip" ainda reivindica um pedaço do flanco
            # lateral (mesma área de baixo gradiente que fez "waist"
            # vazar) -- sobra como um bloco de cantos retos colado nas
            # laterais do quadril. "waist" já foi decidida (dict
            # preserva a ordem de inserção, "waist" vem antes de "hip"
            # em SEMENTES) com um contorno correto, então subtraí-la
            # aqui -- junto dos braços, mesmo raciocínio -- corrige o
            # vazamento na raiz em vez de só cortar reto com LIMITE_LATERAL.
            binaria = (
                (rotulos_ws == idx)
                & ~mascara_cintura_final
                & ~(rotulos_ws == nome_para_id["right_arm"])
                & ~(rotulos_ws == nome_para_id["left_arm"])
            )
        else:
            binaria = rotulos_ws == idx
        if nome in LIMITE_LATERAL:
            x0f, x1f = LIMITE_LATERAL[nome]
            binaria = binaria.copy()
            binaria[:, : int(x0f * w)] = False
            binaria[:, int(x1f * w) :] = False
        if nome in LIMITE_SUPERIOR:
            binaria = binaria.copy()
            binaria[: int(LIMITE_SUPERIOR[nome] * h), :] = False
        if nome in JANELA_NOTCH_LATERAL:
            x_maxf, y0f, y1f = JANELA_NOTCH_LATERAL[nome]
            binaria = binaria.copy()
            binaria[int(y0f * h) : int(y1f * h), int(x_maxf * w) :] = False
        # "waist" precisa do recorte final com `corpo_mask_cintura` (a
        # silhueta dilatada -- ver `RAIO_RECUPERAR_SOMBRA_CINTURA`), não com
        # `corpo_mask` (raio 40 sem dilatação, padrão de todas as outras
        # regiões): o flanco sombreado usado por "waist" cai abaixo do
        # limiar de silhueta com o raio padrão, então recortar por
        # `corpo_mask` derrubaria a máscara de volta a quase nada.
        mascara_final = corpo_mask_cintura if nome == "waist" else corpo_mask
        salvar_mascara(
            PASTA_SAIDA / f"{nome}.png", binaria, mascara_final, h, w,
            raio_fechamento=FECHAMENTO_EXTRA.get(nome, 4),
        )
        print(f"{nome}: {binaria.sum()} px -> {PASTA_SAIDA / f'{nome}.png'}")

    import colorsys

    debug = (arr * 0.35).astype(np.uint8)
    for i, nome in enumerate(n for n in nomes if not n.startswith("ignore")):
        idx = nome_para_id[nome]
        hue = (i * 0.61803398875) % 1.0
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.85, 1.0)]
        debug[rotulos_ws == idx] = [r, g, b]
    caminho_debug = PASTA_SAIDA.parent / "watershed_debug_feminino.png"
    Image.fromarray(debug).save(caminho_debug)
    print("depuração salva em", caminho_debug)


if __name__ == "__main__":
    main()
