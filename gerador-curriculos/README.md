# Gerador de Currículos

*Leia em: [English](README.en.md)*

Mantém toda a minha carreira em uma base única, em arquivos YAML, e gera currículos em PDF em português, inglês e espanhol, em versões por área: dados, varejo e engenharia. Os dados desta pasta são os meus, reais. Só o telefone fica de fora.

Os PDFs gerados estão em [saida/](saida/).

## Por que

Quem mantém vários currículos à mão acaba com versões que se contradizem: um número muda em um arquivo e não no outro, uma tradução fica para trás. Aqui cada fato é escrito uma única vez, com a fonte e o texto nos três idiomas. Cada versão só escolhe quais fatos entram e em que ordem.

## Como rodar

```bash
pip install -r gerar/requirements.txt
python gerar/gerar.py
```

O programa valida a base, monta os documentos, converte para PDF e confere o resultado. A pasta `saida/` só é substituída se tudo passar, e os PDFs anteriores vão para `historico/`.

A conversão usa o Microsoft Word no Windows. Sem o Word, ou em outro sistema, usa o LibreOffice. A paginação do LibreOffice pode ser um pouco diferente, e a conferência de páginas avisa se algum currículo passar do limite.

Para uma vaga específica, crie `versoes/vagas/<nome>.yaml` com `herda: dados` e só os campos que mudam, e rode:

```bash
python gerar/gerar.py --vaga <nome>
```

Para rodar os testes, use `python -m pytest gerar/testes` nesta pasta.

## Como funciona

**`base/`** guarda a carreira:

- `perfil.yaml`: nome, contato, idiomas e produção científica;
- `experiencias.yaml`: cargos e fatos. Cada fato tem `id`, cargo, tipo (`atividade` ou `resultado`), fonte e texto em `pt`, `en` e `es`;
- `formacao.yaml`, `publicacoes.yaml`, `projetos.yaml` e `competencias.yaml`;
- `pendencias.yaml`: fatos ainda não confirmados, que não podem entrar em nenhuma versão;
- `perfil.local.yaml`: contato que fica só na minha máquina, como o telefone. Ele não está no repositório; sem ele, o currículo sai sem telefone.

**`versoes/`** define cada currículo: título, resumo, seções, competências, cursos, projetos e os fatos, em ordem. O resumo cita fatos pelo `id`, como `{pricing-margem}`, então um resultado é escrito uma vez só e aparece igual no resumo e na experiência.

**`gerar/`** faz o trabalho:

- `base.py` lê e valida: fonte em todo fato, tradução nos três idiomas, `id` sem repetição e nenhuma versão citando algo inexistente ou pendente;
- `documento.py` monta o documento em uma coluna, sem tabelas, imagens nem cabeçalho, para os sistemas de triagem (ATS) lerem bem;
- `checar.py` confere cada PDF: no máximo 2 páginas, e todo número impresso precisa existir na base;
- `arquivar.py` troca a `saida/` de uma vez e devolve os PDFs antigos se algo falhar no meio;
- `gerar.py` junta tudo.

## Como foi feito

O projeto foi desenvolvido com IA (Claude Code). Primeiro, uma especificação escrita e aprovada, depois um plano de implementação, testes escritos antes do código e revisão do resultado. No dia a dia funciona como uma conversa: conto uma novidade da carreira, ela é registrada na base com a fonte, e os currículos são gerados de novo.
