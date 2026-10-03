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
IMAGEM = RAIZ / "assets" / "corpos" / "corpohomem.png"
PASTA_SAIDA = RAIZ / "assets" / "corpos" / "mascaras_masculino"

RAIO_FECHAMENTO_SILHUETA = 80
SIGMA_BLUR_ELEVACAO = 3.0
COMPACTNESS = 1e-3
COR_VERDE = (46, 204, 113)

SEMENTES = {
    "ignore_face": [(0.50, 0.06)],
    "ignore_neck": [(0.50, 0.155)],
    "shoulder": [(0.315, 0.205), (0.685, 0.205)],
    "chest": [(0.435, 0.245), (0.565, 0.245), (0.50, 0.20)],
    "abdomen": [
        (0.465, 0.315), (0.535, 0.315),
        (0.465, 0.365), (0.535, 0.365),
        (0.465, 0.415), (0.535, 0.415),
    ],
    "waist": [(0.415, 0.345), (0.585, 0.345)],
    "hip": [
        (0.50, 0.43), (0.50, 0.46),
        (0.40, 0.44), (0.60, 0.44),
        (0.37, 0.475), (0.63, 0.475),
    ],
    "right_arm": [(0.29, 0.32), (0.33, 0.37), (0.35, 0.39)],
    "left_arm": [(0.71, 0.32), (0.67, 0.37), (0.65, 0.39)],
    "right_forearm": [(0.235, 0.43), (0.28, 0.38), (0.26, 0.48)],
    "left_forearm": [(0.765, 0.43), (0.72, 0.38), (0.74, 0.48)],
    "ignore_hand_right": [
        (0.19, 0.53), (0.22, 0.45), (0.30, 0.45), (0.35, 0.45),
        (0.30, 0.50), (0.32, 0.51), (0.28, 0.51), (0.33, 0.49),
    ],
    "ignore_hand_left": [
        (0.81, 0.53), (0.78, 0.45), (0.70, 0.45), (0.65, 0.44),
        (0.70, 0.47), (0.72, 0.49), (0.74, 0.50),
        (0.70, 0.51), (0.72, 0.53), (0.68, 0.49), (0.68, 0.52),
    ],
    "right_thigh": [(0.40, 0.50), (0.38, 0.55), (0.41, 0.60), (0.465, 0.455), (0.46, 0.475)],
    "left_thigh": [(0.60, 0.50), (0.62, 0.55), (0.59, 0.60), (0.535, 0.455), (0.54, 0.475)],
    "right_calf": [(0.40, 0.71), (0.40, 0.77), (0.41, 0.82)],
    "left_calf": [(0.60, 0.71), (0.60, 0.77), (0.59, 0.82)],
    "ignore_foot_right": [(0.38, 0.92)],
    "ignore_foot_left": [(0.62, 0.92)],
}

ZONAS_EXCLUSAO_FECHAMENTO = [
    (0.24, 0.37, 0.395, 0.50),
    (0.63, 0.76, 0.395, 0.50),
]

LIMITE_LATERAL: dict = {}

LIMITE_SUPERIOR: dict = {"right_thigh": 0.492, "left_thigh": 0.492}

LIMITE_INFERIOR: dict = {"hip": 0.475}

SUAVIZACAO_CONTORNO = {
    "hip": 6,
}

PONTE_QUADRIL_Y = (0.412, 0.448)
_DOADORAS_PONTE_QUADRIL = ("abdomen", "right_thigh", "left_thigh")
QUADRIL_RECUO_EXTERNO_PX = 4
DESCIDA_QUADRIL_PX = 80
AUMENTO_LATERAL_QUADRIL = [
    ((0.44, 1.0), 8),
    ((0.0, 0.44), 4),
    ((0.39, 0.415), 10),
]
QUADRIL_RECUO_INFERIOR_PX = 1

FAIXA_INTERNA_COXAS_X = (0.44, 0.56)

ABA_EXTERNA_COXA_MAX_PX = {"right_thigh": 3, "left_thigh": 2}

AUMENTO_EXTERNO_COXA = [
    ((0.59, 0.68), 16),
    ((0.45, 0.56), 40),
]

AUMENTO_EXTERNO_BRACO_OMBRO_PX = {"right_arm": 5, "left_arm": 5, "shoulder": 5}
AJUSTE_EXTERNO_BRACO_OMBRO_PX = 8
RECUO_INFERIOR_BRACO_PX = 22
FALHA_INTERNA_BRACO_PX = 10
RECUO_BRACO_CINTURA_PX = {"right_arm": 8}
SUBIDA_CINTURA_DIREITA_PX = 70
FOLGA_SUBIDA_CINTURA_PX = 1
DESCIDA_CINTURA_PX = 40

ALONGAMENTO_ANTEBRACO_PX = 42
ALONGAMENTO_ANTEBRACO_Y0 = 0.42
BORDA_INTERNA_ANTEBRACO_PX = 12
PREENCHIMENTO_EXTERNO_ANTEBRACO_PX = 30

RECUO_TOPO_PANTURRILHA_PX = 85
AUMENTO_LATERAL_PANTURRILHA_PX = 8
AUMENTO_INTERNO_PANTURRILHA_PX = 16
ARREDONDAMENTO_TOPO_PANTURRILHA_PX = 30

ALONGAMENTO_COXA_PX = 20
ARCO_JOELHO_COXA_PX = 30
RECUO_COXA_QUADRIL_PX = 8
ARCO_TOPO_COXA_PX = 20
RECUO_TOPO_INTERNO_COXA_PX = {"right_thigh": 80, "left_thigh": 110}
FOLGA_ENTRE_COXAS_PX = 10


def _suavizar_contorno(binaria: np.ndarray, raio: int, tamanho_minimo: int = 1000) -> np.ndarray:
    suavizada = m_open(binaria, morph_disk(raio))
    suavizada = remove_small_objects(suavizada, min_size=tamanho_minimo)
    return m_close(suavizada, morph_disk(raio))


POLIGONO_CINTURA_LADO = [
    (0.360, 0.268),
    (0.392, 0.275),
    (0.416, 0.284),
    (0.424, 0.306),
    (0.431, 0.317),
    (0.427, 0.332),
    (0.419, 0.346),
    (0.411, 0.370),
    (0.403, 0.392),
    (0.396, 0.402),
    (0.385, 0.407),
    (0.374, 0.408),
    (0.363, 0.405),
    (0.352, 0.397),
    (0.390, 0.377),
    (0.388, 0.353),
    (0.373, 0.332),
    (0.364, 0.318),
    (0.362, 0.303),
    (0.364, 0.278),
]

RECUO_ESPELHO_TOPO_EXTERNO = 0.004
RECUO_ESPELHO_EXTERNO = 0.010
AVANCO_ESPELHO_TOPO = 0.012

_VIZINHAS_CINTURA = ("chest", "abdomen", "hip", "right_arm", "left_arm")


def mascara_poligono_cintura(h: int, w: int) -> np.ndarray:
    mascara = np.zeros((h, w), dtype=bool)
    n = len(POLIGONO_CINTURA_LADO)
    espelho = [
        (
            1 - x
            - (RECUO_ESPELHO_TOPO_EXTERNO if i >= n - 4 else 0)
            - (RECUO_ESPELHO_EXTERNO if i >= n - 7 else 0)
            + (AVANCO_ESPELHO_TOPO if i >= n - 3 else 0),
            y,
        )
        for i, (x, y) in enumerate(POLIGONO_CINTURA_LADO)
    ]
    for pontos in (POLIGONO_CINTURA_LADO, espelho):
        ys = [y * h for _x, y in pontos]
        xs = [x * w for x, _y in pontos]
        rr, cc = draw_polygon(ys, xs, shape=(h, w))
        mascara[rr, cc] = True
    return mascara


def calcular_silhueta(gray: np.ndarray) -> np.ndarray:
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

    corpo_fechado = m_close(corpo_bruto, morph_disk(RAIO_FECHAMENTO_SILHUETA))

    zona_exclusao = np.zeros((h, w), dtype=bool)
    for (x0, x1, y0, y1) in ZONAS_EXCLUSAO_FECHAMENTO:
        zona_exclusao[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = True

    return corpo_bruto | (corpo_fechado & ~zona_exclusao)


FECHAMENTO_EXTRA = {
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

    fundo_real = np.array(Image.open(IMAGEM).convert("RGBA"))[..., 3] < 128
    dist_ao_corpo = ndimage.distance_transform_edt(fundo_real)
    dist_ao_fundo = ndimage.distance_transform_edt(~fundo_real)
    fundo_entre_pernas = fundo_real.copy()
    fundo_entre_pernas[:, : int(FAIXA_INTERNA_COXAS_X[0] * w)] = False
    fundo_entre_pernas[:, int(FAIXA_INTERNA_COXAS_X[1] * w) :] = False

    ponte_quadril = np.isin(rotulos_ws, [nome_para_id[n] for n in _DOADORAS_PONTE_QUADRIL])
    ponte_quadril[: int(PONTE_QUADRIL_Y[0] * h)] = False
    ponte_quadril[int(PONTE_QUADRIL_Y[1] * h) :] = False

    mascaras_finais: dict = {}
    for nome in nomes:
        if nome.startswith("ignore"):
            continue
        idx = nome_para_id[nome]
        if nome == "waist":
            vizinhas = np.zeros_like(corpo_mask)
            for vizinha in _VIZINHAS_CINTURA:
                vizinhas |= rotulos_ws == nome_para_id[vizinha]
            binaria = mascara_poligono_cintura(h, w) & corpo_mask & ~vizinhas
        else:
            binaria = rotulos_ws == idx
        if nome == "hip":
            binaria = (binaria | ponte_quadril) & (dist_ao_fundo > QUADRIL_RECUO_EXTERNO_PX)
        elif nome in _DOADORAS_PONTE_QUADRIL:
            binaria = binaria & ~ponte_quadril
        if nome in ("right_arm", "left_arm"):
            binaria = binaria & ~fundo_real
            rotulos_braco, n_pedacos = ndimage.label(binaria)
            if n_pedacos > 1:
                tamanhos = ndimage.sum(binaria, rotulos_braco, range(1, n_pedacos + 1))
                binaria = rotulos_braco == int(np.argmax(tamanhos)) + 1
            outras = np.isin(rotulos_ws, [
                nome_para_id[n] for n in nomes
                if n not in (nome, "waist") and not n.startswith("ignore")
            ]) | mascaras_finais["waist"]
            fechado = m_close(binaria, morph_disk(FALHA_INTERNA_BRACO_PX))
            binaria = binaria | (fechado & ~fundo_real & ~outras)
            if RECUO_BRACO_CINTURA_PX.get(nome):
                perto_cintura = ndimage.binary_dilation(
                    mascaras_finais["waist"] | mascaras_finais["chest"], morph_disk(RECUO_BRACO_CINTURA_PX[nome])
                )
                binaria = binaria & ~perto_cintura
            antebraco = rotulos_ws == nome_para_id[nome.replace("arm", "forearm")]
            cols = np.where(antebraco.any(axis=0))[0]
            topo = antebraco[:, cols].argmax(axis=0)
            x = np.arange(w)
            corte_col = np.interp(x, cols, topo, left=topo.min(), right=topo.min()) - RECUO_INFERIOR_BRACO_PX
            cx = np.where(binaria.any(axis=0))[0].mean()
            interno = (x > cx) if cx < w // 2 else (x < cx)
            nivel = np.median(topo[-30:] if cx < w // 2 else topo[:30])
            corte_col[interno] = np.minimum(np.interp(x, cols, topo), nivel)[interno]
            binaria = binaria & (np.arange(h)[:, None] < corte_col[None, :])
        if nome in ("right_forearm", "left_forearm"):
            rotulos_ab, n_pedacos = ndimage.label(binaria)
            if n_pedacos > 1:
                tamanhos = ndimage.sum(binaria, rotulos_ab, range(1, n_pedacos + 1))
                binaria = rotulos_ab == int(np.argmax(tamanhos)) + 1
            livre = ~fundo_real & ~np.isin(rotulos_ws, [nome_para_id[n] for n in nomes if n != nome and not n.startswith("ignore")])
            livre[: int(ALONGAMENTO_ANTEBRACO_Y0 * h)] = False
            binaria = ndimage.binary_dilation(
                binaria, iterations=ALONGAMENTO_ANTEBRACO_PX, mask=livre | binaria
            )
            livre[np.where(binaria.any(axis=1))[0].max() + 1 :] = False
            binaria = ndimage.binary_dilation(
                binaria, iterations=ALONGAMENTO_ANTEBRACO_PX, mask=livre | binaria
            )
            bloqueadas = np.isin(rotulos_ws, [
                nome_para_id[n] for n in nomes
                if n != nome and not n.startswith("ignore") and n not in mascaras_finais
            ])
            for n, m in mascaras_finais.items():
                bloqueadas |= m
            cx = int(np.where(binaria.any(axis=0))[0].mean())
            lado_tronco = np.zeros_like(binaria)
            if cx < w // 2:
                lado_tronco[:, cx:] = True
            else:
                lado_tronco[:, :cx] = True
            extra = ndimage.binary_dilation(binaria, morph_disk(BORDA_INTERNA_ANTEBRACO_PX))
            binaria = binaria | (extra & lado_tronco & ~fundo_real & ~bloqueadas)
            livre_ext = ~fundo_real & ~bloqueadas
            livre_ext[np.where(binaria.any(axis=1))[0].max() + 1 :] = False
            binaria = ndimage.binary_dilation(
                binaria, iterations=PREENCHIMENTO_EXTERNO_ANTEBRACO_PX, mask=livre_ext | binaria
            )
            binaria = ndimage.binary_fill_holes(binaria)
        if nome in ("right_calf", "left_calf"):
            binaria = binaria & ~fundo_real
            rotulos_pant, n_pedacos = ndimage.label(binaria)
            if n_pedacos > 1:
                tamanhos = ndimage.sum(binaria, rotulos_pant, range(1, n_pedacos + 1))
                binaria = rotulos_pant == int(np.argmax(tamanhos)) + 1
            topo = np.where(binaria.any(axis=1))[0].min()
            corte = topo + RECUO_TOPO_PANTURRILHA_PX
            xs_topo = np.where(binaria[corte : corte + 40].any(axis=0))[0]
            cx, rx = (xs_topo.min() + xs_topo.max()) / 2, (xs_topo.max() - xs_topo.min()) / 2 + 1
            u = np.clip((np.arange(w) - cx) / rx, -1, 1)
            corte_col = corte + ARREDONDAMENTO_TOPO_PANTURRILHA_PX * np.sqrt(1 - u**2)
            acima_do_oval = np.arange(h)[:, None] < corte_col[None, :]
            binaria = binaria & ~acima_do_oval
            extra = ndimage.binary_dilation(binaria, morph_disk(AUMENTO_LATERAL_PANTURRILHA_PX))
            extra &= ~acima_do_oval
            outras = np.isin(rotulos_ws, [nome_para_id[n] for n in nomes if n != nome and not n.startswith("ignore")])
            binaria = binaria | (extra & ~fundo_real & ~outras)
            extra = ndimage.binary_dilation(binaria, morph_disk(AUMENTO_INTERNO_PANTURRILHA_PX))
            extra &= ~acima_do_oval
            extra[np.where(binaria.any(axis=1))[0].max() + 1 :] = False
            if cx < w // 2:
                extra[:, : int(cx)] = False
            else:
                extra[:, int(cx) :] = False
            binaria = binaria | (extra & ~fundo_real & ~outras)
        if nome in AUMENTO_EXTERNO_BRACO_OMBRO_PX:
            extra = ndimage.binary_dilation(binaria, morph_disk(AUMENTO_EXTERNO_BRACO_OMBRO_PX[nome]))
            binaria = binaria | (extra & (rotulos_ws == 0) & ~fundo_real)
        if nome in ("right_thigh", "left_thigh"):
            binaria = binaria & ~fundo_entre_pernas
            aba = dist_ao_corpo > ABA_EXTERNA_COXA_MAX_PX[nome]
            aba[:, int(FAIXA_INTERNA_COXAS_X[0] * w) : int(FAIXA_INTERNA_COXAS_X[1] * w)] = False
            binaria = binaria & ~aba
            outras = np.isin(rotulos_ws, [nome_para_id[n] for n in nomes if n != nome and not n.startswith("ignore")])
            base = binaria
            for (y0f, y1f), raio in AUMENTO_EXTERNO_COXA:
                extra = ndimage.binary_dilation(base, morph_disk(raio))
                extra[: int(y0f * h)] = False
                extra[int(y1f * h) :] = False
                extra[:, int(FAIXA_INTERNA_COXAS_X[0] * w) : int(FAIXA_INTERNA_COXAS_X[1] * w)] = False
                binaria = binaria | (extra & ~fundo_real & ~outras)
            fundo_coxa = np.where(binaria.any(axis=1))[0].max()
            limite = fundo_coxa + ALONGAMENTO_COXA_PX
            outras_sem_pant = outras & ~np.isin(rotulos_ws, [nome_para_id["right_calf"], nome_para_id["left_calf"]])
            livre = ~fundo_real & ~outras_sem_pant
            livre[: fundo_coxa - 2 * ALONGAMENTO_COXA_PX] = False
            livre[limite + 1 :] = False
            binaria = ndimage.binary_dilation(binaria, iterations=ALONGAMENTO_COXA_PX, mask=livre | binaria)
            binaria = ndimage.binary_dilation(binaria, iterations=ALONGAMENTO_COXA_PX, mask=livre | binaria)
            xs_ponta = np.where(binaria[limite - 40 : limite + 1].any(axis=0))[0]
            cx, rx = (xs_ponta.min() + xs_ponta.max()) / 2, (xs_ponta.max() - xs_ponta.min()) / 2 + 1
            u = np.clip((np.arange(w) - cx) / rx, -1, 1)
            corte_col = limite - ARCO_JOELHO_COXA_PX * np.sqrt(1 - u**2)
            binaria = binaria & ~(np.arange(h)[:, None] > corte_col[None, :])
            binaria = binaria & ~ndimage.binary_dilation(
                mascaras_finais["hip"], morph_disk(RECUO_COXA_QUADRIL_PX)
            )
            ocupado_coxa = np.isin(rotulos_ws, [
                nome_para_id[n] for n in nomes
                if n != nome and not n.startswith("ignore") and n not in mascaras_finais
            ])
            for m in mascaras_finais.values():
                ocupado_coxa |= m
            livre_topo = ~fundo_real & ~ocupado_coxa
            livre_topo[: int(LIMITE_SUPERIOR.get(nome, 0) * h)] = False
            livre_topo[int(0.56 * h) :] = False
            binaria = ndimage.binary_dilation(binaria, iterations=40, mask=livre_topo | binaria)
            binaria[:, w // 2 - FOLGA_ENTRE_COXAS_PX : w // 2 + FOLGA_ENTRE_COXAS_PX] = False
            topo_coxa = int(LIMITE_SUPERIOR.get(nome, 0) * h)
            xs_topo = np.where(binaria[topo_coxa : topo_coxa + 40].any(axis=0))[0]
            cx, rx = (xs_topo.min() + xs_topo.max()) / 2, (xs_topo.max() - xs_topo.min()) / 2 + 1
            u = np.clip((np.arange(w) - cx) / rx, -1, 1)
            corte_col = topo_coxa + ARCO_TOPO_COXA_PX * (1 - np.sqrt(1 - u**2))
            interno = u > 0 if cx < w // 2 else u < 0
            corte_col[interno] += RECUO_TOPO_INTERNO_COXA_PX[nome] * np.abs(u[interno]) ** 2
            binaria = binaria & (np.arange(h)[:, None] >= corte_col[None, :])
            rotulos_coxa, n_pedacos = ndimage.label(binaria)
            if n_pedacos > 1:
                tamanhos = ndimage.sum(binaria, rotulos_coxa, range(1, n_pedacos + 1))
                binaria = rotulos_coxa == int(np.argmax(tamanhos)) + 1
            livre_interno = ~fundo_real & ~ocupado_coxa
            livre_interno[: np.where(fundo_entre_pernas.any(axis=1))[0].min()] = False
            livre_interno[int(0.60 * h) :] = False
            if nome == "right_thigh":
                livre_interno[:, : int(FAIXA_INTERNA_COXAS_X[0] * w)] = False
                livre_interno[:, w // 2 :] = False
            else:
                livre_interno[:, : w // 2] = False
                livre_interno[:, int(FAIXA_INTERNA_COXAS_X[1] * w) :] = False
            binaria = ndimage.binary_dilation(
                binaria, iterations=FOLGA_ENTRE_COXAS_PX, mask=livre_interno | binaria
            )
        if nome in LIMITE_LATERAL:
            x0f, x1f = LIMITE_LATERAL[nome]
            binaria = binaria.copy()
            binaria[:, : int(x0f * w)] = False
            binaria[:, int(x1f * w) :] = False
        if nome in LIMITE_SUPERIOR:
            binaria = binaria.copy()
            binaria[: int(LIMITE_SUPERIOR[nome] * h), :] = False
        if nome in LIMITE_INFERIOR:
            binaria = binaria.copy()
            binaria[int(LIMITE_INFERIOR[nome] * h) :, :] = False
        if nome in SUAVIZACAO_CONTORNO:
            binaria = _suavizar_contorno(binaria, SUAVIZACAO_CONTORNO[nome])
        mascaras_finais[nome] = binaria
        salvar_mascara(
            PASTA_SAIDA / f"{nome}.png", binaria,
            corpo_mask | ~fundo_real
            if nome in (
                "right_thigh", "left_thigh", "right_forearm", "left_forearm",
                "right_calf", "left_calf", *AUMENTO_EXTERNO_BRACO_OMBRO_PX,
            )
            else corpo_mask,
            h, w,
            raio_fechamento=FECHAMENTO_EXTRA.get(nome, 4),
        )
        print(f"{nome}: {binaria.sum()} px -> {PASTA_SAIDA / f'{nome}.png'}")

    quadril = mascaras_finais["hip"]
    outras_finais = np.zeros_like(quadril)
    for n, m in mascaras_finais.items():
        if n != "hip":
            outras_finais |= m
    livre_quadril = (dist_ao_fundo > QUADRIL_RECUO_EXTERNO_PX) & ~outras_finais
    livre_quadril[: np.where(quadril.any(axis=1))[0].max() - 5] = False
    quadril = ndimage.binary_dilation(
        quadril, iterations=DESCIDA_QUADRIL_PX, mask=livre_quadril | quadril
    )
    quadril = quadril | (ndimage.binary_fill_holes(quadril) & ~outras_finais & ~fundo_real)
    base_quadril = quadril
    for (y0_lat, y1_lat), raio_lat in AUMENTO_LATERAL_QUADRIL:
        extra = ndimage.binary_dilation(base_quadril, morph_disk(raio_lat))
        extra[: int(y0_lat * h)] = False
        extra[int(y1_lat * h) :] = False
        extra[:, int(FAIXA_INTERNA_COXAS_X[0] * w) : int(FAIXA_INTERNA_COXAS_X[1] * w)] = False
        quadril = quadril | (extra & (dist_ao_fundo > QUADRIL_RECUO_INFERIOR_PX) & ~outras_finais)
    mascaras_finais["hip"] = quadril
    salvar_mascara(PASTA_SAIDA / "hip.png", quadril, corpo_mask | ~fundo_real, h, w, raio_fechamento=4)

    cintura = mascaras_finais["waist"]
    ocupado = np.zeros_like(cintura)
    for n, m in mascaras_finais.items():
        if n != "waist":
            ocupado |= m
    livre = ~fundo_real & ~ndimage.binary_dilation(ocupado, iterations=FOLGA_SUBIDA_CINTURA_PX)
    livre[:, int(np.where(cintura[:, : w // 2].any(axis=0))[0].mean()) :] = False
    livre[: np.where(cintura[:, : w // 2].any(axis=1))[0].min() - SUBIDA_CINTURA_DIREITA_PX] = False
    cintura = ndimage.binary_dilation(
        cintura, iterations=SUBIDA_CINTURA_DIREITA_PX, mask=livre | cintura
    )
    colado = mascaras_finais["abdomen"] | mascaras_finais["hip"]
    livre_baixo = ~fundo_real & ~colado & ~ndimage.binary_dilation(ocupado & ~colado, iterations=3)
    for lado in (slice(0, w // 2), slice(w // 2, w)):
        livre_lado = np.zeros_like(livre_baixo)
        livre_lado[:, lado] = livre_baixo[:, lado]
        livre_lado[: np.where(cintura[:, lado].any(axis=1))[0].min()] = False
        cintura = ndimage.binary_dilation(
            cintura, iterations=DESCIDA_CINTURA_PX, mask=livre_lado | cintura
        )
    cintura = cintura | (m_close(cintura, morph_disk(8)) & livre_baixo)
    cintura = ndimage.binary_fill_holes(cintura)
    limite = corpo_mask | ~fundo_real
    limite[:, w // 2 :] = ~fundo_real[:, w // 2 :]
    cintura = cintura & limite
    salvar_mascara(
        PASTA_SAIDA / "waist.png", cintura, limite, h, w,
        raio_fechamento=FECHAMENTO_EXTRA.get("waist", 4),
    )
    mascaras_finais["waist"] = cintura

    for nome in AUMENTO_EXTERNO_BRACO_OMBRO_PX:
        mascara = mascaras_finais[nome]
        ocupado = np.zeros_like(mascara)
        for n, m in mascaras_finais.items():
            if n != nome:
                ocupado |= m
        livre = ~fundo_real & ~ocupado & (dist_ao_fundo <= AJUSTE_EXTERNO_BRACO_OMBRO_PX)
        for lado in (slice(0, w // 2), slice(w // 2, w)):
            cols = np.where(mascara[:, lado].any(axis=0))[0]
            if not len(cols):
                continue
            cx = lado.start + int(cols.mean())
            if lado.start == 0:
                livre[:, cx : w // 2] = False
            else:
                livre[:, w // 2 : cx] = False
        mascara = ndimage.binary_dilation(
            mascara, iterations=AJUSTE_EXTERNO_BRACO_OMBRO_PX, mask=livre | mascara
        )
        mascaras_finais[nome] = mascara
        salvar_mascara(PASTA_SAIDA / f"{nome}.png", mascara, corpo_mask | ~fundo_real, h, w)

    import colorsys

    debug = (arr * 0.35).astype(np.uint8)
    for i, nome in enumerate(n for n in nomes if not n.startswith("ignore")):
        idx = nome_para_id[nome]
        hue = (i * 0.61803398875) % 1.0
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.85, 1.0)]
        debug[rotulos_ws == idx] = [r, g, b]
    Image.fromarray(debug).save(PASTA_SAIDA.parent / "watershed_debug.png")
    print("depuração salva em", PASTA_SAIDA.parent / "watershed_debug.png")


if __name__ == "__main__":
    main()
