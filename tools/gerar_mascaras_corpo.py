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

# Topo das coxas reto (pedido: lados retos, não arredondados, abaixo do
# corte reto do quadril em `LIMITE_INFERIOR`).
LIMITE_SUPERIOR: dict = {"right_thigh": 0.492, "left_thigh": 0.492}

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
# Fundo do quadril reto (pedido: a parte de baixo arredondada descia demais).
LIMITE_INFERIOR: dict = {"hip": 0.475}

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

# Faixa (frações de altura) logo abaixo do umbigo que liga os 3 pedaços de
# "hip" num só: as asas e a ponta central só se tocam através da borda de
# baixo do "abdomen" (as coxas sobem entre elas). Os pixels de
# `_DOADORAS_PONTE_QUADRIL` dessa faixa passam pro "hip" e saem da dona
# original -- a faixa desce além do abdômen e come o topo das coxas pra
# deixar a ligação mais grossa.
PONTE_QUADRIL_Y = (0.412, 0.448)
_DOADORAS_PONTE_QUADRIL = ("abdomen", "right_thigh", "left_thigh")
# Quanto (px) a borda externa do quadril fica pra dentro do corpo real.
QUADRIL_RECUO_EXTERNO_PX = 4
# Depois das coxas prontas, o fundo reto do quadril (`LIMITE_INFERIOR`) desce
# até este tanto (px) pela pele livre, até encostar nas coxas (ver `main()`).
DESCIDA_QUADRIL_PX = 80

# O fechamento da silhueta solda o vão entre as pernas (ver comentário de
# `ZONAS_EXCLUSAO_FECHAMENTO`) e as coxas herdavam esse fundo como lateral
# interna. Dentro desta faixa central de x, as coxas são recortadas pelo
# alfa real de `IMAGEM` (pixel transparente = fundo) -- lateral externa e
# resto da silhueta não mudam.
FAIXA_INTERNA_COXAS_X = (0.44, 0.56)

# Na lateral EXTERNA, o mesmo fechamento cria uma "aba" sobre o fundo no
# meio da coxa. Não some de todo (só "um pouco"): pixels de fundo fora da
# faixa central são mantidos até esta distância (px) do corpo real. A aba
# da esquerda da imagem ("right_thigh") era maior (~39px) que a da direita
# (~21px), por isso recua mais.
ABA_EXTERNA_COXA_MAX_PX = {"right_thigh": 3, "left_thigh": 2}

# Faixas da lateral externa onde sobrava pele real sem máscara: em cada
# faixa de linhas (frações de altura) a coxa cresce até o raio (px) pra
# fora, só sobre pixels que não são de outra região.
AUMENTO_EXTERNO_COXA = [
    ((0.59, 0.655), 6),   # parte de baixo, perto do joelho
    ((0.45, 0.56), 40),   # parte de cima, perto do quadril
]

# Quanto (px) braço e ombro crescem pra fora, sobre a borda escura da pele
# que a silhueta deixa de fora (ver uso em `main()`).
AUMENTO_EXTERNO_BRACO_OMBRO_PX = {"right_arm": 5, "left_arm": 5, "shoulder": 5}
# Quanto (px) o fundo do braço fica acima do topo do antebraço.
RECUO_INFERIOR_BRACO_PX = 22
# Raio (px) do fechamento que tapa falhas na borda interna do braço.
FALHA_INTERNA_BRACO_PX = 10
# Quanto (px) a borda interna do braço fica afastada das máscaras finais da
# cintura e do peito (o braço direito invadia os dois).
RECUO_BRACO_CINTURA_PX = {"right_arm": 8}
# O canto superior externo da cintura direita (lado esquerdo da imagem)
# ficava cortado pelo peito, com uma faixa de pele sem máscara entre braço e
# peito. A cintura sobe/cresce até este tanto (px) só sobre pele que não é
# de nenhuma outra máscara final.
SUBIDA_CINTURA_DIREITA_PX = 25
# A ponta de baixo da cintura parava antes do quadril, com pele sem máscara
# entre os dois. Ela desce até este tanto (px), só sobre pele livre.
DESCIDA_CINTURA_PX = 40

# O antebraço terminava no meio: a metade de baixo (até o punho) é da mão
# ("ignore_hand_*"). Ele cresce este tanto (px) pra baixo, só a partir da
# linha ALONGAMENTO_ANTEBRACO_Y0 (fração da altura) -- acima dela nada muda.
ALONGAMENTO_ANTEBRACO_PX = 42
ALONGAMENTO_ANTEBRACO_Y0 = 0.42
# Alcance (px) do preenchimento da borda interna do antebraço (ver `main()`).
BORDA_INTERNA_ANTEBRACO_PX = 12
# Alcance (px) do preenchimento da metade externa do antebraço (ver `main()`).
PREENCHIMENTO_EXTERNO_ANTEBRACO_PX = 30

# Quanto (px) o topo das panturrilhas desce (corte por altura, ver `main()`).
RECUO_TOPO_PANTURRILHA_PX = 85
# Quanto (px) as bordas externa/interna das panturrilhas crescem.
AUMENTO_LATERAL_PANTURRILHA_PX = 8
# Quanto (px) o meio do topo desce em relação aos cantos (arco invertido).
ARREDONDAMENTO_TOPO_PANTURRILHA_PX = 30

# Ponta de baixo das coxas (ver `main()`): quanto (px) desce, e quanto o
# meio sobe em arco em volta do joelho.
ALONGAMENTO_COXA_PX = 20
ARCO_JOELHO_COXA_PX = 30
# Quanto (px) o topo das coxas fica afastado da máscara final do quadril.
RECUO_COXA_QUADRIL_PX = 8
# Topo das coxas em arco: quanto (px) os cantos descem em relação ao meio, e
# quanto o canto interno (virilha) desce a mais.
ARCO_TOPO_COXA_PX = 20
RECUO_TOPO_INTERNO_COXA_PX = {"right_thigh": 80, "left_thigh": 110}
# Distância mínima (px) de cada coxa até a linha central da imagem.
FOLGA_ENTRE_COXAS_PX = 10


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
    (0.360, 0.268),  # ponta superior, entre a axila e o peitoral -- axila ainda maior
    (0.392, 0.275),
    (0.416, 0.284),
    (0.424, 0.306),
    (0.431, 0.317),
    (0.427, 0.332),
    (0.419, 0.346),
    (0.411, 0.370),
    (0.403, 0.392),
    (0.396, 0.402),  # início da curva do fundo (perto do abdômen)
    (0.385, 0.407),
    (0.374, 0.408),
    (0.363, 0.405),
    (0.352, 0.397),
    (0.390, 0.377),  # fim da curva do fundo (perto do braço) -- lateral externa um pouco mais estreita
    (0.388, 0.353),
    (0.373, 0.332),  # borda externa superior puxada pra axila (serrátil livre ali)
    (0.364, 0.318),
    (0.362, 0.303),
    (0.364, 0.278),
]

# A ilustração não é perfeitamente simétrica perto da axila: no lado
# DIREITO da imagem (espelho) os 4 últimos pontos acima (borda externa
# superior) ficavam um pouco largos demais, então recuam só lá.
RECUO_ESPELHO_TOPO_EXTERNO = 0.004
# Recuo extra de TODA a borda externa (pontos a partir do fundo externo, perto
# do antebraço) só no espelho -- a cintura direita da imagem encostava demais
# no braço. O lado esquerdo da imagem não muda.
RECUO_ESPELHO_EXTERNO = 0.010
# ...mas a ponta superior externa (perto do bíceps) ficou curta demais com
# esse recuo -- os 3 pontos do topo externo avançam de volta pra fora, só
# no espelho.
AVANCO_ESPELHO_TOPO = 0.012

# Regiões vizinhas que a máscara da cintura nunca pode invadir -- mesmo que
# o polígono acima avance por cima delas, elas são subtraídas antes de
# salvar (ver `main()`), então ficam bit-a-bit como já estavam.
_VIZINHAS_CINTURA = ("chest", "abdomen", "hip", "right_arm", "left_arm")


def mascara_poligono_cintura(h: int, w: int) -> np.ndarray:
    """Rasteriza `POLIGONO_CINTURA_LADO` (e seu espelho) em uma máscara
    booleana do tamanho da imagem -- ainda sem recorte pela silhueta nem
    pelas regiões vizinhas, isso acontece em `main()`."""
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

    # Ver `FAIXA_INTERNA_COXAS_X`.
    fundo_real = np.array(Image.open(IMAGEM).convert("RGBA"))[..., 3] < 128
    dist_ao_corpo = ndimage.distance_transform_edt(fundo_real)
    dist_ao_fundo = ndimage.distance_transform_edt(~fundo_real)
    fundo_entre_pernas = fundo_real.copy()
    fundo_entre_pernas[:, : int(FAIXA_INTERNA_COXAS_X[0] * w)] = False
    fundo_entre_pernas[:, int(FAIXA_INTERNA_COXAS_X[1] * w) :] = False

    # Ver `PONTE_QUADRIL_Y`.
    ponte_quadril = np.isin(rotulos_ws, [nome_para_id[n] for n in _DOADORAS_PONTE_QUADRIL])
    ponte_quadril[: int(PONTE_QUADRIL_Y[0] * h)] = False
    ponte_quadril[int(PONTE_QUADRIL_Y[1] * h) :] = False

    mascaras_finais: dict = {}
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
        if nome == "hip":
            # O fechamento da silhueta estende a lateral externa sobre o
            # fundo; recorta pelo alfa real, recuando QUADRIL_RECUO_EXTERNO_PX.
            binaria = (binaria | ponte_quadril) & (dist_ao_fundo > QUADRIL_RECUO_EXTERNO_PX)
        elif nome in _DOADORAS_PONTE_QUADRIL:
            binaria = binaria & ~ponte_quadril
        if nome in ("right_arm", "left_arm"):
            # O fechamento da silhueta solda o vão braço-tronco e o watershed
            # dava esse fundo (e a pele do tronco do outro lado dele, até a
            # cintura) ao braço. Recorta pelo alfa real e fica só com o
            # maior pedaço -- o braço de verdade.
            binaria = binaria & ~fundo_real
            rotulos_braco, n_pedacos = ndimage.label(binaria)
            if n_pedacos > 1:
                tamanhos = ndimage.sum(binaria, rotulos_braco, range(1, n_pedacos + 1))
                binaria = rotulos_braco == int(np.argmax(tamanhos)) + 1
            # Tapa mordidas pequenas na borda interna (perto da cintura),
            # só sobre pele real que não é de outra região. A "waist" do
            # watershed mordia o braço ali, mas a cintura final é o polígono
            # (já pronto em `mascaras_finais`) -- vale ele, não o watershed.
            outras = np.isin(rotulos_ws, [
                nome_para_id[n] for n in nomes
                if n not in (nome, "waist") and not n.startswith("ignore")
            ]) | mascaras_finais["waist"]
            fechado = m_close(binaria, morph_disk(FALHA_INTERNA_BRACO_PX))
            binaria = binaria | (fechado & ~fundo_real & ~outras)
            # Ver `RECUO_BRACO_CINTURA_PX`.
            if RECUO_BRACO_CINTURA_PX.get(nome):
                perto_cintura = ndimage.binary_dilation(
                    mascaras_finais["waist"] | mascaras_finais["chest"], morph_disk(RECUO_BRACO_CINTURA_PX[nome])
                )
                binaria = binaria & ~perto_cintura
            # A ponta de baixo descia pela borda interna, sobre o antebraço.
            # Corta abaixo do topo do antebraço, coluna a coluna (fora das
            # colunas dele, corta na altura do ponto mais alto desse topo),
            # subindo RECUO_INFERIOR_BRACO_PX -- só na metade externa. Na
            # metade interna (lado do tronco) desce até o topo do antebraço,
            # senão sobra um canto sem máscara acima do cotovelo -- mas sem
            # passar da altura típica desse topo nas 30 colunas mais internas
            # (na ponta o topo despenca e o braço escorria ao lado dele).
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
            # Ver `ALONGAMENTO_ANTEBRACO_PX`: cresce "por dentro" do braço
            # desenhado (dilatação geodésica), só sobre pele que é da mão
            # ("ignore_*") ou de ninguém, e só pra baixo do topo atual --
            # a frente de crescimento segue a inclinação do próprio antebraço.
            # Antes, descarta pedaços soltos (havia um perto do punho do
            # "left_forearm" que cresceria até a mão).
            rotulos_ab, n_pedacos = ndimage.label(binaria)
            if n_pedacos > 1:
                tamanhos = ndimage.sum(binaria, rotulos_ab, range(1, n_pedacos + 1))
                binaria = rotulos_ab == int(np.argmax(tamanhos)) + 1
            livre = ~fundo_real & ~np.isin(rotulos_ws, [nome_para_id[n] for n in nomes if n != nome and not n.startswith("ignore")])
            livre[: int(ALONGAMENTO_ANTEBRACO_Y0 * h)] = False
            binaria = ndimage.binary_dilation(
                binaria, iterations=ALONGAMENTO_ANTEBRACO_PX, mask=livre | binaria
            )
            # Nivela: o lado de fora parava mais alto que o de dentro. Completa
            # até a linha mais baixa já alcançada, deixando o fundo reto.
            livre[np.where(binaria.any(axis=1))[0].max() + 1 :] = False
            binaria = ndimage.binary_dilation(
                binaria, iterations=ALONGAMENTO_ANTEBRACO_PX, mask=livre | binaria
            )
            # Borda interna (lado do tronco), perto do cotovelo: sobrava pele
            # sem máscara -- era do braço no watershed, mas saiu do braço no
            # recorte "maior pedaço" acima. O antebraço cobre essa pele (e
            # fecha os furinhos), sem tocar a máscara final do braço nem
            # outras regiões, e só na metade do lado do tronco.
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
            # O braço recuou (`RECUO_INFERIOR_BRACO_PX`) e sobrou uma faixa
            # sem máscara acima do antebraço, além da borda escura de fora.
            # O antebraço sobe/cresce sobre essa pele livre até encostar no
            # braço, sem descer além do próprio fundo.
            livre_ext = ~fundo_real & ~bloqueadas
            livre_ext[np.where(binaria.any(axis=1))[0].max() + 1 :] = False
            binaria = ndimage.binary_dilation(
                binaria, iterations=PREENCHIMENTO_EXTERNO_ANTEBRACO_PX, mask=livre_ext | binaria
            )
            binaria = ndimage.binary_fill_holes(binaria)
        if nome in ("right_calf", "left_calf"):
            # O fechamento da silhueta solda o vão entre as canelas e as duas
            # panturrilhas se ligavam por ele. Recorta pelo alfa real, fica
            # com o maior pedaço e baixa o topo `RECUO_TOPO_PANTURRILHA_PX`
            # (corte por altura -- as laterais abaixo da linha ficam intactas).
            binaria = binaria & ~fundo_real
            rotulos_pant, n_pedacos = ndimage.label(binaria)
            if n_pedacos > 1:
                tamanhos = ndimage.sum(binaria, rotulos_pant, range(1, n_pedacos + 1))
                binaria = rotulos_pant == int(np.argmax(tamanhos)) + 1
            topo = np.where(binaria.any(axis=1))[0].min()
            corte = topo + RECUO_TOPO_PANTURRILHA_PX
            # Topo em arco invertido: o corte é uma meia-elipse -- nos cantos
            # fica em `corte` e no meio desce `ARREDONDAMENTO_TOPO_PANTURRILHA_PX`,
            # encaixando embaixo da curva do joelho.
            xs_topo = np.where(binaria[corte : corte + 40].any(axis=0))[0]
            cx, rx = (xs_topo.min() + xs_topo.max()) / 2, (xs_topo.max() - xs_topo.min()) / 2 + 1
            u = np.clip((np.arange(w) - cx) / rx, -1, 1)
            corte_col = corte + ARREDONDAMENTO_TOPO_PANTURRILHA_PX * np.sqrt(1 - u**2)
            acima_do_oval = np.arange(h)[:, None] < corte_col[None, :]
            binaria = binaria & ~acima_do_oval
            # Alarga as bordas externa e interna sobre pele real sem outra
            # região (a borda escura fica fora da silhueta), sem subir acima
            # do topo oval.
            extra = ndimage.binary_dilation(binaria, morph_disk(AUMENTO_LATERAL_PANTURRILHA_PX))
            extra &= ~acima_do_oval
            outras = np.isin(rotulos_ws, [nome_para_id[n] for n in nomes if n != nome and not n.startswith("ignore")])
            binaria = binaria | (extra & ~fundo_real & ~outras)
        if nome in AUMENTO_EXTERNO_BRACO_OMBRO_PX:
            # A borda externa é pele escura (gray<100) fora da silhueta.
            # Cresce só sobre pixels sem região nenhuma (rótulo 0) que são
            # corpo pelo alfa real -- vizinhos e o vão braço-tronco ficam
            # intocados, então na prática só o lado de fora cresce.
            extra = ndimage.binary_dilation(binaria, morph_disk(AUMENTO_EXTERNO_BRACO_OMBRO_PX[nome]))
            binaria = binaria | (extra & (rotulos_ws == 0) & ~fundo_real)
        if nome in ("right_thigh", "left_thigh"):
            binaria = binaria & ~fundo_entre_pernas
            aba = dist_ao_corpo > ABA_EXTERNA_COXA_MAX_PX[nome]
            aba[:, int(FAIXA_INTERNA_COXAS_X[0] * w) : int(FAIXA_INTERNA_COXAS_X[1] * w)] = False
            binaria = binaria & ~aba
            # Ver `AUMENTO_EXTERNO_COXA`. Regiões "ignore_*" podem ser
            # invadidas: a pele ao lado do topo da coxa é "ignore_hand_*"
            # (sementes extras pra tirá-la do quadril), não a mão desenhada,
            # que fica além do vão de fundo -- e `fundo_real` não é cruzado.
            outras = np.isin(rotulos_ws, [nome_para_id[n] for n in nomes if n != nome and not n.startswith("ignore")])
            base = binaria
            for (y0f, y1f), raio in AUMENTO_EXTERNO_COXA:
                extra = ndimage.binary_dilation(base, morph_disk(raio))
                extra[: int(y0f * h)] = False
                extra[int(y1f * h) :] = False
                extra[:, int(FAIXA_INTERNA_COXAS_X[0] * w) : int(FAIXA_INTERNA_COXAS_X[1] * w)] = False
                # A borda externa ali é pele escura (gray<100) que a silhueta
                # trata como fundo -- o limite aqui é o alfa real da imagem.
                binaria = binaria | (extra & ~fundo_real & ~outras)
            # Ponta de baixo: desce `ALONGAMENTO_COXA_PX` (dilatação geodésica
            # sobre pele real -- pode tomar o joelho, que é território de
            # panturrilha no watershed mas fica acima do topo dela), nivela e
            # recorta em arco: laterais descem, o meio sobe
            # `ARCO_JOELHO_COXA_PX` em volta do joelho (espelho do topo da
            # panturrilha).
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
            # A parte de cima subia colada no quadril (faixa ao lado da "asa"
            # externa e topo perto da virilha): recua RECUO_COXA_QUADRIL_PX da
            # máscara final do quadril e fica só com o maior pedaço.
            binaria = binaria & ~ndimage.binary_dilation(
                mascaras_finais["hip"], morph_disk(RECUO_COXA_QUADRIL_PX)
            )
            # Com o fundo do quadril cortado reto (`LIMITE_INFERIOR`), sobra
            # pele sem máscara no canto superior externo da coxa (onde descia
            # a "asa" do quadril): a coxa cresce sobre ela até o topo reto
            # (`LIMITE_SUPERIOR`), sem tocar outras regiões.
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
            # As duas coxas se tocavam na virilha: cada uma fica a
            # FOLGA_ENTRE_COXAS_PX da linha central (antes do arco abaixo, pra
            # ele arredondar já a partir da borda nova).
            binaria[:, w // 2 - FOLGA_ENTRE_COXAS_PX : w // 2 + FOLGA_ENTRE_COXAS_PX] = False
            # Topo em arco (espelho do joelho): o meio fica na linha reta de
            # `LIMITE_SUPERIOR` e os cantos descem `ARCO_TOPO_COXA_PX`; o
            # canto interno (virilha) desce mais `RECUO_TOPO_INTERNO_COXA_PX`.
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

    # Ver `DESCIDA_QUADRIL_PX`. Roda depois das coxas (que usam o quadril
    # cortado reto pra se afastar dele) e antes da cintura (que encosta no
    # quadril final).
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
    # Tapa os buracos que ficam fechados dentro dele (onde antes subiam os
    # topos das coxas), só sobre pele livre.
    quadril = quadril | (ndimage.binary_fill_holes(quadril) & ~outras_finais & ~fundo_real)
    mascaras_finais["hip"] = quadril
    salvar_mascara(PASTA_SAIDA / "hip.png", quadril, corpo_mask, h, w, raio_fechamento=4)

    # Ver `SUBIDA_CINTURA_DIREITA_PX`. Roda depois de tudo porque a faixa
    # livre só existe depois que o braço recua (`RECUO_BRACO_CINTURA_PX`).
    cintura = mascaras_finais["waist"]
    ocupado = np.zeros_like(cintura)
    for n, m in mascaras_finais.items():
        if n != "waist":
            ocupado |= m
    livre = ~fundo_real & ~ndimage.binary_dilation(ocupado, iterations=5)
    # Só a metade externa (lado do braço) da cintura direita.
    livre[:, int(np.where(cintura[:, : w // 2].any(axis=0))[0].mean()) :] = False
    livre[: np.where(cintura[:, : w // 2].any(axis=1))[0].min() - SUBIDA_CINTURA_DIREITA_PX] = False
    cintura = ndimage.binary_dilation(
        cintura, iterations=SUBIDA_CINTURA_DIREITA_PX, mask=livre | cintura
    )
    # Ver `DESCIDA_CINTURA_PX`: cada lado cresce pela pele livre -- desce até
    # perto do quadril e tapa as falhas da borda interna (lado do abdômen) --
    # sem subir acima do próprio topo. Depois um fechamento alisa a borda
    # serrilhada, também só sobre pele livre.
    # Abdômen e quadril sem folga (a cintura encosta neles, sem listra de
    # pele entre as máscaras); as outras vizinhas mantêm 3px de folga.
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
    # A cintura esquerda (lado direito da imagem) vazava do corpo ao lado do
    # braço (a silhueta fechada cobre o vão ali): recorta pelo alfa real.
    limite = corpo_mask | ~fundo_real
    limite[:, w // 2 :] = ~fundo_real[:, w // 2 :]
    cintura = cintura & limite
    salvar_mascara(
        PASTA_SAIDA / "waist.png", cintura, limite, h, w,
        raio_fechamento=FECHAMENTO_EXTRA.get("waist", 4),
    )

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
