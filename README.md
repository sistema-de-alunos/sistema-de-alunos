# Sistema de Alunos

Aplicativo desktop para personal trainers e academias cadastrarem e acompanharem seus alunos: anamnese, avaliações físicas, composição corporal e registro de fotos, tudo salvo localmente no computador.

## Sobre o projeto

O sistema reúne em um só lugar as informações de cada aluno e o histórico das suas avaliações.

**Painel de alunos**

- Lista dos alunos cadastrados, em ordem alfabética, com busca por nome.
- Foto de perfil para cada aluno, com ajuste de posição e zoom.
- Abertura do cadastro para consulta e edição, e exclusão com confirmação.

**Cadastro e anamnese**

O cadastro é feito em etapas:

1. **Dados do aluno:** nome completo, idade, sexo e altura.
2. **Histórico de atividade física:** se já treinou, há quanto tempo treina e tempo sem atividade física.
3. **Objetivo principal:** emagrecimento, hipertrofia, condicionamento, reabilitação ou outro objetivo descrito pelo personal.
4. **Frequência e tempo de treino:** dias por semana e tempo de treino por dia.
5. **Histórico de saúde e limitações:** doenças, limitações de movimento, dores e cirurgias, com campo para detalhar.
6. **Hábitos de vida:** medicamento controlado, dieta, consumo de álcool e tabagismo.

**Avaliação física**

- **Circunferências corporais:** ombro, tórax, cintura, abdômen, quadril, braços (relaxados e contraídos), antebraços, coxas e panturrilhas, com um boneco anatômico (masculino ou feminino, conforme o sexo do aluno) que destaca as regiões já medidas.
- **Dobras cutâneas e peso:** tríceps, peito, axilar média, subescapular, abdominal, supra-ilíaca e coxa.
- **Composição corporal:** calculada automaticamente pelo protocolo de Jackson & Pollock de 7 dobras, com fórmulas diferentes para homens e mulheres, e pela equação de Siri. Mostra densidade corporal, percentual de gordura, massa gorda e massa magra.
- **Registro de fotos:** sessões de fotos com data, cada uma com imagem de frente, de costas, do lado direito e do lado esquerdo.

**Histórico ao longo do tempo**

- As circunferências, as dobras cutâneas e as sessões de fotos aceitam várias avaliações por aluno, cada uma com sua própria data. Uma nova avaliação começa com a data atual do computador, que pode ser alterada.
- Avaliações já salvas ficam bloqueadas para consulta, preservando o histórico.

## Funcionamento

O Sistema de Alunos é um aplicativo para Windows. Depois de instalado, funciona totalmente offline: não depende de servidor, de conta ou de banco de dados externo.

Os dados ficam em um banco SQLite criado automaticamente no computador do usuário, em:

```
%APPDATA%\SistemaDeAlunos\alunos.db
```

Tudo permanece salvo ao fechar e abrir o aplicativo novamente.

## Instalação

Não é preciso instalar Python, bibliotecas ou configurar nada manualmente.

1. Abra o **CMD** (Prompt de Comando).
2. Copie o comando abaixo.
3. Cole no CMD.
4. Pressione **ENTER**.
5. Aguarde a instalação terminar.

```
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; irm https://raw.githubusercontent.com/sistema-de-alunos/sistema-de-alunos/main/instalar.ps1 | iex"
```

Esse comando executa o instalador ([`instalar.ps1`](instalar.ps1)), que:

- baixa a versão mais recente do sistema, publicada nas [Releases](https://github.com/sistema-de-alunos/sistema-de-alunos/releases) deste repositório;
- instala o aplicativo em `%LOCALAPPDATA%\Programs\SistemaDeAlunos`, sem pedir permissão de administrador;
- cria atalhos na Área de Trabalho e no Menu Iniciar;
- abre o Sistema de Alunos.

## Atualização

Quando uma nova versão for disponibilizada, basta executar o mesmo comando de instalação novamente:

```
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; irm https://raw.githubusercontent.com/sistema-de-alunos/sistema-de-alunos/main/instalar.ps1 | iex"
```

O instalador fecha o aplicativo, se estiver aberto, substitui os arquivos do programa pela versão mais recente e o abre de novo. Os dados dos alunos, que ficam em `%APPDATA%\SistemaDeAlunos`, não são alterados.

O sistema não se atualiza sozinho: a atualização acontece somente quando o comando é executado.

## Requisitos

- **Windows:** o instalador e o aplicativo são destinados ao Windows.
- **Internet:** necessária apenas para baixar e instalar (ou atualizar) o programa. Depois de instalado, o aplicativo funciona offline.

## Observação sobre os dados

- Os dados ficam **somente no computador** onde o sistema está instalado. Não há sincronização em nuvem nem backup automático.
- Para não perder informações, faça backup periódico da pasta `%APPDATA%\SistemaDeAlunos`.
- As fotos não são copiadas para dentro do sistema: ele guarda o caminho do arquivo de imagem escolhido. Por isso, mantenha os arquivos das fotos no lugar e inclua essas pastas no seu backup. Se uma imagem for movida ou apagada, ela deixa de aparecer no sistema.

## Tecnologias

- **Python:** linguagem do aplicativo.
- **PySide6 (Qt):** interface gráfica.
- **SQLite:** banco de dados local.
- **PyInstaller:** geração do executável para Windows.
- **PowerShell:** script de instalação e de geração do pacote.

## Estrutura do projeto

```
main.py                  Ponto de entrada do aplicativo
ui_main.py               Janela principal e navegação entre painel e cadastro
core/                    Tema visual, validações e importações do Qt
database/                Conexão com o SQLite e criação/atualização das tabelas
models/                  Acesso aos dados de alunos, avaliações e fotos
gui/                     Telas (painel, cadastro em etapas, foto de perfil) e componentes
assets/corpos/           Imagens dos bonecos anatômicos e máscaras das regiões do corpo
instalar.ps1             Instalador usado pelo comando da seção Instalação
tools/                   Ferramentas de desenvolvimento (geração do executável e das máscaras)
```

## Desenvolvimento

Para executar a partir do código-fonte (requer Python 3 instalado):

```
pip install -r requirements.txt
python main.py
```

Para gerar o pacote de instalação (`dist\SistemaDeAlunos.zip`), que deve ser anexado a uma nova Release com esse mesmo nome:

```
powershell -ExecutionPolicy Bypass -File tools\gerar_executavel.ps1
```
