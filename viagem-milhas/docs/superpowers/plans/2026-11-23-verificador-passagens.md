# Verificador de passagens e milhas — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Um programa Python que, todo dia, consulta o preço do trajeto aberto GIG→BUD / BER→GIG, aplica as regras de escala do Sérgio, guarda o histórico, avisa quando o preço cai e quando surge promoção de milhas barata.

**Architecture:** Pacote `verificador` com uma peça por responsabilidade (config, regras, coleta, histórico, alertas, promoções, calculadora) e um `run_daily` que as encadeia. Roda pelo Agendador de Tarefas do Windows, sem o Claude. Dados em CSV/JSON na própria pasta.

**Tech Stack:** Python 3.11+, `requests`, `feedparser`, `pytest`, `tomllib` (padrão), SerpApi (Google Voos), PowerShell para notificação e agenda.

**Spec:** `viagem-milhas/docs/2026-11-23-verificador-passagens-design.md`

## Global Constraints

- Trajeto fixo: ida `GIG`→`BUD` em `2027-07-10`; volta `BER`→`GIG` em `2027-07-22`. **A volta NÃO sai de Budapeste.**
- 2 adultos, econômica, moeda `BRL`.
- Regras: toda escala com **no mínimo 240 minutos**; **nenhuma escala em aeroporto do Brasil** (lista em config: `GIG, GRU, VCP, CGH, SDU, BSB, CNF, SSA, REC, FOR`).
- Referência de hoje (para os testes): KLM Light, **R$ 19.152** total; **502.000 milhas** (230.000 ida + 272.000 volta); equilíbrio ≈ **R$ 32,17** o milheiro com **R$ 3.000** de taxas (taxas ainda não confirmadas).
- Limites padrão: queda de **5%**, valor-alvo **R$ 18.000**; milheiro: Flying Blue/TAP/Livelo **< R$ 35**, Smiles **< R$ 12**.
- 1 coleta por dia, de manhã (08:00). Plano gratuito SerpApi: 250 consultas/mês.
- A chave da API vem só da variável de ambiente `SERPAPI_KEY`; nunca em arquivo do projeto.
- Windows 11; sem banco de dados (CSV); sem CAPTCHA/burla de bloqueio.

## Review Focus

1. **API devolve lista vazia ou erro (429, cota, rede):** não gravar preço 0 nem apagar histórico; registrar linha `status=error` e avisar a falha.
2. **Escala sem duração informada:** tratar como **não conforme** (conservador) e contar quantas foram descartadas por isso, para o Sérgio saber.
3. **Primeira execução (sem histórico):** não disparar "queda de preço" falsa; só avisar se abaixo do valor-alvo.
4. **Rodar duas vezes no mesmo dia:** a linha do dia é substituída, sem duplicar, e o aviso não se repete.
5. **Post de blog com vários "R$" no texto:** só extrair milheiro colado a "milheiro"; sem confiança, não avisar (melhor calar que chorar lobo).

---

## Estrutura de arquivos

```
viagem-milhas/
  config.toml                      # trajeto, regras, limites, feeds
  requirements.txt
  src/verificador/__init__.py
  src/verificador/models.py        # Layover, Leg, Offer
  src/verificador/config.py        # load_config
  src/verificador/rules.py         # is_compliant, cheapest_compliant
  src/verificador/calculator.py    # breakeven_milheiro, compare
  src/verificador/history.py       # upsert_record, last_price
  src/verificador/collector.py     # fetch_offers, parse_offers
  src/verificador/alerts.py        # price_alerts, notify
  src/verificador/promos.py        # extract_milheiro, find_promos, fetch_feed
  src/verificador/run_daily.py     # main
  scripts/register_task.ps1       # Agendador do Windows
  tests/ (um arquivo por módulo) + tests/fixtures/
  data/history.csv, data/seen_promos.json, data/alerts.log   (gerados)
  README.md
```

---

### Task 1: Esqueleto, configuração e modelos

**Files:**
- Create: `config.toml`, `requirements.txt`, `README.md`, `src/verificador/__init__.py`, `src/verificador/models.py`, `src/verificador/config.py`, `tests/test_config.py`, `.gitignore` (ignora `data/` e `.env`)

**Interfaces:**
- Produces (`models.py`): `Layover(airport: str, minutes: int | None)`; `Leg(origin: str, destination: str, airlines: tuple[str, ...], layovers: tuple[Layover, ...])`; `Offer(total_price_brl: float, outbound: Leg, inbound: Leg, fare: str | None)` — todos `@dataclass(frozen=True)`.
- Produces (`config.py`): `Config` (dataclass com `trip`, `rules`, `alerts`, `promos`, `paths`) e `load_config(path: str = "config.toml") -> Config`.

- [ ] **Step 1: Write the failing test** `test_load_config_has_spec_values`: carrega `config.toml` e afirma `cfg.trip.outbound == ("GIG","BUD","2027-07-10")`, `cfg.trip.inbound == ("BER","GIG","2027-07-22")`, `cfg.trip.adults == 2`, `cfg.rules.min_layover_minutes == 240`, `"GRU" in cfg.rules.brazil_airports`, `cfg.alerts.drop_pct == 5.0`, `cfg.alerts.target_brl == 18000`, `cfg.promos.max_milheiro["smiles"] == 12`.
- [ ] **Step 2: Run** `python -m pytest tests/test_config.py -v` → FAIL (módulo não existe).
- [ ] **Step 3: Implement** `config.toml`, `models.py`, `config.py` (usa `tomllib`; converte listas em tuplas/frozenset). Inclui no `config.toml` os feeds `https://passageirodeprimeira.com/feed/` e `https://pontospravoar.com/feed/` e as palavras-chave `flying blue, smiles, livelo, tap, milheiro, bônus`.
- [ ] **Step 4: Run** o teste → PASS. Rodar `python -m pytest -q` → tudo verde.
- [ ] **Step 5: Commit** (`git init` na pasta `viagem-milhas` se ainda não houver repositório): `git add . && git commit -m "feat: esqueleto, config e modelos"`.

---

### Task 2: Filtro de regras

**Files:**
- Create: `src/verificador/rules.py`, `tests/test_rules.py`

**Interfaces:**
- Consumes: `Offer`, `Leg`, `Layover` (Task 1); `Config.rules`.
- Produces: `is_compliant(offer: Offer, min_layover_minutes: int, brazil_airports: frozenset[str]) -> bool` e `cheapest_compliant(offers: list[Offer], min_layover_minutes: int, brazil_airports: frozenset[str]) -> tuple[Offer | None, int]` (devolve a oferta e quantas foram descartadas por **escala sem duração**).

- [ ] **Step 1: Write the failing tests** (helper `make_offer(price, out_layovers, in_layovers)`):
  - `test_rejects_layover_under_240`: escala de 239 min na ida → `False`; 240 min → `True`.
  - `test_rejects_brazil_layover`: escala `GRU` em qualquer perna → `False`.
  - `test_rejects_unknown_duration`: `Layover("AMS", None)` → `False`, e `cheapest_compliant` devolve contagem 1.
  - `test_cheapest_compliant_picks_lowest_price_among_passing`: três ofertas, a mais barata reprovada, devolve a segunda mais barata (reproduz o caso real: 17.243 reprovada, 19.152 aprovada).
  - `test_returns_none_when_all_fail`.
- [ ] **Step 2: Run** `python -m pytest tests/test_rules.py -v` → FAIL.
- [ ] **Step 3: Implement** as duas funções em `rules.py` (sem escala = conforme).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: filtro de regras de escala`.

---

### Task 3: Calculadora dinheiro × milhas

**Files:**
- Create: `src/verificador/calculator.py`, `tests/test_calculator.py`

**Interfaces:**
- Produces: `breakeven_milheiro(cash_brl: float, miles: int, taxes_brl: float) -> float`; `compare(cash_brl: float, miles: int, milheiro_brl: float, taxes_brl: float) -> Comparison` com `Comparison(miles_cost_brl: float, cash_brl: float, miles_win: bool, savings_brl: float)` (frozen dataclass; `savings_brl` positivo = milhas ganham).
- Chamada como linha de comando: `python -m verificador.calculator --cash 19152 --miles 502000 --milheiro 30 --taxes 3000` imprime o resultado.

- [ ] **Step 1: Write the failing tests:** `test_breakeven_matches_reference` → `breakeven_milheiro(19152, 502000, 3000) == pytest.approx(32.17, abs=0.01)`; `test_compare_milheiro_100_loses` (milheiro 100 → `miles_win is False`, `miles_cost_brl == 53200`); `test_compare_milheiro_30_wins` (`miles_win is True`, `savings_brl == pytest.approx(19152 - (502*30+3000))`); `test_miles_zero_raises_valueerror`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (custo = `miles/1000*milheiro + taxes`; `miles <= 0` → `ValueError`) e o `__main__` com `argparse`.
- [ ] **Step 4: Run** testes → PASS; rodar o comando de linha com os valores acima e conferir a saída "milhas ganham".
- [ ] **Step 5: Commit** `feat: calculadora dinheiro x milhas`.

---

### Task 4: Histórico em CSV

**Files:**
- Create: `src/verificador/history.py`, `tests/test_history.py`

**Interfaces:**
- Produces: `HistoryRecord(date: str, total_price_brl: float | None, airlines: str, layovers: str, fare: str | None, status: str)` (frozen; `status` ∈ `ok|error|empty`); `upsert_record(path: str, record: HistoryRecord) -> None` (substitui a linha da mesma `date`; cria arquivo e cabeçalho se não existir); `last_price(path: str, before_date: str) -> float | None` (último `ok` com data **anterior** a `before_date`).

- [ ] **Step 1: Write the failing tests:** `test_upsert_creates_file_with_header`; `test_upsert_same_date_replaces_not_duplicates` (duas gravações do mesmo dia → 1 linha com o valor novo); `test_last_price_ignores_error_rows`; `test_last_price_none_on_first_run` (arquivo ausente → `None`). Usar `tmp_path`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** com `csv` da biblioteca padrão; ordenar por data ao regravar.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: historico csv`.

---

### Task 5: Validação da SerpApi e coletor (decisão no meio)

**Files:**
- Create: `scripts/spike_serpapi.py`, `docs/spike-serpapi.md`, `tests/fixtures/serpapi_open_jaw.json`, `src/verificador/collector.py`, `tests/test_collector.py`

**Interfaces:**
- Consumes: modelos (Task 1).
- Produces: `parse_offers(payload: dict) -> list[Offer]` (função pura, testada contra a fixture) e `fetch_offers(cfg: Config, api_key: str) -> list[Offer]` (faz a(s) chamada(s) HTTP e devolve as ofertas; levanta `CollectorError(Exception)` em HTTP ≥ 400, JSON com campo `error` ou cota esgotada).

- [ ] **Step 1 (manual, precisa do Sérgio):** o Sérgio cria conta gratuita na SerpApi e define `setx SERPAPI_KEY "<chave>"` (a chave não vai para o repositório). Conferir o plano gratuito e o suporte a multi-trechos na página oficial de preços/documentação do Google Flights da SerpApi.
- [ ] **Step 2: Spike.** `scripts/spike_serpapi.py` faz UMA busca real do trajeto open-jaw (engine Google Flights, tipo multi-city, `GIG→BUD` 2027-07-10 e `BER→GIG` 2027-07-22, 2 adultos, `currency=BRL`) e grava a resposta crua em `tests/fixtures/serpapi_open_jaw.json`. Anotar em `docs/spike-serpapi.md`: (a) o preço total vem direto ou exige chamada encadeada por trecho? (b) vem a duração de cada escala? (c) quantas consultas por dia isso consome?
- [ ] **Step 3: DECISÃO.** Se (a) exigir chamadas encadeadas, o coletor faz uma chamada por trecho (2/dia, ~60/mês, dentro do gratuito). Se a SerpApi **não** devolver o trajeto aberto, parar e voltar ao Sérgio com o plano reserva (Duffel) antes de seguir.
- [ ] **Step 4: Write the failing test** `test_parse_offers_from_fixture`: afirma que há ≥ 1 oferta, que cada `Offer.inbound.origin == "BER"` e `outbound.origin == "GIG"`, que `total_price_brl > 0`, e que escalas com duração ausente viram `Layover(airport, None)`. Mais `test_parse_offers_empty_payload_returns_empty_list` e `test_fetch_offers_raises_on_api_error_field` (HTTP simulado com `monkeypatch`).
- [ ] **Step 5: Run** `python -m pytest tests/test_collector.py -v` → FAIL.
- [ ] **Step 6: Implement** `parse_offers` e `fetch_offers` (`requests`, timeout 30 s, sem imprimir a chave em logs).
- [ ] **Step 7: Run** → PASS.
- [ ] **Step 8: Commit** `feat: coletor serpapi + fixture real`.

---

### Task 6: Alertas de preço e notificação

**Files:**
- Create: `src/verificador/alerts.py`, `tests/test_alerts.py`

**Interfaces:**
- Consumes: `Config.alerts` (Task 1).
- Produces: `price_alerts(previous: float | None, current: float, drop_pct: float, target_brl: float) -> list[str]` (mensagens em português); `notify(title: str, message: str, log_path: str) -> None` (sempre acrescenta em `log_path`; também tenta notificação do Windows via PowerShell e **não levanta exceção** se ela falhar).

- [ ] **Step 1: Write the failing tests:** `test_drop_of_5_percent_alerts` (19152 → 18194 gera 1 mensagem de queda); `test_drop_of_4_percent_is_silent`; `test_below_target_alerts_even_on_first_run` (`previous=None`, `current=17900`); `test_first_run_above_target_is_silent` (`previous=None`, `current=19152` → lista vazia); `test_increase_is_silent`; `test_notify_writes_log_even_if_toast_fails` (`monkeypatch` do subprocess para lançar erro; conferir que o log tem a linha).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Notificação via `subprocess.run(["powershell", "-NoProfile", "-Command", ...])` com balão do `System.Windows.Forms.NotifyIcon`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: alertas de preco`.

---

### Task 7: Vigia de promoções (feeds de blogs)

**Files:**
- Create: `src/verificador/promos.py`, `tests/test_promos.py`, `tests/fixtures/feed_sample.xml`

**Interfaces:**
- Produces: `extract_milheiro(text: str) -> float | None` (só aceita valor colado a "milheiro", ex.: `"milheiro a R$ 29,50"`, `"R$ 30,10 o milheiro"`); `Promo(program: str, title: str, link: str, milheiro_brl: float)` (frozen); `find_promos(entries: list[dict], keywords: list[str], max_milheiro: dict[str, float], seen: set[str]) -> list[Promo]` (cada entrada tem `title`, `summary`, `link`; devolve só as que citam um programa conhecido, têm milheiro extraído **menor que o limite do programa** e `link` ainda não visto); `fetch_feed(url: str) -> list[dict]` (via `feedparser`); `load_seen(path)`/`save_seen(path, seen)`.

- [ ] **Step 1: Write the failing tests:** `test_extract_milheiro_variants` (ambos os formatos acima → 29.5 e 30.1); `test_extract_ignores_other_prices` (`"Passagem por R$ 5.192 ... milheiro a R$ 68"` → 68.0, não 5192); `test_extract_none_when_no_milheiro_word`; `test_find_promos_flying_blue_under_35_alerts`; `test_find_promos_smiles_needs_under_12` (milheiro 17,20 → vazio); `test_find_promos_skips_seen_links`; `test_find_promos_without_confident_price_is_silent`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** com regex ancorada em "milheiro"; mapeamento programa←palavra-chave por substring minúscula.
- [ ] **Step 4: Run** → PASS. Conferir uma vez à mão: `python -c "from verificador.promos import fetch_feed; print(len(fetch_feed('https://passageirodeprimeira.com/feed/')))"` imprime um número > 0 (se o feed estiver fora do ar, anotar no README e seguir).
- [ ] **Step 5: Commit** `feat: vigia de promocoes por feed`.

---

### Task 8: Orquestração diária, falhas e agenda

**Files:**
- Create: `src/verificador/run_daily.py`, `tests/test_run_daily.py`, `scripts/register_task.ps1`
- Modify: `README.md` (como instalar, criar a chave, registrar a tarefa, ler o histórico, rodar a calculadora)

**Interfaces:**
- Consumes: tudo das Tasks 1–7.
- Produces: `run(cfg: Config, api_key: str, today: str, fetch=fetch_offers, notify_fn=notify) -> int` (devolve 0 em sucesso, 1 em falha; `fetch` e `notify_fn` injetáveis para teste) e `main() -> int` (lê config, `SERPAPI_KEY`, data local; falta de chave → aviso e retorno 1). Execução: `python -m verificador.run_daily`.

- [ ] **Step 1: Write the failing tests** (com `fetch` e `notify_fn` falsos, `tmp_path`):
  - `test_run_records_cheapest_compliant_and_returns_0`.
  - `test_run_empty_offers_records_status_empty_and_notifies_failure` (não grava preço 0).
  - `test_run_fetch_error_records_status_error_and_notifies` (levanta `CollectorError`).
  - `test_run_twice_same_day_single_row_and_no_duplicate_alert`.
  - `test_run_first_run_no_drop_alert`.
  - `test_run_alerts_on_drop_against_previous_day`.
  - `test_run_notifies_promos_once` (promo já vista não repete).
  - `test_main_without_api_key_returns_1`.
- [ ] **Step 2: Run** `python -m pytest tests/test_run_daily.py -v` → FAIL.
- [ ] **Step 3: Implement** `run`/`main`. Ordem: coletar → filtrar → gravar histórico → avisos de preço → promoções. Em qualquer falha de coleta, gravar `error`/`empty` e chamar `notify_fn` com o motivo (inclui "limite da API" quando for o caso). Avisos de preço só no primeiro registro `ok` do dia.
- [ ] **Step 4: Run** a suíte inteira `python -m pytest -q` → verde.
- [ ] **Step 5: Implement** `scripts/register_task.ps1`: cria a tarefa `VerificadorPassagens` diária às 08:00 executando `python -m verificador.run_daily` na pasta do projeto (`schtasks /Create ... /F`).
- [ ] **Step 6: Verificação ao vivo (com a chave do Sérgio):** rodar `python -m verificador.run_daily` uma vez; esperado: uma linha `ok` em `data/history.csv` com o preço do dia; rodar de novo e conferir que continua **uma** linha. Rodar `powershell -File scripts/register_task.ps1` e `schtasks /Query /TN VerificadorPassagens` (deve listar a tarefa como "Pronto").
- [ ] **Step 7: Commit** `feat: execucao diaria, falhas e agenda`.

---

## Self-review (feito)

- **Cobertura da spec:** metas 1–2 → Tasks 4, 5, 8; meta 3 → Task 6; meta 4 → Task 7; meta 5 → Task 3; regras de 4h/Brasil → Task 2; anti-metas (alerta à toa, quebra silenciosa, vazar chave) → Tasks 6, 8 e Global Constraints; riscos (SerpApi multi-trecho, duração de escala) → Task 5 e Review Focus 2.
- **Consistência de tipos:** `Offer/Leg/Layover` definidos na Task 1 e usados com as mesmas assinaturas nas Tasks 2, 5 e 8; `HistoryRecord`/`last_price` (Task 4) usados na Task 8; `price_alerts`/`notify` (Task 6) usados na Task 8; `find_promos`/`load_seen`/`save_seen` (Task 7) usados na Task 8.
- **Proporção:** plano com tarefas curtas, sem corpos de função; a única parte aberta de verdade é a Task 5, por depender do formato real da resposta da SerpApi.
- **Chamadas minhas, a conferir:** Livelo entra na lista de milheiro com limite de R$ 35 (a spec cita só Flying Blue/TAP/Smiles); limite de queda de 5% e alvo R$ 18.000 como na spec.
