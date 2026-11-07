# Résumé Generator

*Read in: [Português](README.md)*

Keeps my whole career in a single database of YAML files and generates PDF résumés in Portuguese, English and Spanish, in role-specific versions: data, retail and engineering. The data in this folder is mine and real. Only the phone number is left out.

The generated PDFs are in [saida/](saida/).

## Why

Keeping several résumés by hand leads to versions that contradict each other: a number changes in one file but not in another, a translation falls behind. Here each fact is written only once, with its source and its text in all three languages. Each version only chooses which facts to include and in what order.

## How to run

```bash
pip install -r gerar/requirements.txt
python gerar/gerar.py
```

The program validates the database, builds the documents, converts them to PDF and checks the result. The `saida/` folder is only replaced if everything passes, and the previous PDFs move to `historico/`.

Conversion uses Microsoft Word on Windows. Without Word, or on another system, it uses LibreOffice. LibreOffice may paginate slightly differently, and the page check warns if any résumé goes over the limit.

For a specific job posting, create `versoes/vagas/<name>.yaml` with `herda: dados` and only the fields that change, then run:

```bash
python gerar/gerar.py --vaga <name>
```

To run the tests, use `python -m pytest gerar/testes` in this folder.

## How it works

The code and data are in Portuguese, so folder and field names are kept as they are.

**`base/`** holds the career:

- `perfil.yaml`: name, contact, languages and research output;
- `experiencias.yaml`: roles and facts. Each fact has an `id`, role, type (`atividade` for activity or `resultado` for result), source and text in `pt`, `en` and `es`;
- `formacao.yaml` (education), `publicacoes.yaml` (publications), `projetos.yaml` (projects) and `competencias.yaml` (skills);
- `pendencias.yaml`: facts not yet confirmed, which cannot enter any version;
- `perfil.local.yaml`: contact details kept only on my machine, such as the phone number. It is not in the repository; without it, the résumé has no phone number.

**`versoes/`** defines each résumé: title, summary, sections, skills, courses, projects and the facts, in order. The summary cites facts by `id`, such as `{pricing-margem}`, so a result is written once and reads the same in the summary and in the experience section.

**`gerar/`** does the work:

- `base.py` reads and validates: a source on every fact, text in all three languages, no repeated `id`, and no version citing something missing or pending;
- `documento.py` builds a single-column document with no tables, images or header, so applicant tracking systems (ATS) read it well;
- `checar.py` checks each PDF: at most 2 pages, and every printed number must exist in the database;
- `arquivar.py` swaps `saida/` in one go and restores the old PDFs if something fails midway;
- `gerar.py` ties it all together.

## How it was built

The project was built with AI (Claude Code). First a written and approved specification, then an implementation plan, tests written before the code, and a review of the result. Day to day it works as a conversation: I describe something new in my career, it is recorded in the database with its source, and the résumés are generated again.
