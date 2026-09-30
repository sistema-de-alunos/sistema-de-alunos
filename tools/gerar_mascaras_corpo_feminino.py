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
_CINTURA_Y0, _CINTURA_Y1 = 0.285, 0.365
# Quanto (px) o meio do topo de cada lado da cintura desce (arco invertido).
_CINTURA_ARCO_TOPO_PX = 22

# Abdômen (ver `main()`): faixa de colunas (frações da largura) do reto
# abdominal e até onde (fração da altura) ele desce sobre o quadril -- no
# centro; o fundo é um arco (meia-elipse) que sobe `_ABDOMEN_ARCO_FUNDO_PX`
# até as bordas. Antes era corte reto em 0.44, comendo o quadril.
_ABDOMEN_X = (0.444, 0.558)
_ABDOMEN_Y1 = 0.415
_ABDOMEN_ARCO_FUNDO_PX = 50

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

# Quanto (px) cada região cresce sobre a pele sem dono ao redor (ver `main()`).
_EXPANSAO_PX = {"right_arm": 18, "left_arm": 18, "shoulder": 10}
# Idem para as laterais do quadril (ramo próprio em `main()`).
_QUADRIL_EXPANSAO_PX = 8
# Ponta de baixo das coxas (ver `main()`): quanto sobe e quanto o arco
# arredondado sobe do centro até as laterais.
_COXA_RECUO_FUNDO_PX = 15
_COXA_ARCO_FUNDO_PX = 25
# Quanto (px), no máximo, o lado externo das coxas cresce (do meio pra baixo).
_COXA_EXPANSAO_EXTERNA_PX = 8
# Quanto (px) o topo reto do quadril desce da borda externa até o abdômen.
_QUADRIL_TOPO_INCLINACAO_PX = 14

# Quanto (px) a borda de baixo do tórax sobe (ver `main()`).
_TORAX_RECUO_FUNDO_PX = 3


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
    centro = w // 2
    for y in range(y0, y1):
        # Borda do tronco = o trecho contínuo que passa pelo centro da
        # imagem. Pegar o 1º/último pixel da linha inteira caía no
        # antebraço, que nesta ilustração fica afastado do tronco.
        linha = tronco_principal[y]
        if not linha[centro]:
            continue
        fora_esq = np.where(~linha[:centro])[0]
        fora_dir = np.where(~linha[centro:])[0]
        esquerda = fora_esq[-1] + 1 if fora_esq.size else 0
        direita = centro + fora_dir[0] if fora_dir.size else w
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
    # ...mas nunca além do contorno real (alfa da imagem): a dilatação
    # passava do tronco e a cintura "enganchava" no fundo ao lado.
    corpo_real = np.array(Image.open(IMAGEM).convert("RGBA"))[..., 3] >= 128
    corpo_mask_cintura &= corpo_real

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

    # Calculada antes do loop porque "abdomen" (que vem antes em SEMENTES)
    # também precisa dela: a faixa da cintura NÃO é mais cortada pelo
    # abdômen -- é o abdômen que cede a faixa lateral pra cintura (o
    # abdômen cobria quase todo o flanco e a cintura sobrava como um fio).
    # O mesmo vale pro tórax (também antes em SEMENTES): a borda lateral de
    # baixo dele cede espaço pra cintura subir até `_CINTURA_Y0`.
    vizinhas = np.zeros_like(corpo_mask)
    for vizinha in _VIZINHAS_CINTURA:
        if vizinha not in ("abdomen", "chest"):
            vizinhas |= rotulos_ws == nome_para_id[vizinha]
    faixa = _faixa_lateral_cintura(h, w, corpo_mask_cintura, rotulos_ws, nome_para_id)
    mascara_cintura_final = faixa & corpo_mask_cintura & ~vizinhas
    # Topo em arco invertido: a faixa começa num corte reto em `_CINTURA_Y0`;
    # em cada lado o corte vira um arco (parábola) -- nas bordas fica em Y0 e
    # no meio da faixa desce `_CINTURA_ARCO_TOPO_PX`.
    y0 = int(_CINTURA_Y0 * h)
    linhas = np.arange(h)[:, None]
    for lado in (slice(0, w // 2), slice(w // 2, w)):
        parte = mascara_cintura_final[:, lado]
        if not parte.any():
            continue
        # Topo real deste lado: 1ª linha em que a faixa já tem 80% da
        # largura máxima (perto da axila o braço corta as primeiras linhas
        # e sobram só alguns pixels soltos acima de onde ela começa de fato).
        largura_linha = parte.sum(axis=1)
        topo = max(y0, int(np.where(largura_linha >= 0.8 * largura_linha.max())[0].min()))
        xs_topo = np.where(parte[topo : topo + 20].any(axis=0))[0]
        cx, rx = (xs_topo.min() + xs_topo.max()) / 2, (xs_topo.max() - xs_topo.min()) / 2 + 1
        u = np.clip((np.arange(parte.shape[1]) - cx) / rx, -1, 1)
        # Parábola, não meia-elipse: a elipse é vertical nas pontas e só um
        # fio de 1-2px subia nos cantos (apagado depois em `salvar_mascara`).
        corte_col = topo + _CINTURA_ARCO_TOPO_PX * (1 - u**2)
        parte &= ~(linhas < corte_col[None, :])

    # Abdômen: embaixo ele se espalhava em "asas" laterais sob a cintura.
    # Fica só na faixa de colunas do reto abdominal (`_ABDOMEN_X`) e desce
    # até `_ABDOMEN_Y1`, tomando esse pedaço central do quadril (que depois
    # desconta o abdômen).
    mascara_abdomen_final = (
        (rotulos_ws == nome_para_id["abdomen"])
        | ((rotulos_ws == nome_para_id["hip"]) & (linhas < int(_ABDOMEN_Y1 * h)))
    ) & ~mascara_cintura_final
    mascara_abdomen_final[:, : int(_ABDOMEN_X[0] * w)] = False
    mascara_abdomen_final[:, int(_ABDOMEN_X[1] * w) :] = False
    # Fundo arredondado (ver `_ABDOMEN_ARCO_FUNDO_PX`); o que o arco corta do
    # abdômen, dentro da faixa de colunas, vai pro quadril.
    x0a, x1a = int(_ABDOMEN_X[0] * w), int(_ABDOMEN_X[1] * w)
    u = np.clip((np.arange(w) - (x0a + x1a) / 2) / ((x1a - x0a) / 2), -1, 1)
    fundo_col = _ABDOMEN_Y1 * h - _ABDOMEN_ARCO_FUNDO_PX * (1 - np.sqrt(1 - u**2))
    abaixo_arco = linhas >= fundo_col[None, :]
    abaixo_arco[:, :x0a] = False
    abaixo_arco[:, x1a:] = False
    abaixo_arco[: int(_CINTURA_Y0 * h)] = False
    sobra_para_quadril = abaixo_arco & (rotulos_ws == nome_para_id["abdomen"])
    mascara_abdomen_final &= ~abaixo_arco

    ja_expandido = np.zeros((h, w), dtype=bool)
    for nome in nomes:
        if nome.startswith("ignore"):
            continue
        idx = nome_para_id[nome]
        if nome == "waist":
            binaria = mascara_cintura_final
        elif nome == "chest":
            # Recorta pelo contorno real: o fechamento da silhueta levava os
            # cantos de baixo (sob o peito) sobre o fundo.
            binaria = (rotulos_ws == idx) & ~mascara_cintura_final & corpo_real
            # A borda de baixo descia além da dobra sob o peito (sobre as
            # costelas); sobe `_TORAX_RECUO_FUNDO_PX` em cada coluna.
            abaixo = np.zeros_like(binaria)
            abaixo[:-_TORAX_RECUO_FUNDO_PX] = binaria[_TORAX_RECUO_FUNDO_PX:]
            binaria &= abaixo
            # Tira as pontinhas finas que sobravam embaixo.
            binaria = m_open(binaria, morph_disk(6))
        elif nome == "abdomen":
            binaria = mascara_abdomen_final
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
                ((rotulos_ws == idx) | sobra_para_quadril)
                & ~mascara_cintura_final
                & ~mascara_abdomen_final
                & ~(rotulos_ws == nome_para_id["right_arm"])
                & ~(rotulos_ws == nome_para_id["left_arm"])
                # O fechamento da silhueta criava uma ponta sobre o fundo no
                # canto superior externo; recorta pelo contorno real.
                & corpo_real
            )
            # Laterais: a pele em sombra da borda do quadril ficava de fora;
            # mesmo crescimento de `_EXPANSAO_PX`, só sobre pele sem dono.
            livre = (
                corpo_real
                & ~mascara_cintura_final
                & ~mascara_abdomen_final
                & ~ja_expandido
                & ~np.isin(
                    rotulos_ws, [i for n, i in nome_para_id.items() if not n.startswith("ignore") and n != nome]
                )
            )
            binaria |= m_dilate(binaria, morph_disk(_QUADRIL_EXPANSAO_PX)) & livre
            # Topo reto: entre o fim da cintura e o quadril sobrava uma faixa
            # sem dono e o topo saía cheio de "espinhos". Em cada lado (fora
            # da faixa do abdômen) o topo vira uma reta que começa colada no
            # fim da cintura, na borda externa, e desce
            # `_QUADRIL_TOPO_INCLINACAO_PX` até o abdômen; acima dela sai do
            # quadril, abaixo dela a pele livre entra ("waist"/"abdomen"
            # brutos contam como livres -- as máscaras finais delas, já
            # excluídas acima, não usam essa faixa).
            livre_topo = (
                corpo_real
                & ~mascara_cintura_final
                & ~mascara_abdomen_final
                & ~ja_expandido
                & ~np.isin(
                    rotulos_ws,
                    [i for n, i in nome_para_id.items() if not n.startswith("ignore") and n not in (nome, "waist", "abdomen")],
                )
            )
            y_topo = int(_CINTURA_Y1 * h)
            linha_topo = corpo_real[y_topo]
            centro = w // 2
            borda_esq = np.where(~linha_topo[:centro])[0][-1] + 1
            borda_dir = centro + np.where(~linha_topo[centro:])[0][0] - 1
            for x_fora, x_abd in ((borda_esq, x0a), (borda_dir, x1a)):
                colunas = range(min(x_fora, x_abd), max(x_fora, x_abd) + 1)
                for x in colunas:
                    y_reta = int(round(y_topo + _QUADRIL_TOPO_INCLINACAO_PX * (x - x_fora) / (x_abd - x_fora)))
                    binaria[:y_reta, x] = False
                    abaixo = np.where(binaria[y_reta:, x])[0]
                    if abaixo.size:
                        faixa = slice(y_reta, y_reta + abaixo[0])
                        binaria[faixa, x] = livre_topo[faixa, x]
            ja_expandido |= binaria
        elif nome in ("right_thigh", "left_thigh"):
            binaria = (rotulos_ws == idx) & corpo_real
            # Lado interno: a pele em sombra até a borda real da perna ficava
            # sem dono; em cada linha preenche só na direção do centro.
            livre = corpo_real & ~np.isin(
                rotulos_ws, [i for n, i in nome_para_id.items() if not n.startswith("ignore") and n != nome]
            )
            passo = 1 if nome == "right_thigh" else -1
            for y in np.where(binaria.any(axis=1))[0]:
                xs = np.where(binaria[y])[0]
                x = xs[-1] if passo == 1 else xs[0]
                inicio = x
                while 0 < x < w - 1 and livre[y, x + passo]:
                    x += passo
                binaria[y, min(inicio, x) : max(inicio, x) + 1] = True
            # Lado externo, só do meio pra baixo (a parte de cima encosta no
            # quadril): cresce até `_COXA_EXPANSAO_EXTERNA_PX` sobre pele sem
            # dono, na direção de fora.
            linhas_coxa = np.where(binaria.any(axis=1))[0]
            y_meio = linhas_coxa.min() + int(0.3 * (linhas_coxa.max() - linhas_coxa.min()))
            for y in linhas_coxa[linhas_coxa >= y_meio]:
                xs = np.where(binaria[y])[0]
                x = xs[0] if passo == 1 else xs[-1]
                for _ in range(_COXA_EXPANSAO_EXTERNA_PX):
                    if not (0 < x < w - 1 and livre[y, x - passo]):
                        break
                    x -= passo
                    binaria[y, x] = True
            # Ponta de baixo: sobe `_COXA_RECUO_FUNDO_PX` e vira um arco
            # (meia-elipse) que sobe `_COXA_ARCO_FUNDO_PX` até as laterais.
            y_fim = np.where(binaria.any(axis=1))[0].max() - _COXA_RECUO_FUNDO_PX
            xs = np.where(binaria[y_fim - _COXA_ARCO_FUNDO_PX])[0]
            x0c, x1c = xs.min(), xs.max()
            u = np.clip((np.arange(w) - (x0c + x1c) / 2) / ((x1c - x0c) / 2), -1, 1)
            fundo_col = y_fim - _COXA_ARCO_FUNDO_PX * (1 - np.sqrt(1 - u**2))
            binaria &= linhas < fundo_col[None, :]
        elif nome in _EXPANSAO_PX:
            # As bordas (pele em sombra, sem dono no watershed) ficavam de
            # fora; cresce `_EXPANSAO_PX` só sobre pele que não é de outra
            # região.
            livre = corpo_real & ~np.isin(
                rotulos_ws, [i for n, i in nome_para_id.items() if not n.startswith("ignore") and n != nome]
            )
            # `ja_expandido`: a pele sem dono fica com quem cresceu antes
            # (ombro antes dos braços), sem as duas máscaras se sobreporem.
            binaria = m_dilate(rotulos_ws == idx, morph_disk(_EXPANSAO_PX[nome])) & livre & ~ja_expandido
            ja_expandido |= binaria
        elif nome in ("right_forearm", "left_forearm"):
            # Mesmo caso do quadril: o fechamento da silhueta estendia a
            # ponta inferior sobre o fundo; recorta pelo contorno real.
            binaria = (rotulos_ws == idx) & corpo_real
            # A borda interna de baixo ficava com a semente da mão (o
            # watershed cortava em diagonal). Em cada linha, preenche até as
            # bordas reais do braço -- só a pele contígua, sem tomar outra
            # região.
            livre = corpo_real & ~np.isin(
                rotulos_ws, [i for n, i in nome_para_id.items() if not n.startswith("ignore") and n != nome]
            )
            for y in np.where(binaria.any(axis=1))[0]:
                xs = np.where(binaria[y])[0]
                a, b = xs[0], xs[-1]
                while a > 0 and livre[y, a - 1]:
                    a -= 1
                while b < w - 1 and livre[y, b + 1]:
                    b += 1
                binaria[y, a : b + 1] = livre[y, a : b + 1]
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
        # A borda interna do antebraço é pele em sombra (gray<100), fora de
        # `corpo_mask`; o antebraço já foi recortado por `corpo_real` acima.
        # Coxas: o fechamento da silhueta (raio 40) soldava o vão real entre
        # as pernas logo abaixo da virilha, e as duas coxas se encontravam
        # por cima dele; pelo contorno real cada uma para na própria borda.
        if nome in ("right_forearm", "left_forearm", "hip", "right_thigh", "left_thigh") or nome in _EXPANSAO_PX:
            mascara_final = corpo_real
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
