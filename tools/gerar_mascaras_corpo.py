"""Gera as máscaras de região usadas por `gui/widgets/corpo_interativo.py`.

FERRAMENTA DE DESENVOLVIMENTO -- não é executada pelo app, e as bibliotecas
que ela usa (numpy/scipy/scikit-image/Pillow) NÃO são dependência do app em
runtime, só deste script. Rode isto de novo apenas se:

  - a imagem `assets/corpos/corpohomem.png` for substituída/recalibrada; ou
  - um novo corpo (ex.: feminino) for adicionado -- nesse caso duplique
    `SEMENTES`/`IMAGEM`/`PASTA_SAIDA` para a nova imagem, com sementes
    recalibradas visualmente sobre ela (ver seção "Como recalibrar" abaixo).

O QUE ISSO FAZ
---------------
As regiões do boneco (ombro, tórax, coxa...) precisam de uma máscara que
siga o contorno real do músculo na ilustração -- não um polígono aproximado.
Como a imagem não tem camadas por músculo, cada região é obtida por
segmentação watershed: a partir de um ponto semente dentro do músculo, a
"água sobe" e para nas bordas de maior gradiente (os traços que o próprio
ilustrador desenhou separando um músculo do outro -- sulco deltopeitoral,
sulcos do abdômen, prega inguinal, dobra do joelho etc.), então o contorno
final acompanha a anatomia de verdade em vez de ser "chutado" à mão.

Etapas:
  1. Silhueta do corpo: flood fill do fundo (que é um degradê radial escuro)
     a partir das bordas da imagem. Sozinho, isso classifica erroneamente
     como "fundo" partes do corpo que estão em sombra (lateral do tronco,
     face interna do braço), por terem brilho parecido com o degradê --
     então um fechamento morfológico de raio grande preenche essas
     reentrâncias. Só que esse mesmo fechamento, sendo cego ao que está de
     cada lado, também soldava indevidamente o braço pendurado ao quadril
     (um vão real, não sombra) em duas faixas específicas; `ZONAS_EXCLUSAO`
     restaura a silhueta original SÓ nelas -- ver `body_silhouette()`.
  2. Elevação = gradiente (Sobel) de uma versão borrada da imagem em tons de
     cinza -- o borramento apaga a textura fina das fibras musculares (ruído
     de alta frequência) mas preserva os sulcos/dobras reais.
  3. Marcadores: um disco pequeno em cada ponto de `SEMENTES`, com o mesmo id
     para sementes do mesmo nome (regiões com mais de uma parte, ex.: duas
     sementes para os dois lóbulos do peitoral em "chest"). Nomes que
     começam com "ignore_" são sorvedouros (rosto, pescoço, mãos, pés, o
     antebraço esquerdo que não tem linha na tabela) -- existem só para
     impedir que essas áreas sejam anexadas às regiões vizinhas nomeadas.
  4. `skimage.segmentation.watershed` restrito à silhueta (`mask=corpo_mask`).
  5. Por região: fecha buracos pequenos, remove manchas espúrias, suaviza a
     borda (blur do alfa binário) para anti-aliasing, reforça um anel mais
     opaco perto do contorno (efeito parecido com o "pen" de contorno da
     versão antiga em polígono) -- e por fim RECORTA esse alfa pela silhueta
     de novo (`alfa *= corpo_mask`). Esse recorte final é a camada de
     segurança: o watershed já é restrito à silhueta, mas o blur do passo
     anterior por si só reintroduziria alguns pixels de alfa passando do
     contorno verdadeiro para o fundo (foi a causa raiz do vazamento
     encontrado em revisão -- o blur normaliza pelo próprio máximo e nunca
     era re-recortado). Salva como PNG RGBA do MESMO tamanho da imagem base
     -- pixel (x, y) da máscara corresponde exatamente ao pixel (x, y) da
     imagem original, então o app não precisa remapear nada: só desenha a
     máscara em cima com opacidade reduzida.

COMO RECALIBRAR AS SEMENTES
-----------------------------
Se uma região sair errada (vazando pra vizinha, ou pequena/vazia demais):
  1. Rode este script; abra `<PASTA_SAIDA>/../watershed_debug.png` -- cada
     região aparece com uma cor diferente sobre o corpo escurecido.
  2. Ajuste a(s) coordenada(s) da região problemática em `SEMENTES` (frações
     0-1 da largura/altura da imagem) e rode de novo. Adicionar mais um
     ponto (mesmo nome) numa área que a região deveria cobrir mas não está
     alcançando costuma resolver mais rápido que mover o ponto existente.
  3. Se uma região vazar por um caminho de gradiente fraco muito longe da
     semente, aumente levemente `COMPACTNESS` (ele penaliza caminhos
     compridos); se regiões pequenas ficarem espremidas demais pelas
     vizinhas, diminua.
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
from skimage.draw import disk as draw_disk

RAIZ = Path(__file__).resolve().parent.parent
IMAGEM = RAIZ / "assets" / "corpos" / "corpohomem.png"
PASTA_SAIDA = RAIZ / "assets" / "corpos" / "mascaras_masculino"

RAIO_FECHAMENTO_SILHUETA = 80
SIGMA_BLUR_ELEVACAO = 3.0
COMPACTNESS = 4e-4
COR_VERDE = (46, 204, 113)  # Cores.SUCESSO (core/theme.py)

# Sementes (frações 0-1 de largura/altura) calibradas visualmente sobre
# corpohomem.png (1024x1536, figura de frente). Convenção anatômica:
# "right_*"/"left_*" são o lado DIREITO/ESQUERDO da PESSOA -- que aparecem
# invertidos (esquerda/direita) para quem olha a imagem de frente.
SEMENTES = {
    "ignore_face": [(0.50, 0.06)],
    "ignore_neck": [(0.50, 0.155)],
    "shoulder": [(0.315, 0.205), (0.685, 0.205)],
    # Terceira semente no esterno (bem acima do início real do peitoral):
    # sem ela, "abdomen" conseguia subir pelo sulco claro entre os dois
    # lóbulos do peitoral (baixo gradiente ali) até quase o pescoço.
    "chest": [(0.435, 0.245), (0.565, 0.245), (0.50, 0.20)],
    # Uma semente por bloco do "tanquinho" (3 linhas x esquerda/direita) em
    # vez de só a linha central -- com só o centro, o bloco superior
    # esquerdo ficava sem nenhuma semente por perto e ia parar em "waist"
    # ou "chest".
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
    # (só 1 semente cada -- a segunda usada numa rodada anterior, mais alta
    # e voltada pro tronco, caía numa sombra que nem o fechamento da
    # silhueta alcança; o braço já fica bem coberto com uma só.)
    "right_arm": [(0.29, 0.32)],
    "left_arm": [(0.71, 0.32)],
    # Vários pontos ao longo do antebraço/mão (cotovelo -> dedos), não só
    # um: perto do quadril esse braço pendurado cai dentro da zona de
    # exclusão do fechamento da silhueta (ver ZONAS_EXCLUSAO_FECHAMENTO), e
    # sem o fechamento ali o contorno bruto fragmenta essa faixa em pedaços
    # -- um pedaço sem nenhuma semente por perto ficava pra "hip" (o vazio
    # virava um degrau reto, a própria borda da zona de exclusão).
    "right_forearm": [(0.235, 0.43), (0.28, 0.38), (0.26, 0.48)],
    "ignore_forearm_left": [(0.765, 0.43), (0.72, 0.38), (0.74, 0.48)],
    "ignore_hand_right": [(0.19, 0.53), (0.22, 0.45), (0.30, 0.45), (0.35, 0.45)],
    "ignore_hand_left": [(0.81, 0.53), (0.78, 0.45), (0.70, 0.45), (0.65, 0.44)],
    "right_thigh": [(0.40, 0.50), (0.38, 0.55), (0.41, 0.60)],
    "left_thigh": [(0.60, 0.50), (0.62, 0.55), (0.59, 0.60)],
    "right_calf": [(0.40, 0.71), (0.40, 0.77), (0.41, 0.82)],
    "left_calf": [(0.60, 0.71), (0.60, 0.77), (0.59, 0.82)],
    "ignore_foot_right": [(0.38, 0.92)],
    "ignore_foot_left": [(0.62, 0.92)],
}

# Faixas (fração da imagem) onde o fechamento morfológico da silhueta solda
# indevidamente a mão/antebraço pendurado ao quadril -- um vão real entre
# duas partes do corpo, não uma sombra sobre uma única superfície. Nessas
# faixas a silhueta final volta a usar o resultado bruto do flood fill (sem
# o fechamento), restaurando o vão; fora delas o fechamento continua valendo
# normalmente. Calibradas verificando que nenhuma semente de músculo cai
# fora da silhueta final e que pontos conhecidos dentro desses vãos (entre a
# mão e o quadril, dos dois lados) continuam fora dela.
ZONAS_EXCLUSAO_FECHAMENTO = [
    (0.24, 0.37, 0.395, 0.50),
    (0.63, 0.76, 0.395, 0.50),
]

# Trava lateral extra (fração x mín, máx) só pra "hip": mesmo com as
# sementes de antebraço/mão mais densas, um fragmento fino e reto de
# antebraço dentro de ZONAS_EXCLUSAO_FECHAMENTO (onde a silhueta volta a
# ser o contorno bruto, sem o fechamento) ainda ficava sem nenhuma semente
# por perto e "hip" o herdava -- visível como um degrau reto na borda
# lateral. "hip" não tem por que se estender além disso de qualquer forma
# (é a região mais central do tronco/virilha), então é um cinto de
# segurança geométrico direto em vez de perseguir mais sementes.
LIMITE_LATERAL = {
    "hip": (0.39, 0.61),
}


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

    # Dentro da zona de exclusão, descarta o que só o fechamento adicionou
    # (restaura o vão real); fora dela, mantém o fechamento (conserta a
    # sombra). NÃO passa por binary_fill_holes de novo depois disso -- um
    # buraco perfeitamente cercado pelo fechamento reencheria exatamente a
    # zona que acabamos de restaurar.
    return corpo_bruto | (corpo_fechado & ~zona_exclusao)


def salvar_mascara(caminho: Path, binaria: np.ndarray, corpo_mask: np.ndarray, h: int, w: int) -> None:
    # Fecha falhas pequenas (gaps entre blocos vizinhos do mesmo músculo,
    # ex.: as junções finas entre os blocos do abdômen) antes de remover
    # manchas espúrias -- na ordem inversa, a abertura chegava a fragmentar
    # ligações finas legítimas entre blocos adjacentes, deixando bordas
    # "escorridas"/irregulares em vez de um contorno limpo.
    binaria = m_close(binaria, morph_disk(4))
    binaria = remove_small_objects(binaria, min_size=250)
    binaria = m_open(binaria, morph_disk(1))

    alfa = gaussian(binaria.astype(np.float64), sigma=1.2)
    alfa = np.clip(alfa / max(alfa.max(), 1e-6), 0, 1)

    dist_dentro = ndimage.distance_transform_edt(binaria)
    anel_borda = (dist_dentro > 0) & (dist_dentro <= 3)
    alfa[anel_borda] = np.maximum(alfa[anel_borda], 0.92)

    # Camada de segurança final: mesmo que o blur do passo acima tenha
    # espalhado alguns pixels de alfa poucos px além do contorno (o blur
    # normaliza pelo próprio máximo e não sabe onde fica a silhueta), aqui
    # ele é recortado de volta pela silhueta real -- nenhum pixel de fundo
    # pode ficar com alfa > 0, não importa o que aconteceu antes.
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

    for nome in nomes:
        if nome.startswith("ignore"):
            continue
        idx = nome_para_id[nome]
        binaria = rotulos_ws == idx
        if nome in LIMITE_LATERAL:
            x0f, x1f = LIMITE_LATERAL[nome]
            binaria = binaria.copy()
            binaria[:, : int(x0f * w)] = False
            binaria[:, int(x1f * w) :] = False
        salvar_mascara(PASTA_SAIDA / f"{nome}.png", binaria, corpo_mask, h, w)
        print(f"{nome}: {binaria.sum()} px -> {PASTA_SAIDA / f'{nome}.png'}")

    # visualização de depuração: cada região com uma cor diferente, pra
    # conferir rapidamente antes de confiar nos PNGs finais.
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
