# Job Finder

*Read in: [Português](README.md)*

A bot that looks for remote data analysis jobs and emails the most recent ones every day at a scheduled time.

The search runs on [Remotar](https://remotar.com.br/), a Brazilian remote job board, because other platforms don't allow this kind of automation and may ban the account. The search terms, filters, and email text are in Portuguese, since the bot was built for the Brazilian job market.

## How it works

1. Searches Remotar for each keyword using Playwright.
2. Discards internships, hybrid or on-site jobs, and titles containing excluded terms.
3. Removes duplicates and sorts the jobs from newest to oldest.
4. Sends the list as an HTML email through Gmail.

## How to run

Install the dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

Copy `config.example.txt` to `~\Desktop\aux portfolio\job finder\config_vagas.txt` and fill in your details. This file stays outside the repository so credentials never reach GitHub. The `SENHA_APP` field takes a Google app password, not your regular account password.

Then run:

```bash
python job_finder.py
```

To run it every day, schedule `rodar_bot.bat` in Windows Task Scheduler.

## Customization

Keywords are in `PERFIL_SERGIO`, and excluded terms are in `EXCLUIR_NO_TITULO` and `EXCLUIR_NO_CARD`, all in `job_finder.py`.

## Limitations

The bot doesn't keep track of jobs it has already sent, so the same job may appear in more than one email.
