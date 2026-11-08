# Job Finder

*Read in: [Português](README.md)*

A bot that collects jobs from several sources, sorts them into categories, puts football, the companies you rated well and large companies first, and emails the new ones every day at a scheduled time. Search terms, categories and email text are in Portuguese, since the bot was built for the Brazilian job market.

## How it works

1. **Collects** jobs from five sources:
   - [Remotar](https://remotar.com.br/): remote jobs in Brazil, read with Playwright.
   - [Gupy](https://portal.gupy.io/): Brazilian jobs, through the portal's public API.
   - LinkedIn: through the public job search, **without logging in**, so the account is never at risk of being banned. It makes only a few searches a day, with pauses in between; if LinkedIn blocks them, the bot carries on with the other sources.
   - Football data companies (Hudl, Genius Sports, Kitman Labs, Sportradar): through the public APIs of their job systems, which list only open jobs.
   - [Jobs In Football](https://jobsinfootball.com/): club jobs worldwide, with Playwright.
2. **Classifies** each job by title into a category: Football Analytics, Data Analysis, BI Analyst, Administrative Analyst/Assistant, or Other (Production/Planning Engineering). Jobs outside these, internships, and titles with excluded terms are dropped.
3. **Filters by location**:
   - General jobs: remote only.
   - Football jobs: in Brazil (on-site included) or remote and open to people living in Brazil. The bot reads the job description: if it requires residence or work authorization in the US, UK or Europe, the job is dropped; if it mentions Brazil, LATAM or "anywhere", it is kept; if it says nothing, it is kept with a note to check.
4. **Prioritizes** the email: football, then companies you rated "quero" (want) or "quero muito" (really want), then large companies, then everything else, and finally "meh" companies. Companies rated "evitar" (avoid) are left out. Within each block, jobs are grouped by category, newest first.
5. **Enriches** each job:
   - **Affinity** in parentheses after the title, e.g. "(75% de afinidade)": of the tools and techniques the job mentions (SQL, Power BI, Spark, AWS...), how many are in your skills, read from [`gerador-curriculos/base/competencias.yaml`](../gerador-curriculos/base/competencias.yaml). The missing ones are listed below. Jobs with no description (Remotar) or mentioning fewer than 2 items get no %.
   - **One line about the company** below the link: from `empresas.txt` or, if the company isn't there, from Wikipedia (cached so it isn't looked up again).
   - **New companies to rate**: at the end of the email, companies not yet in `empresas.txt`, each as a line ready to paste there.
6. **Remembers** jobs already sent (`vagas_vistas.json`), so each job arrives only once. If nothing is new, no email is sent.

### Your company ratings

[`empresas.txt`](empresas.txt) holds one company per line as `Name | rating | why the company is cool`. Ratings are `quero muito`, `quero`, `ok`, `meh` and `evitar`. Matching ignores case and accents and looks for the whole name in the job's company name.

### What counts as a "large company"

Anything listed in [`empresas_grandes.txt`](empresas_grandes.txt): an editable list, one company per line, built from GPTW Brazil, LinkedIn Top Companies Brazil, the largest companies in Brazil and worldwide, and multinationals that hire remotely in Brazil. Matching ignores case and accents and looks for whole words in the job's company name ("itau" matches "Itaú Unibanco").

## Structure

| File | What it does |
|---|---|
| `job_finder.py` | Ties everything together: collect, classify, keep the new ones, send |
| `fontes/` | One module per job source |
| `classificacao.py` | Categories, football, location and priority |
| `empresas.py` | Your company ratings and the one-line description |
| `afinidade.py` | Affinity between your skills and the job |
| `memoria.py` | Jobs already sent |
| `email_vagas.py` | Builds and sends the email |
| `empresas.txt` | Your company ratings |
| `empresas_grandes.txt` | List of large companies |
| `tests/` | Classification tests |

## How to run

Install the dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

Copy `config.example.txt` to `~\Desktop\aux portfolio\job finder\config_vagas.txt` and fill in your details. This file stays outside the repository so credentials never reach GitHub. The `SENHA_APP` field takes a Google app password, not your regular account password. The memory of sent jobs is kept in the same folder.

To test without sending email or saving the memory (it saves a preview to `previa_email.html`, in the same folder as the config):

```bash
python job_finder.py --sem-email
```

To run it for real:

```bash
python job_finder.py
```

To run it every day, schedule `rodar_bot.bat` in Windows Task Scheduler. Tests run with `python -m pytest tests`.

## Customization

- Search terms for each source: at the top of `job_finder.py`.
- Categories, excluded terms and location rules: in `classificacao.py`.
- Football companies monitored: in `fontes/empresas_futebol.py`.
- Large companies: in `empresas_grandes.txt`.
- Your rating of each company: in `empresas.txt`.
- Tools counted for affinity: in `afinidade.py`.

## Limitations

- LinkedIn may block the public search on some days. When that happens, its jobs wait for the next run.
- The location rule for football jobs reads the description for keywords, so it can get unclear descriptions wrong. That is why remote jobs with no country stated come marked for checking.
- Affinity compares words and doesn't understand context: a job listing AWS as "nice to have" counts the same as one that requires it. It's a quick guide, not a score.
- Websites change: if a source changes its layout or API, it stops returning jobs until the code is updated. The other sources keep working.
