# Como publicar o memga no R-universe

O R-universe é uma central de pacotes de R, grátis, que compila o pacote a partir do GitHub e gera instaladores para Windows, Mac e Linux. Quem usa instala com `install.packages()`, sem esperar o CRAN. Os detalhes podem mudar, então confira <https://r-universe.dev/publish> se algo não bater.

## Como funciona

1. Você cria um repositório público no GitHub com um nome fixo: `safsalles.r-universe.dev` (seu usuário + `.r-universe.dev`). Ele só serve de lista dos seus pacotes.
2. Nele, um arquivo `packages.json` diz onde está cada pacote.
3. Você instala o app do R-universe no GitHub.
4. O R-universe lê a lista, compila e publica em `https://safsalles.r-universe.dev`.

## Passo a passo

### 1. Criar o repositório de registro

No GitHub, crie um repositório **público** chamado exatamente `safsalles.r-universe.dev`.

### 2. Criar o `packages.json`

Como o pacote está dentro de uma subpasta do `portfolio-ds` (e não na raiz de um repositório), use `subdir`:

```json
[
  {
    "package": "memga",
    "url": "https://github.com/safsalles/portfolio-ds",
    "subdir": "mem-ga/r"
  }
]
```

Salve como `packages.json` na raiz do repositório de registro e faça o commit.
Se um dia mover o pacote para um repositório só dele, tire a linha `subdir` e troque a `url`.

### 3. Instalar o app

1. Abra <https://github.com/apps/r-universe/installations/new>.
2. Escolha sua conta `safsalles`.
3. Selecione **só** os repositórios `safsalles.r-universe.dev` e `portfolio-ds`.
4. Confirme.

### 4. Esperar a compilação

- Em alguns minutos aparece a página <https://safsalles.r-universe.dev>, com a lista de pacotes e o estado de cada compilação (a primeira pode demorar um pouco).
- Se alguma plataforma falhar, o painel mostra o log. O pacote já passa no `R CMD check`, então o mais provável é problema de configuração (nome do repositório, `subdir` errado).
- Os dados, a documentação e o README do pacote aparecem na página.

### 5. Testar a instalação

Em um R limpo:

```r
install.packages("memga",
  repos = c("https://safsalles.r-universe.dev", "https://cloud.r-project.org"))
library(memga)
memga(recruiting_small, size = 2)
```

### 6. Atualizar

Aumente a versão no `DESCRIPTION` (por exemplo `0.1.1`), faça o commit e o push no `portfolio-ds`. O R-universe percebe sozinho e recompila, geralmente em até uma hora.

## Pontos de atenção

- O README dentro de `mem-ga/r` já mostra essa forma de instalar.
- O R-universe é a **forma rápida**. O CRAN continua sendo o selo que o seu orientador pediu, e os dois podem existir ao mesmo tempo.
- Para citar o pacote em artigos, vale também gerar um DOI no Zenodo (ligando o repositório do GitHub ao Zenodo e criando uma release).
