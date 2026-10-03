
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

RAIO_FECHAMENTO_SILHUETA = 40
SIGMA_BLUR_ELEVACAO = 3.0
COMPACTNESS = 1e-3
COR_VERDE = (46, 204, 113)

SEMENTES = {
    "ignore_face": [(0.50, 0.06)],
    "ignore_neck": [(0.50, 0.155)],
    "shoulder": [(0.335, 0.195), (0.665, 0.195)],
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

ZONAS_EXCLUSAO_FECHAMENTO: list = []

LIMITE_LATERAL = {
    "right_thigh": (0.0, 0.50),
    "left_thigh": (0.50, 1.0),
    "right_calf": (0.0, 0.50),
    "left_calf": (0.50, 1.0),
}

LIMITE_SUPERIOR: dict = {}

JANELA_NOTCH_LATERAL: dict = {}


_VIZINHAS_CINTURA = ("chest", "abdomen", "hip", "right_arm", "left_arm")

_CINTURA_Y0, _CINTURA_Y1 = 0.285, 0.365
_CINTURA_ARCO_TOPO_PX = 14
_CINTURA_TOPO_SUBIDA_PX = 8

_ABDOMEN_X = (0.444, 0.558)
_ABDOMEN_Y1 = 0.415
_ABDOMEN_ARCO_FUNDO_PX = 50

_CINTURA_LARGURA_FAIXA = 0.038

_CINTURA_DILATACAO_EXCLUSAO_BRACO = 3

_EXPANSAO_PX = {"right_arm": 18, "left_arm": 18, "shoulder": 10}
_OMBRO_LINHA_DELTOIDE = (
    ((0.357, 0.223), (0.314, 0.264)),
    ((0.648, 0.225), (0.684, 0.267)),
)
_BRACO_FUNDO_LINHA = {"left_arm": ((0.723, 0.324), (0.660, 0.357))}
_QUADRIL_EXPANSAO_PX = 8
_COXA_FUNDO_Y = 0.654
_COXA_ARCO_FUNDO_PX = 22
_PANTURRILHA_TOPO_Y = 0.686
_PANTURRILHA_ARCO_TOPO_PX = 22
_QUADRIL_TOPO_INCLINACAO_PX = 14
_QUADRIL_FUNDO = (
    ((0.30, 0.417), (0.407, 0.411), (0.497, 0.487)),
    ((0.70, 0.417), (0.586, 0.411), (0.501, 0.487)),
)

_TORAX_RECUO_FUNDO_PX = 3


def _preencher_perna(corpo_real: np.ndarray, y0: int, y1: int, esquerda: bool, bloqueio: np.ndarray) -> np.ndarray:
    h, w = corpo_real.shape
    perna = np.zeros((h, w), dtype=bool)
    for y in range(y0, y1 + 1):
        d = np.diff(np.r_[0, corpo_real[y].astype(np.int8), 0])
        trechos = [
            (a, b) for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0])
            if (a < w // 2 if esquerda else b > w // 2)
        ]
        if trechos:
            a, b = max(trechos, key=lambda t: t[1] - t[0])
            perna[y, a:b] = True
    return perna & ~bloqueio


def _arco_vertical(binaria: np.ndarray, y_lado: int, arco_px: int, fundo: bool) -> np.ndarray:
    h, w = binaria.shape
    xs = np.where(binaria[y_lado])[0]
    u = np.clip((np.arange(w) - (xs.min() + xs.max()) / 2) / ((xs.max() - xs.min()) / 2 + 1), -1, 1)
    linhas = np.arange(h)[:, None]
    if fundo:
        return binaria & (linhas < (y_lado - arco_px * (1 - u**2))[None, :])
    return binaria & (linhas >= (y_lado + arco_px * (1 - u**2))[None, :])


def _faixa_lateral_cintura(h: int, w: int, corpo_mask_cintura: np.ndarray, rotulos_ws: np.ndarray, nome_para_id: dict) -> np.ndarray:
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
    y0, y1 = int(_CINTURA_Y0 * h), int(_CINTURA_Y1 * h) + _QUADRIL_TOPO_INCLINACAO_PX + 1
    centro = w // 2
    abd_esq, abd_dir = int(_ABDOMEN_X[0] * w), int(_ABDOMEN_X[1] * w)
    for y in range(y0, y1):
        linha = tronco_principal[y]
        if not linha[centro]:
            continue
        fora_esq = np.where(~linha[:centro])[0]
        fora_dir = np.where(~linha[centro:])[0]
        esquerda = fora_esq[-1] + 1 if fora_esq.size else 0
        direita = centro + fora_dir[0] if fora_dir.size else w
        faixa[y, esquerda : max(esquerda + largura_px, abd_esq)] = True
        faixa[y, min(direita - largura_px, abd_dir) : direita] = True
    return faixa


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
    corpo_mask_cintura = m_dilate(corpo_mask, morph_disk(RAIO_RECUPERAR_SOMBRA_CINTURA))
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

    vizinhas = np.zeros_like(corpo_mask)
    for vizinha in _VIZINHAS_CINTURA:
        if vizinha not in ("abdomen", "chest", "hip"):
            vizinhas |= rotulos_ws == nome_para_id[vizinha]
    linhas = np.arange(h)[:, None]
    x0a, x1a = int(_ABDOMEN_X[0] * w), int(_ABDOMEN_X[1] * w)
    y_topo = int(_CINTURA_Y1 * h)
    linha_topo = corpo_real[y_topo]
    centro = w // 2
    borda_esq = np.where(~linha_topo[:centro])[0][-1] + 1
    borda_dir = centro + np.where(~linha_topo[centro:])[0][0] - 1
    y_encontro = np.full(w, y_topo)
    for x_fora, x_abd in ((borda_esq, x0a), (borda_dir, x1a)):
        for x in range(min(x_fora, x_abd), max(x_fora, x_abd) + 1):
            y_encontro[x] = int(round(y_topo + _QUADRIL_TOPO_INCLINACAO_PX * (x - x_fora) / (x_abd - x_fora)))
    faixa = _faixa_lateral_cintura(h, w, corpo_mask_cintura, rotulos_ws, nome_para_id)
    mascara_cintura_final = faixa & corpo_mask_cintura & ~vizinhas & (linhas < y_encontro[None, :])
    y0 = int(_CINTURA_Y0 * h)
    for lado in (slice(0, w // 2), slice(w // 2, w)):
        parte = mascara_cintura_final[:, lado]
        if not parte.any():
            continue
        largura_linha = parte.sum(axis=1)
        topo = max(y0, int(np.where(largura_linha >= 0.8 * largura_linha.max())[0].min())) - _CINTURA_TOPO_SUBIDA_PX
        xs_topo = np.where(parte[topo : topo + 20].any(axis=0))[0]
        cx, rx = (xs_topo.min() + xs_topo.max()) / 2, (xs_topo.max() - xs_topo.min()) / 2 + 1
        u = np.clip((np.arange(parte.shape[1]) - cx) / rx, -1, 1)
        corte_col = topo + _CINTURA_ARCO_TOPO_PX * (1 - u**2)
        parte &= ~(linhas < corte_col[None, :])

    mascara_abdomen_final = (
        (rotulos_ws == nome_para_id["abdomen"])
        | ((rotulos_ws == nome_para_id["hip"]) & (linhas < int(_ABDOMEN_Y1 * h)))
    ) & ~mascara_cintura_final
    mascara_abdomen_final[:, : int(_ABDOMEN_X[0] * w)] = False
    mascara_abdomen_final[:, int(_ABDOMEN_X[1] * w) :] = False
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
            binaria = (rotulos_ws == idx) & ~mascara_cintura_final & corpo_real
            abaixo = np.zeros_like(binaria)
            abaixo[:-_TORAX_RECUO_FUNDO_PX] = binaria[_TORAX_RECUO_FUNDO_PX:]
            binaria &= abaixo | m_dilate(mascara_cintura_final, morph_disk(_TORAX_RECUO_FUNDO_PX + 1))
            binaria = m_open(binaria, morph_disk(6))
            vizinho_baixo = mascara_cintura_final | mascara_abdomen_final
            for x in np.where(binaria.any(axis=0))[0]:
                y = np.where(binaria[:, x])[0].max()
                abaixo = vizinho_baixo[y + 1 : y + 26, x]
                if abaixo.any():
                    fim = y + 1 + int(np.argmax(abaixo))
                    binaria[y + 1 : fim, x] = corpo_real[y + 1 : fim, x]
            sobra = (rotulos_ws == idx) & corpo_real & ~binaria & ~vizinho_baixo
            rotulos_sobra, _ = ndimage.label(sobra)
            braco = np.isin(rotulos_ws, [nome_para_id["right_arm"], nome_para_id["left_arm"]]) & corpo_real
            tocam = np.unique(rotulos_sobra[m_dilate(braco, morph_disk(2)) & sobra])
            sobra_torax_braco = np.isin(rotulos_sobra, tocam[tocam > 0])
            binaria |= sobra & ~sobra_torax_braco
        elif nome == "abdomen":
            binaria = mascara_abdomen_final
        elif nome == "hip":
            binaria = (
                ((rotulos_ws == idx) | sobra_para_quadril)
                & ~mascara_cintura_final
                & ~mascara_abdomen_final
                & ~(rotulos_ws == nome_para_id["right_arm"])
                & ~(rotulos_ws == nome_para_id["left_arm"])
                & corpo_real
            )
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
            for x_fora, x_abd in ((borda_esq, x0a), (borda_dir, x1a)):
                colunas = range(min(x_fora, x_abd), max(x_fora, x_abd) + 1)
                for x in colunas:
                    y_reta = y_encontro[x]
                    binaria[:y_reta, x] = False
                    abaixo = np.where(binaria[y_reta:, x])[0]
                    if abaixo.size:
                        faixa = slice(y_reta, y_reta + abaixo[0])
                        binaria[faixa, x] = livre_topo[faixa, x]
            abaixo_fundo = np.zeros((h, w), dtype=bool)
            for pontos, lado in zip(_QUADRIL_FUNDO, (slice(0, w // 2), slice(w // 2, w))):
                xs_f, ys_f = zip(*sorted((px * w, py * h) for px, py in pontos))
                y_col = np.interp(np.arange(w), xs_f, ys_f)
                abaixo_fundo[:, lado] = linhas >= y_col[None, lado]
            quadril_para_coxas = binaria & abaixo_fundo
            binaria &= ~abaixo_fundo
            for y in np.where(binaria.any(axis=1))[0]:
                xs = np.where(binaria[y])[0]
                for x, passo in ((xs[0], -1), (xs[-1], 1)):
                    for _ in range(12):
                        if not corpo_real[y, x + passo] or abaixo_fundo[y, x + passo]:
                            break
                        x += passo
                        binaria[y, x] = True
            ja_expandido |= binaria
        elif nome in ("right_thigh", "left_thigh"):
            y_ini = np.where(((rotulos_ws == idx) | quadril_para_coxas).any(axis=1))[0].min()
            y_lado = int(_COXA_FUNDO_Y * h)
            binaria = _preencher_perna(corpo_real, y_ini, y_lado, nome == "right_thigh", ja_expandido)
            binaria = _arco_vertical(binaria, y_lado, _COXA_ARCO_FUNDO_PX, fundo=True)
        elif nome in ("right_calf", "left_calf"):
            y_lado = int(_PANTURRILHA_TOPO_Y * h)
            y_fim = np.where((rotulos_ws == idx).any(axis=1))[0].max()
            binaria = _preencher_perna(corpo_real, y_lado, y_fim, nome == "right_calf", ja_expandido)
            binaria = _arco_vertical(binaria, y_lado, _PANTURRILHA_ARCO_TOPO_PX, fundo=False)
        elif nome in _EXPANSAO_PX:
            livre = corpo_real & ~np.isin(
                rotulos_ws, [i for n, i in nome_para_id.items() if not n.startswith("ignore") and n != nome]
            )
            if nome in ("right_arm", "left_arm"):
                livre |= sobra_torax_braco
            binaria = m_dilate(rotulos_ws == idx, morph_disk(_EXPANSAO_PX[nome])) & livre & ~ja_expandido
            if nome == "shoulder":
                pode = corpo_real & (livre | np.isin(rotulos_ws, [nome_para_id["right_arm"], nome_para_id["left_arm"]]))
                colunas = np.arange(w)[None, :]
                for (xa, ya), (xb, yb) in _OMBRO_LINHA_DELTOIDE:
                    xa, ya, xb, yb = xa * w, ya * h, xb * w, yb * h
                    x_linha = np.where(linhas < ya, xa, xa + (xb - xa) * (linhas - ya) / (yb - ya))
                    fora = colunas < x_linha if xb < xa else colunas > x_linha
                    lado = (colunas < w // 2) if xb < xa else (colunas >= w // 2)
                    binaria |= fora & lado & (linhas >= int(0.15 * h)) & (linhas <= yb) & pode
            if nome in _BRACO_FUNDO_LINHA:
                (xa, ya), (xb, yb) = _BRACO_FUNDO_LINHA[nome]
                xa, ya, xb, yb = xa * w, ya * h, xb * w, yb * h
                y_linha = ya + (yb - ya) * (np.arange(w) - xa) / (xb - xa)
                antebraco = rotulos_ws == nome_para_id[nome.replace("arm", "forearm")]
                binaria |= antebraco & corpo_real & (linhas < y_linha[None, :])
            ja_expandido |= binaria
        elif nome in ("right_forearm", "left_forearm"):
            binaria = (rotulos_ws == idx) & corpo_real
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
            binaria &= ~ja_expandido
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
        mascara_final = corpo_mask_cintura if nome == "waist" else corpo_mask
        if nome in ("right_forearm", "left_forearm", "hip", "right_thigh", "left_thigh", "right_calf", "left_calf") or nome in _EXPANSAO_PX:
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
