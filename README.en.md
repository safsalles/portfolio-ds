# portfolio-ds

*Read in: [Português](README.md)*

A portfolio of new and older projects that apply Data Science and automation techniques to solve problems.

## Projects

| Project | What it does | Technologies |
| --- | --- | --- |
| [Job Finder](job-finder/README.en.md) | Searches 8 sources every day (Remotar, Gupy, LinkedIn, Glassdoor, InfoJobs, Vagas.com, football data companies and Jobs In Football), sorts jobs by category and emails them with football and favorite companies first, résumé affinity and new jobs flagged | Python, Playwright, APIs, SMTP, pytest |
| [mem-ga](mem-ga/README.en.md) | The Multiple Choice Method as a package for Python ([PyPI](https://pypi.org/project/memga/)), R ([R-universe](https://safsalles.r-universe.dev/memga)) and MATLAB ([File Exchange](https://www.mathworks.com/matlabcentral/fileexchange/185196-memga-multiple-choice-method-for-selecting-sets-of-alternatives)), with two scoring rules, exhaustive search and a genetic algorithm, two fictional examples and a [DOI](https://doi.org/10.5281/zenodo.24062574) | Python, R, MATLAB, genetic algorithm |
| [football-analytics](football-analytics/README.en.md) | Lineup (MEM-GA) and signings (GA-MEM) with 2017 Brazilian Championship data, from my master's dissertation, using mem-ga | Python, NumPy, genetic algorithm |
| [Résumé Generator](gerador-curriculos/README.en.md) | Generates PDF résumés in 3 languages and role-specific versions from a single database of my career, with validation and automatic checks | Python, YAML, python-docx, pytest, Claude Code |
| [Flight Price Tracker](viagem-milhas/README.en.md) | Checks every day the price of the trip you configure (destinations, dates, passengers, baggage and minimum layover), including open-jaw returns; keeps the price history, alerts on price drops or cheap miles promotions and compares cash and miles; has a browser interface that saves every consultation to review the next day | Python, SerpApi, Streamlit, pytest, Windows Task Scheduler, Claude Code |
| [Workforce Staffing](dimensionamento-equipe/README.en.md) | Workforce Management: aggregates 2 million NYC 311 calls by hour, forecasts demand, sizes the team (Erlang C) and simulates the queue with a choice of distributions, fitted to real service times (Technion data), in an app that shows the effect of hiring or letting people go. Team and assumptions are fictional | Python, PySpark, time series, Erlang C, simulation, Streamlit, pytest, Claude Code |
