# Como submeter o memga ao CRAN

Esta pasta (`dev/`) não entra no pacote. Ela fica aqui só para você.

## 1. O que preencher antes (só você sabe)

No arquivo `DESCRIPTION`:

- **Nome completo** em `Authors@R` (hoje está só "Sérgio Salles").
- **E-mail do mantenedor.** Hoje está `maintainer@example.com`, que não funciona. O CRAN manda um link de confirmação para esse e-mail, e ele fica público na página do pacote. Use um e-mail que você vai manter por anos.
- **ORCID** (opcional, mas comum): acrescente `comment = c(ORCID = "0000-0000-0000-0000")` dentro de `person(...)`.
- **Coautoria do seu orientador.** O método é dele. Se ele aceitar, entra em `Authors@R` com `role = "aut"` (ou `"ctb"`, contribuidor). Só coloque o nome dele com o consentimento dele. O texto para pedir está no final deste arquivo.
- **Licença.** Está MIT (`License: MIT + file LICENSE`, com seu nome no arquivo `LICENSE`). Se preferir outra, como GPL-3, troque no `DESCRIPTION`. Ela precisa combinar com a da tese e dos dados, se houver restrição.

Depois de editar, gere a documentação de novo (`roxygen2::roxygenise()`) e rode a verificação local (passo 2).

## 2. Verificação local

Na pasta `mem-ga/r`, em um terminal:

```bash
R CMD build .
R CMD check --as-cran memga_0.1.0.tar.gz
```

O objetivo é `Status: OK`, ou só uma NOTE sobre "New submission", que é normal.
O `--as-cran` completo também confere sua URL e seu e-mail pela internet.
No Windows, a parte do manual em PDF precisa de LaTeX (MiKTeX); sem ele, use `--no-manual` só para testar.

## 3. Verificação em outros sistemas (o CRAN pede)

O CRAN roda em Windows, Linux e Mac. Teste antes:

1. **win-builder:** envie o arquivo `memga_0.1.0.tar.gz` em <https://win-builder.r-project.org/upload.aspx>, escolhendo R-release e R-devel. O resultado chega por e-mail, para o e-mail do mantenedor.
2. **R-hub:** com o pacote `rhub`, `rhub::rhub_check()` roda em Linux, Mac e Windows pelo GitHub Actions (precisa de uma conta GitHub e de um token).

Anote os resultados no `cran-comments.md`, na seção "Test environments".

## 4. Submeter

1. Acesse <https://cran.r-project.org/submit.html>.
2. Preencha seu nome e o e-mail do mantenedor (os mesmos do `DESCRIPTION`).
3. Envie o arquivo `memga_0.1.0.tar.gz`.
4. Marque as caixas de confirmação.
5. No campo de comentário (Optional comment), cole o texto abaixo.
6. O CRAN manda um e-mail com um link para confirmar. **Sem clicar no link, a submissão não vale.**
7. Depois a revisão é feita por pessoas. Pode vir pedido de ajuste.

### Texto para o campo de comentário (em inglês, como o CRAN espera)

```
This is a new submission.

memga implements the Multiple Choice Method (da Hora and Costa, 2015,
doi:10.1590/0103-6513.084812) for selecting a set of alternatives that
complement each other, with an exhaustive search and a genetic algorithm.

R CMD check --as-cran gives 0 errors and 0 warnings on win-builder
(R-release and R-devel). The only note is "New submission", plus "Costa" and
"da" flagged as possible misspellings: they are parts of the names of the
authors of the cited paper (see cran-comments.md).
The package has no compiled code. Tests that take about a minute are skipped
on CRAN, and the examples run in a fraction of a second.
```

O texto fala só do win-builder porque o R-hub não foi rodado. Se você rodar o R-hub, acrescente-o aqui e no `cran-comments.md`.

### Se pedirem ajustes

Responda no mesmo e-mail, corrija, aumente a versão (`0.1.1`), acrescente em `NEWS.md` e reenvie com este comentário:

```
Thank you for the review. I have made the changes you asked for:
- <o que mudou, uma linha para cada ponto>

This is a resubmission.
```

Depois de aceito, o CRAN pede um intervalo de uns 1 a 2 meses entre atualizações. Não reenvie por detalhes pequenos.

## 5. Antes de apertar o botão: lista final

- [ ] Nome completo, e-mail real e licença conferidos no `DESCRIPTION`
- [ ] Coautoria do orientador decidida (com o consentimento dele)
- [ ] `R CMD check --as-cran` com Status OK
- [x] win-builder rodado em R-release e R-devel (1 NOTE: "New submission" e os nomes dos autores), resultados no `cran-comments.md`
- [ ] R-hub (opcional, não rodado)
- [ ] `NEWS.md` com a versão
- [ ] Versão do `DESCRIPTION` é a que vai ser enviada (`0.1.0`)

## 6. Mensagem para o orientador (opcional)

> Professor, estou transformando o MEM e o MEM-GA em um pacote de R para
> subir no CRAN, como o senhor sugeriu. O pacote chama-se memga e implementa o
> método do artigo da Hora e Costa (2015). Gostaria de saber se o senhor quer
> constar como coautor do pacote, ou se prefere só ser citado como origem do
> método. Posso enviar o texto do pacote e a página dele antes da submissão.
> Obrigado!
