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
COMPACTNESS = 4e-4
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

# Trava adicional só pra "right_forearm": um "bico" fino vazava pro fundo
# escuro entre o cotovelo e o tronco (faixa y=0.32-0.38) -- o fechamento da
# silhueta (raio 40) solda esse pedaço de fundo ao braço porque o vão real
# ali é mais estreito que o raio. Confirmado lendo os pixels: no bico a cor
# é tão escura quanto o fundo (gray~28-77, abaixo do limiar de fundo 100)
# mas `corpo_mask` (radius 40) dizia True mesmo assim -- só volta a False a
# partir do raio 35. Baixar o raio global resolveria, mas mexe em TODAS as
# regiões (testado: chest vai de 39154 pra 35176px, hip de 51489 pra
# 49547px, thigh/calf também mudam) -- pra corrigir só aqui sem tocar a
# silhueta compartilhada por todas as outras máscaras, a trava abaixo corta
# só o retângulo do vazamento, direto na máscara final de "right_forearm".
# "left_forearm" não tem essa trava porque não mostrou o mesmo salto de
# escuridão no perfil (a ilustração não é perfeitamente simétrica).
JANELA_NOTCH_LATERAL = {
    "right_forearm": (0.325, 0.32, 0.38),  # (x máximo, y mínimo, y máximo)
}


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


# Raio maior, só para a máscara auxiliar usada ao recortar "waist" (ver
# `corpo_mask_cintura` em `main()`). O flanco do tronco (axila -> lateral
# das costelas) nesta ilustração é sombreado o bastante para cair abaixo do
# limiar `gray<100` mesmo sem estar realmente fora do corpo -- com o raio
# principal (40) essa faixa de pele ficaria fora da silhueta e cortaria
# quase toda a máscara de "waist" (recortada por `corpo_mask` logo abaixo).
# Um raio maior aqui resolve, mas só pode ser usado para ESSE recorte
# específico: aplicado à silhueta principal, ele é o que achatava "hip" num
# bloco de cantos retos (ver o comentário de `RAIO_FECHAMENTO_SILHUETA`).
RAIO_FECHAMENTO_CINTURA = 90

# SEGUNDO BUG (achado depois de renderizar `CorpoInterativoWidget` de
# verdade e comparar visualmente com o corpo -- não só olhando a máscara
# isolada): o raio 90 acima não fecha só o buraco sombreado do flanco --
# nesta ilustração a lacuna de fundo REAL entre o braço pendurado e o tronco
# (a "sombra" visível entre cotovelo/antebraço e a cintura) tem uma largura
# parecida com a do buraco sombreado (testado programaticamente: nenhum raio
# entre 45 e 90 fecha um sem também começar a soldar o outro -- a partir de
# ~r=52 pixels já vazam pra além de x=0.70, que é território do antebraço).
# Sem trava nenhuma, esse raio también transforma um pedaço enorme do espaço
# vazio ao lado do braço em "corpo" -- e como a faixa da cintura
# (`_faixa_lateral_cintura`) segue a borda EXTERNA dessa silhueta linha por
# linha, ela persegue essa borda falsa e sai disparada até quase a mão
# (era exatamente o defeito visível no app: bloco verde enorme cobrindo o
# antebraço). Confirmado comparando pixel a pixel a silhueta com raio 40 vs
# 90 sobre a imagem: a área extra do raio 90 é literalmente um blob no
# formato do vazamento.
#
# CORREÇÃO: `zona_permitida_fechamento` (ver `calcular_silhueta`) restringe
# onde esse raio grande pode adicionar pixels -- só dentro de um retângulo
# pequeno colado em cada flanco (largura suficiente pra cobrir o buraco
# sombreado, com folga até x=0.68/0.32, antes de x=0.70 onde o vazamento
# pro antebraço começa). Fora desses retângulos a silhueta cai de volta na
# versão sem fechamento (`corpo_bruto`), então a lacuna real braço<->tronco
# nunca é soldada.
ZONAS_PERMITIDAS_FECHAMENTO_CINTURA = [
    (0.320, 0.440, 0.270, 0.400),  # flanco direito da pessoa (esquerda na imagem)
    (0.560, 0.680, 0.270, 0.400),  # flanco esquerdo da pessoa (direita na imagem)
]


def calcular_silhueta(
    gray: np.ndarray,
    raio_fechamento: int = RAIO_FECHAMENTO_SILHUETA,
    zona_permitida_fechamento: "list | None" = None,
) -> np.ndarray:
    """`zona_permitida_fechamento`: se informado (lista de retângulos
    fração 0-1 `(x0, x1, y0, y1)`), os pixels que o FECHAMENTO adiciona (que
    `corpo_bruto` sozinho não tinha) só valem DENTRO desses retângulos --
    fora deles a silhueta cai de volta em `corpo_bruto` (sem fechamento
    nenhum). Existe por causa de `RAIO_FECHAMENTO_CINTURA`: ver o comentário
    grande sobre ele em `main()` para o porquê disso ser necessário (raio
    grande o bastante pra fechar o buraco sombreado do flanco também solda,
    sem essa trava, a lacuna de fundo real entre o braço pendurado e o
    tronco -- os dois têm largura parecida nesta ilustração, então não existe
    um único raio que feche um sem soldar o outro; confirmado testando o
    raio de 45 a 90 -- ver histórico do commit). Se `None` (comportamento
    padrão, usado por todas as outras chamadas), o fechamento vale na imagem
    inteira como sempre valeu.
    """
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
    if zona_permitida_fechamento is not None:
        zona_permitida = np.zeros((h, w), dtype=bool)
        for (x0, x1, y0, y1) in zona_permitida_fechamento:
            zona_permitida[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = True
        fechamento_extra = fechamento_extra & zona_permitida

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
    corpo_mask_cintura = calcular_silhueta(
        gray,
        raio_fechamento=RAIO_FECHAMENTO_CINTURA,
        zona_permitida_fechamento=ZONAS_PERMITIDAS_FECHAMENTO_CINTURA,
    )

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
        # "waist" precisa do recorte final com `corpo_mask_cintura` (o mesmo
        # raio maior já usado pra montar `binaria` acima) -- não com
        # `corpo_mask` (raio 40, padrão de todas as outras regiões). Usar o
        # raio padrão aqui era um bug: ele derrubava quase toda a máscara de
        # "waist" de volta a quase nada (o próprio motivo de
        # RAIO_FECHAMENTO_CINTURA existir é esse flanco cair abaixo do
        # limiar de silhueta com o raio padrão -- ver o comentário grande
        # ali) -- só não tinha sido notado porque o polígono antigo, alto
        # demais, passava boa parte do tempo sobre pele não sombreada
        # (braço/ombro) onde o raio 40 ainda basta, mascarando o problema.
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
