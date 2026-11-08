# Job Finder

*Read in: [Português](README.md)*

A bot that collects jobs from several sources, sorts them into categories, puts football, the companies you rated well and large companies first, and emails the new ones every day at a scheduled time. Search terms, categories and email text are in Portuguese, since the bot was built for the Brazilian job market.

## How it works

1. **Collects** jobs from eight sources:
   - [Remotar](https://remotar.com.br/): remote jobs in Brazil, read with Playwright.
   - [Gupy](https://portal.gupy.io/): Brazilian jobs, through the portal's public API.
   - LinkedIn: through the public job search, **without logging in**, so the account is never at risk of being banned. It makes only a few searches a day, with pauses in between; if LinkedIn blocks them, the bot carries on with the other sources.
   - Football data companies (Hudl, Genius Sports, Kitman Labs, Sportradar): through the public APIs of their job systems, which list only open jobs.
   - [Jobs In Football](https://jobsinfootball.com/): club jobs worldwide, with Playwright.
   - [Glassdoor](https://www.glassdoor.com.br/): search with the site's remote-work filter, with Playwright. The description snippet on the card feeds the affinity score.
   - [InfoJobs](https://www.infojobs.com.br/): the card says whether the job is on-site, hybrid or remote, with Playwright.
   - [Vagas.com](https://www.vagas.com.br/): the list doesn't say whether a job is remote, so the bot opens the pages of jobs that might fit (up to 40 per run) and reads the work model from the description.

   Indeed is left out: it requires an anti-bot check, which the bot does not bypass.
2. **Classifies** each job by title into a category: Football Analytics, Data Analysis, BI Analyst, Administrative Analyst/Assistant, or Other (Production/Planning Engineering). Jobs outside these, internships, and titles with excluded terms are dropped.
   What the bot drops by title or description, in both emails:
   - **Data science / machine learning** only at entry level (senior data and BI analysts are still kept) (junior, jr, entry, associate or "I"); with no level in the title, it is dropped.
   - **Data engineering** (data engineer, analytics engineer...), football jobs included.
   - **Jobs exclusive to people with disabilities or minorities** (PcD, affirmative positions, women only, Black candidates, LGBT, 50+...). "PcD are welcome" doesn't count as exclusive.
   - **English-language jobs** are kept only if they accept Brazil: those requiring residence or work authorization elsewhere are dropped. Operational roles in English (data entry, data operator, administrative assistant and administrative analyst) are searched on LinkedIn.
3. **Filters by location**:
   - All jobs, football included, must be remote.
   - Football jobs: remote and open to people living in Brazil, or remote and based in Brazil. The bot reads the job description: if it requires residence or work authorization in the US, UK or Europe, the job is dropped; if it mentions Brazil, LATAM or "anywhere", it is kept; if it says nothing, it is kept with a note to check.
4. **Prioritizes** the email: football, then companies you rated "quero" (want) or "quero muito" (really want), then large companies, then everything else, and finally "meh" companies. Companies rated "evitar" (avoid) are left out. Within each block, jobs are grouped by category, newest first.
5. **Enriches** each job:
   - **Affinity** in parentheses after the title, e.g. "(75% de afinidade)": of the tools and techniques the job mentions (SQL, Power BI, Spark, AWS...), how many are in your skills, read from [`gerador-curriculos/base/competencias.yaml`](../gerador-curriculos/base/competencias.yaml). The missing ones are listed below. Jobs with no description (Remotar) or mentioning fewer than 2 items get no %.
   - **One line about the company** below the link: from `empresas.txt` or, if the company isn't there, from the "about" text on its Gupy or LinkedIn page and, last, from Wikipedia. Jobs from LinkedIn also show company size (e.g. "1.001-5.000 funcionários"). Everything is cached so it isn't looked up again.
   - **New companies to rate**: at the end of the email, companies not yet in `empresas.txt`, each as a line ready to paste there.
6. **Remembers** jobs already sent (`vagas_vistas.json`) only to mark new ones with 🆕. The email lists every job still open, so nothing is lost if you skip a day. Jobs from "confidential" companies are dropped. With no jobs at all, no email is sent.

### Your company ratings

[`empresas.txt`](empresas.txt) holds one company per line as `Name | rating | why the company is cool`. Ratings are `quero muito`, `quero`, `ok`, `meh` and `evitar`. Matching ignores case and accents and looks for the whole name in the job's company name.

### What counts as a "large company"

Anything listed in [`empresas_grandes.txt`](empresas_grandes.txt): an editable list, one company per line, built from GPTW Brazil, LinkedIn Top Companies Brazil, the largest companies in Brazil and worldwide, and multinationals that hire remotely in Brazil. Matching ignores case and accents and looks for whole words in the job's company name ("itau" matches "Itaú Unibanco").

### "Perto de casa" (close to home) email

A second email with **on-site and hybrid** jobs in Campos dos Goytacazes, São João da Barra and Macaé (Rio de Janeiro state). The search here is broad: the bot takes every job in those cities from Gupy, InfoJobs, Vagas.com and LinkedIn and filters by title using the lists in [`perto_de_casa.txt`](perto_de_casa.txt):

- **[excluir]** (exclude): operational roles (stock clerk, shelf stocker, machine operator...), trades and licensed professions you don't practice (doctor, pharmacist, dentist, lawyer...).
- **[sempre]** (always): kept even if an excluded term matches (e.g. professor, college level only).
- **[areas]**: a job is kept only if its title has a term from your fields (data, administration, finance, purchasing, logistics, planning, quality, management...).

Jobs are sorted by company and show city, work model (on-site or hybrid), affinity and your company rating, as in the main email. To run only this email: `python job_finder.py --so-perto`.

## Structure

| File | What it does |
|---|---|
| `job_finder.py` | Ties everything together: collect, classify, keep the new ones, send |
| `fontes/` | One module per job source |
| `classificacao.py` | Categories, football, location and priority |
| `empresas.py` | Your company ratings and the one-line description |
| `afinidade.py` | Affinity between your skills and the job |
| `perto_de_casa.py` | Filter and ordering for the close-to-home email |
| `memoria.py` | Jobs already sent |
| `email_vagas.py` | Builds and sends the email |
| `empresas.txt` | Your company ratings |
| `perto_de_casa.txt` | Job titles kept or dropped in the close-to-home email |
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
