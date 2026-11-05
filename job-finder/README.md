# Job Finder

*Leia em: [English](README.en.md)*

Bot que procura vagas remotas relacionadas a análise de dados e envia as mais recentes por e-mail, todos os dias, em um horário agendado.

A busca é feita no [Remotar](https://remotar.com.br/), porque outras plataformas não permitem esse tipo de automação e a conta pode ser banida.

## Como funciona

1. Pesquisa cada palavra-chave no Remotar com o Playwright.
2. Descarta estágios, vagas híbridas ou presenciais e títulos com termos de exclusão.
3. Remove duplicadas e ordena das mais recentes para as mais antigas.
4. Envia a lista por e-mail em HTML, pelo Gmail.

## Como rodar

Instale as dependências:

```bash
pip install -r requirements.txt
playwright install chromium
```

Copie `config.example.txt` para `~\Desktop\aux portfolio\job finder\config_vagas.txt` e preencha com os seus dados. Esse arquivo fica fora do repositório para as credenciais não irem para o GitHub. O campo `SENHA_APP` usa uma senha de app do Google, não a senha normal da conta.

Depois, execute:

```bash
python job_finder.py
```

Para rodar todo dia, agende o `rodar_bot.bat` no Agendador de Tarefas do Windows.

## Personalização

As palavras-chave ficam em `PERFIL_SERGIO` e os termos de exclusão em `EXCLUIR_NO_TITULO` e `EXCLUIR_NO_CARD`, todos em `job_finder.py`.

## Limitações

O bot não guarda as vagas já enviadas, então a mesma vaga pode aparecer em mais de um e-mail.
