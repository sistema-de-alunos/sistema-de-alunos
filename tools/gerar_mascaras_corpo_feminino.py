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
    binary_opening as m_open,
    remove_small_objects,
)
from skimage.draw import disk as draw_disk, polygon as draw_polygon

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


# "waist" também não usa o resultado bruto do watershed aqui -- mesmo motivo
# do masculino (ver o comentário grande em `gerar_mascaras_corpo.py`): nesta
# ilustração o flanco do tronco (axila -> lateral das costelas -> oblíquo)
# é uma superfície lisa, quase sem textura própria que separe esse musculo
# do peitoral/abdômen vizinhos -- sem uma borda de gradiente forte pra
# seguir, o watershed caiu na regra de distância entre sementes e vazou tanto
# pra dentro (sobre chest/abdomen) quanto pra fora (até a axila do braço).
# Contornado a olho, direto sobre `corpomulher.png`: ponta junto à axila,
# descendo pela lateral do tronco, arredondando perto do início do quadril.
# Recortado por `corpo_mask` e pelas regiões vizinhas já decididas pelo MESMO
# `rotulos_ws` (ver `main()`) antes de virar a máscara final -- então mesmo
# que o polígono avance por engano sobre território de outra região, o
# resultado nunca invade uma máscara que já está correta.
#
# Pontos (frações 0-1) de UM lado -- o lado ESQUERDO da IMAGEM (lado DIREITO
# da pessoa). O outro lado é o espelho (x -> 1-x), já que a ilustração de
# frente é simétrica.
POLIGONO_CINTURA_LADO = [
    (0.380, 0.205),  # ponta superior, junto à axila
    (0.400, 0.225),
    (0.415, 0.245),
    (0.420, 0.265),  # lateral da mama/peitoral
    (0.415, 0.285),
    (0.405, 0.305),
    (0.398, 0.325),
    (0.392, 0.345),
    (0.388, 0.362),
    (0.378, 0.375),  # início da curva do fundo (perto do quadril)
    (0.365, 0.380),
    (0.350, 0.378),
    (0.338, 0.372),  # fim da curva do fundo (perto do braço)
    (0.330, 0.355),
    (0.325, 0.330),
    (0.323, 0.305),
    (0.327, 0.280),
    (0.335, 0.255),
    (0.348, 0.232),
    (0.362, 0.215),
]

_VIZINHAS_CINTURA = ("chest", "abdomen", "hip", "right_arm", "left_arm")


def mascara_poligono_cintura(h: int, w: int) -> np.ndarray:
    mascara = np.zeros((h, w), dtype=bool)
    for pontos in (POLIGONO_CINTURA_LADO, [(1 - x, y) for x, y in POLIGONO_CINTURA_LADO]):
        ys = [y * h for _x, y in pontos]
        xs = [x * w for x, _y in pontos]
        rr, cc = draw_polygon(ys, xs, shape=(h, w))
        mascara[rr, cc] = True
    return mascara


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


def calcular_silhueta(gray: np.ndarray, raio_fechamento: int = RAIO_FECHAMENTO_SILHUETA) -> np.ndarray:
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

    return corpo_bruto | (corpo_fechado & ~zona_exclusao)


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
    corpo_mask_cintura = calcular_silhueta(gray, raio_fechamento=RAIO_FECHAMENTO_CINTURA)

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
            binaria = mascara_poligono_cintura(h, w) & corpo_mask_cintura & ~vizinhas
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
        salvar_mascara(
            PASTA_SAIDA / f"{nome}.png", binaria, corpo_mask, h, w,
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
