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
     começam com "ignore_" são sorvedouros (rosto, pescoço, mãos, pés) --
     existem só para impedir que essas áreas sejam anexadas às regiões
     vizinhas nomeadas.
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
from skimage.draw import disk as draw_disk, polygon as draw_polygon

RAIZ = Path(__file__).resolve().parent.parent
IMAGEM = RAIZ / "assets" / "corpos" / "corpohomem.png"
PASTA_SAIDA = RAIZ / "assets" / "corpos" / "mascaras_masculino"

RAIO_FECHAMENTO_SILHUETA = 80
SIGMA_BLUR_ELEVACAO = 3.0
# 4e-4 (valor original) deixava a fronteira quadril/coxa (virilha) e
# quadril/braço caótica/serrilhada: o gradiente ali é fraco (pouca textura
# na prega inguinal), então o watershed ficava sem uma borda forte pra
# seguir e a fronteira oscilava pixel a pixel numa "agulha" -- daí os
# remendos retos antigos (LIMITE_SUPERIOR/LIMITE_LATERAL abaixo, hoje
# removidos dessas regiões). COMPACTNESS penaliza fronteiras compridas e
# tortuosas (a documentação do próprio skimage descreve exatamente esse
# uso); 1e-3 (2.5x o valor original) já é suficiente para o watershed
# convergir numa curva única e suave -- comparado visualmente contra 3e-3
# e 1e-2, que já distorcem o contorno normal do tórax/abdômen/ombro para
# divisões quase retas por dependerem demais da distância às sementes em
# vez do gradiente real da imagem.
COMPACTNESS = 1e-3
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
    # Duas sementes extras cada (0.33/0.35 e espelho 0.67/0.65, y=0.37-0.39):
    # sem elas, a sombra do tríceps perto da dobra do cotovelo (pele real,
    # só escura na ilustração -- confirmado lendo os pixels, tom de pele
    # ~(137,60,50), não fundo) tinha gradiente fraco demais para o
    # watershed decidir sozinho e "right_forearm"/"left_forearm" arrematava
    # essa sombra como se fosse antebraço, formando uma cunha triangular
    # avançando na direção do tronco (visível renderizando o
    # CorpoInterativoWidget de verdade). As sementes aqui não CORTAM nada
    # -- só dizem ao watershed a quem essa sombra pertence de verdade
    # (tríceps), deixando-o decidir a borda pelo próprio gradiente da
    # dobra do cotovelo.
    "right_arm": [(0.29, 0.32), (0.33, 0.37), (0.35, 0.39)],
    "left_arm": [(0.71, 0.32), (0.67, 0.37), (0.65, 0.39)],
    # Vários pontos ao longo do antebraço/mão (cotovelo -> dedos), não só
    # um: perto do quadril esse braço pendurado cai dentro da zona de
    # exclusão do fechamento da silhueta (ver ZONAS_EXCLUSAO_FECHAMENTO), e
    # sem o fechamento ali o contorno bruto fragmenta essa faixa em pedaços
    # -- um pedaço sem nenhuma semente por perto ficava pra "hip" (o vazio
    # virava um degrau reto, a própria borda da zona de exclusão).
    "right_forearm": [(0.235, 0.43), (0.28, 0.38), (0.26, 0.48)],
    "left_forearm": [(0.765, 0.43), (0.72, 0.38), (0.74, 0.48)],
    # (0.30/0.32/0.28, 0.49-0.51) extras: mesmo fenômeno do vazamento de
    # "left_forearm" perto do punho (ver comentário grande abaixo), só que
    # aqui era "hip" quem arrematava essa faixa de pele em sombra -- um
    # retângulo de verdade grudado no quadril (a borda de
    # ZONAS_EXCLUSAO_FECHAMENTO), visível renderizando o
    # CorpoInterativoWidget. Mesma correção: ensinar ao watershed que esse
    # pedaço é território da mão (nunca desenhado), não do quadril.
    "ignore_hand_right": [
        (0.19, 0.53), (0.22, 0.45), (0.30, 0.45), (0.35, 0.45),
        (0.30, 0.50), (0.32, 0.51), (0.28, 0.51), (0.33, 0.49),
    ],
    # "left_forearm" tinha um segundo vazamento, independente do cotovelo:
    # perto do punho (y=0.467-0.537), a mesma pele em sombra (confirmado
    # nos pixels) fica ambígua entre punho/mão e quadril -- nem uma semente
    # de "hip" ali resolve bem (o watershed reivindica uma cunha enorme por
    # regra de distância, sem gradiente forte pra travar a borda). Como
    # essa faixa é realmente parte da mão/vão junto ao quadril (não do
    # antebraço nem de um músculo específico do tronco), os pontos extras
    # abaixo ensinam o watershed a tratá-la como território de
    # "ignore_hand_left" (nunca desenhado -- ver `main()`), tirando-a de
    # "left_forearm" sem forçar essa área a virar outra região errada.
    "ignore_hand_left": [
        (0.81, 0.53), (0.78, 0.45), (0.70, 0.45), (0.65, 0.44),
        (0.70, 0.47), (0.72, 0.49), (0.74, 0.50),
        (0.70, 0.51), (0.72, 0.53), (0.68, 0.49), (0.68, 0.52),
    ],
    # (0.465/0.535, 0.455-0.475): sementes extras perto da linha média,
    # dentro da virilha -- sem elas, o adutor/púbis (pele real, textura de
    # músculo, checada nos pixels) tem gradiente fraco demais ali e "hip"
    # tomava esse território todo, formando um "V" que descia fundo demais
    # entre as pernas (visível renderizando o CorpoInterativoWidget: o
    # verde do quadril quase encostava no do lado oposto). Como esse
    # músculo é realmente adutor (coxa), não glúteo/quadril, essas sementes
    # só corrigem a QUEM o watershed atribui essa área -- não cortam nada.
    "right_thigh": [(0.40, 0.50), (0.38, 0.55), (0.41, 0.60), (0.465, 0.455), (0.46, 0.475)],
    "left_thigh": [(0.60, 0.50), (0.62, 0.55), (0.59, 0.60), (0.535, 0.455), (0.54, 0.475)],
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
#
# (O vão entre as duas pernas tem o mesmo problema -- o fechamento também o
# solda entre a virilha e perto do tornozelo -- mas restaurá-lo aqui mexe na
# silhueta usada por TODAS as regiões e mudava também "hip"/"abdomen" [parte
# superior, que não pode mudar]. Ver LIMITE_LATERAL/LIMITE_SUPERIOR de
# coxa/panturrilha abaixo: mesmo problema, corrigido só nessas máscaras.)
ZONAS_EXCLUSAO_FECHAMENTO = [
    (0.24, 0.37, 0.395, 0.50),
    (0.63, 0.76, 0.395, 0.50),
]

# HISTÓRICO (revisão que trocou os cortes retos abaixo por COMPACTNESS mais
# alto, ver esse comentário): "hip"/"right_thigh"/"left_thigh"/"right_calf"/
# "left_calf" tinham cada uma um corte reto (LIMITE_LATERAL e/ou
# LIMITE_SUPERIOR) só para disfarçar uma fronteira caótica/serrilhada na
# virilha e no joelho -- o gradiente é fraco ali (pouca textura na prega
# inguinal e na face medial do joelho), então o watershed com COMPACTNESS
# baixo ficava sem uma borda forte pra seguir e a fronteira oscilava
# pixel a pixel numa "agulha", em vez de acompanhar a curva anatômica real.
# Cortar reto escondia a agulha, mas trocava "serrilhado" por "reta
# artificial" -- exatamente os "blocos/retângulos" que não deveriam
# aparecer. Com COMPACTNESS = 1e-3 (ver acima) o próprio watershed já
# converge numa curva única e suave nessas fronteiras (confirmado
# visualmente e no perfil de largura por linha -- sem mais salto
# instantâneo de largura, só crescimento gradual), então nenhum desses
# cortes retos é mais necessário: os dois dicts abaixo ficam vazios de
# propósito (mantidos, e não removidos, só para o restante do código que os
# referencia continuar funcionando sem alterações).
LIMITE_LATERAL: dict = {}

LIMITE_SUPERIOR: dict = {}

# HISTÓRICO: "left_forearm" tinha um corte reto aqui (`LIMITE_INFERIOR`,
# y=0.478) para um vazamento perto do punho -- dentro de
# ZONAS_EXCLUSAO_FECHAMENTO, a pele do antebraço em sombra ficava ambígua
# com o vão do quadril/mão, e o watershed "arrematava" essa faixa como se
# fosse antebraço até quase a mão. Tentativas de resolver isso puramente
# com suavização morfológica (abrir + manter só o maior componente conexo)
# amputavam o antebraço bem acima do punho de verdade -- pioravam o
# resultado. A correção que funcionou (ver `ignore_hand_left` em
# `SEMENTES`, acima) foi ensinar ao PRÓPRIO watershed, com sementes
# adicionais bem no meio da área ambígua, que aquele pedaço pertence à
# "mão" (uma região "ignore_*", nunca desenhada -- ver `main()`), em vez de
# cortar uma faixa reta na máscara já pronta. `LIMITE_INFERIOR` fica vazio
# de propósito, pela mesma razão de `LIMITE_LATERAL`/`LIMITE_SUPERIOR`
# acima.
LIMITE_INFERIOR: dict = {}

# "hip" tem um problema geométrico diferente de jaggedness: bem no canto de
# `ZONAS_EXCLUSAO_FECHAMENTO` (onde o fechamento da silhueta é desligado
# para restaurar o vão braço-quadril), a borda RETA daquele retângulo (o
# canto em x=0.37, y=0.395 do lado direito, espelhado do esquerdo) aparece
# encostada na máscara de "hip" como um degrau de 90° bem visível -- um
# "canto de retângulo" de verdade, não uma aproximação. Diferente da
# jaggedness da virilha (resolvida com COMPACTNESS acima) e do "V" fundo
# demais na virilha (resolvido com as sementes extras de "right_thigh"/
# "left_thigh", acima), aqui a causa é a forma do próprio retângulo de
# exclusão -- então precisa de uma correção à parte: abrir (erodir+dilatar)
# arredonda o canto reto sem afetar a curva anatômica; fechar de novo com o
# mesmo raio restaura a área que a abertura tirou a mais do contorno.
#
# Com as sementes de "right_thigh"/"left_thigh" perto da linha média, "hip"
# hoje sai como VÁRIOS pedaços de verdade (asa esquerda, asa direita, e uma
# pequena ponta central acima do púbis -- confirmado: 3 componentes
# conexos, ~10k/8k/4.5k px, todos anatomia real, não ruído) -- diferente de
# antes (um só componente com o canto reto grudado nele). "Manter só o
# maior componente" descartaria as asas ou a ponta central por engano, dado
# que os três já têm tamanhos parecidos; por isso a versão atual descarta
# só fragmentos GENUINAMENTE pequenos (min_size, mesmo limiar de ruído que
# `salvar_mascara` já usa no resto do arquivo), preservando qualquer
# pedaço anatômico de verdade, não só o maior.
SUAVIZACAO_CONTORNO = {
    "hip": 6,
}


def _suavizar_contorno(binaria: np.ndarray, raio: int, tamanho_minimo: int = 1000) -> np.ndarray:
    """Arredonda cantos retos artificiais (ver `SUAVIZACAO_CONTORNO`) sem
    aproximar a região por um retângulo/polígono -- opera diretamente nos
    pixels já decididos pelo watershed, só suavizando a borda. Preserva
    TODOS os pedaços com pelo menos `tamanho_minimo` pixels (não só o
    maior) -- uma região pode legitimamente sair em mais de um pedaço
    anatômico (ex.: as duas "asas" do quadril, separadas pela coxa)."""
    suavizada = m_open(binaria, morph_disk(raio))
    suavizada = remove_small_objects(suavizada, min_size=tamanho_minimo)
    return m_close(suavizada, morph_disk(raio))


# "waist" é a ÚNICA região que não usa o resultado bruto do watershed
# (`rotulos_ws == idx`) como máscara final -- ver o `if nome == "waist"` em
# `main()`. Motivo: o oblíquo externo/serrátil ali tem textura de fibra
# muito sutil (mesmo nível de cinza do tórax/abdômen vizinhos após o blur
# do gradiente), então o watershed, sem uma borda forte pra seguir, cai de
# volta na regra de distância (ponderada por COMPACTNESS) entre sementes
# vizinhas -- o que produz uma divisão quase reta/simétrica em vez de
# acompanhar o contorno real (visível em `watershed_debug.png`: a região
# saía como um bloco vertical de cantos retos, lida como "retângulo verde"
# em vez de músculo). Aumentar COMPACTNESS ou mexer nas sementes de
# vizinhos pra "empurrar" essa borda mudaria também chest/abdomen/hip
# (proibido tocar). A solução foi contornar a olho, direto sobre
# `corpohomem.png`, o polígono do oblíquo/serrátil visível (ponta entre
# axila e peitoral, descendo ao longo da bainha do reto abdominal, fundo
# arredondado acima do início do quadril) -- ver `POLIGONO_CINTURA_LADO`.
# Esse polígono nunca é usado sozinho: é sempre recortado por
# `corpo_mask` (silhueta) e por `_mascara_regioes_vizinhas_cintura`
# (chest/abdomen/hip/right_arm/left_arm, lidos do MESMO `rotulos_ws` já
# calculado) antes de virar a máscara final -- então mesmo que o polígono
# avance por engano sobre território de outra região, o resultado nunca
# invade uma máscara que já está correta (ver `main()`).
#
# Pontos (frações 0-1 de largura/altura) de UM lado -- o lado ESQUERDO da
# IMAGEM (lado DIREITO da pessoa). O outro lado é o espelho (x -> 1-x), já
# que a ilustração de frente é simétrica. Calibrado visualmente: se um dia
# a imagem base for substituída, recalibre soltando um overlay desses
# pontos sobre a nova imagem antes de confiar neles de novo.
POLIGONO_CINTURA_LADO = [
    (0.360, 0.278),  # ponta superior, entre a axila e o peitoral
    (0.388, 0.283),
    (0.415, 0.290),
    (0.435, 0.298),
    (0.443, 0.312),
    (0.438, 0.330),
    (0.428, 0.348),
    (0.418, 0.365),
    (0.408, 0.380),
    (0.400, 0.383),  # início da curva do fundo (perto do abdômen)
    (0.386, 0.386),
    (0.372, 0.388),
    (0.358, 0.387),
    (0.345, 0.384),
    (0.334, 0.380),  # fim da curva do fundo (perto do braço)
    (0.330, 0.368),
    (0.330, 0.345),
    (0.334, 0.322),
    (0.342, 0.300),
    (0.352, 0.286),
]

# Regiões vizinhas que a máscara da cintura nunca pode invadir -- mesmo que
# o polígono acima avance por cima delas, elas são subtraídas antes de
# salvar (ver `main()`), então ficam bit-a-bit como já estavam.
_VIZINHAS_CINTURA = ("chest", "abdomen", "hip", "right_arm", "left_arm")


def mascara_poligono_cintura(h: int, w: int) -> np.ndarray:
    """Rasteriza `POLIGONO_CINTURA_LADO` (e seu espelho) em uma máscara
    booleana do tamanho da imagem -- ainda sem recorte pela silhueta nem
    pelas regiões vizinhas, isso acontece em `main()`."""
    mascara = np.zeros((h, w), dtype=bool)
    for pontos in (POLIGONO_CINTURA_LADO, [(1 - x, y) for x, y in POLIGONO_CINTURA_LADO]):
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

    # Dentro da zona de exclusão, descarta o que só o fechamento adicionou
    # (restaura o vão real); fora dela, mantém o fechamento (conserta a
    # sombra). NÃO passa por binary_fill_holes de novo depois disso -- um
    # buraco perfeitamente cercado pelo fechamento reencheria exatamente a
    # zona que acabamos de restaurar.
    return corpo_bruto | (corpo_fechado & ~zona_exclusao)



# Raio do fechamento em `salvar_mascara` (o padrão é 4 -- ver abaixo). Só
# "waist" está aqui: a borda dela contra o tórax segue as interdigitações
# reais do serrátil, que na ilustração aparecem como um serrilhado bem miúdo
# (dentes de poucos px) -- com o fechamento padrão isso é preservado quase
# fiel demais, e o contorno lê como "picotado"/impreciso em vez de uma curva
# única. Um raio maior aqui só arredonda esses dentes pequenos (fechamento
# não desloca a borda geral, só funde reentrâncias menores que o raio) --
# continua recortado pela silhueta no final, então não pode fazer a região
# invadir o fundo nem crescer além do que já cresceria com o raio padrão.
FECHAMENTO_EXTRA = {
    "waist": 7,
}


def salvar_mascara(
    caminho: Path, binaria: np.ndarray, corpo_mask: np.ndarray, h: int, w: int, raio_fechamento: int = 4
) -> None:
    # Fecha falhas pequenas (gaps entre blocos vizinhos do mesmo músculo,
    # ex.: as junções finas entre os blocos do abdômen) antes de remover
    # manchas espúrias -- na ordem inversa, a abertura chegava a fragmentar
    # ligações finas legítimas entre blocos adjacentes, deixando bordas
    # "escorridas"/irregulares em vez de um contorno limpo.
    binaria = m_close(binaria, morph_disk(raio_fechamento))
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
        if nome == "waist":
            # Ver o comentário grande junto de `POLIGONO_CINTURA_LADO`: a
            # forma final da cintura não vem do watershed (`rotulos_ws ==
            # idx`, usado por todas as outras regiões), e sim de um
            # polígono calibrado à mão, recortado pela silhueta e pelas
            # regiões vizinhas já decididas por ESTE MESMO `rotulos_ws`
            # (não recalculadas -- só lidas, então chest/abdomen/hip/
            # right_arm/left_arm saem bit-a-bit iguais ao que já eram).
            vizinhas = np.zeros_like(corpo_mask)
            for vizinha in _VIZINHAS_CINTURA:
                vizinhas |= rotulos_ws == nome_para_id[vizinha]
            binaria = mascara_poligono_cintura(h, w) & corpo_mask & ~vizinhas
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
        if nome in LIMITE_INFERIOR:
            binaria = binaria.copy()
            binaria[int(LIMITE_INFERIOR[nome] * h) :, :] = False
        if nome in SUAVIZACAO_CONTORNO:
            binaria = _suavizar_contorno(binaria, SUAVIZACAO_CONTORNO[nome])
        salvar_mascara(
            PASTA_SAIDA / f"{nome}.png", binaria, corpo_mask, h, w,
            raio_fechamento=FECHAMENTO_EXTRA.get(nome, 4),
        )
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
