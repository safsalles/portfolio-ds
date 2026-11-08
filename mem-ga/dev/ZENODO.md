# Como gerar o DOI do memga no Zenodo

O Zenodo é um repositório aberto, do CERN, que dá um **DOI** a qualquer arquivo de pesquisa, inclusive software. Com o DOI, o `memga` ganha uma citação formal e permanente.

Fazemos o **envio manual** (e não pela ligação com o GitHub), porque o `memga` mora numa subpasta do `portfolio-ds`. A ligação com o GitHub arquivaria o portfólio inteiro a cada release.

## O que é permanente
**Um registro publicado no Zenodo não pode ser apagado**: os arquivos e o DOI ficam. Dá para editar os dados do registro depois, mas não trocar os arquivos da versão publicada. Para corrigir um arquivo, publica-se uma nova versão. Por isso vale conferir tudo antes de clicar em *Publish*.

Opcional: o <https://sandbox.zenodo.org> é um Zenodo de ensaio, com os mesmos formulários e DOIs falsos, para você treinar antes.

## 1. Conta
Entre em <https://zenodo.org/signup/>. O jeito mais prático é **Log in with GitHub** ou *with ORCID*. Se tiver ORCID, é uma boa hora de ligar.

## 2. Novo envio
1. Clique em **Upload** (ou *New upload*), no topo.
2. Envie o arquivo `memga-1.2.0-source.zip`.

## 3. Dados do registro (campos, em inglês)
- **Resource type:** `Software`
- **Title:** `memga: Multiple Choice Method for selecting sets of alternatives`
- **Publication date:** a data de hoje
- **Version:** `1.2.0`
- **Creators:**
  1. `Salles, Sérgio Augusto Faria` (afiliação e ORCID, se quiser)
  2. `da Hora, Henrique Rego Monteiro`
- **Description:**

  > Selects a set of alternatives that complement each other, instead of ranking the alternatives one by one. Implements the Multiple Choice Method (MEM) proposed in da Hora and Costa (2015), and an adaptation for larger problems that scores criteria in pairs. The best set is found by exhaustive search or by a genetic algorithm, with optional quotas per group. Available for Python (PyPI), R (R-universe, submitted to CRAN), and MATLAB / GNU Octave (File Exchange). Version 1.2.0 of the Python and MATLAB packages and version 0.1.0 of the R package.

- **License:** `MIT License`
- **Keywords:** `multicriteria decision making`, `genetic algorithm`, `selection of sets`, `Python`, `R`, `MATLAB`
- **Related works** (opcional, mas ajuda a ligar tudo):
  - `https://pypi.org/project/memga/`, tipo *Is supplemented by* / ou *Is alternate identifier*, recurso *Software*
  - `https://safsalles.r-universe.dev/memga`, mesma relação
  - `https://doi.org/10.1590/0103-6513.084812`, relação *Is derived from*, recurso *Publication / Article*
- **Funding, Subjects, etc.:** deixe em branco.

## 4. Publicar
Revise tudo e clique em **Publish**. O Zenodo mostra o **DOI** (algo como `10.5281/zenodo.1234567`) e dois números:
- o **DOI da versão** (aponta para esse zip);
- o **DOI do conceito** (aponta sempre para a versão mais recente). **Use este** nas citações do projeto.

## 5. Depois
Me mande o DOI do conceito. Eu coloco nos READMEs, no `CITATION.cff` e nas próximas versões dos pacotes (PyPI, R e MATLAB).

Para uma versão nova do `memga` no futuro: no registro, clique em **New version**, envie o zip novo e atualize o campo *Version*.
