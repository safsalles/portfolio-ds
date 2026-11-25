# Dimensionamento de equipe (WFM) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pipeline PySpark → previsão por hora → Erlang C com cenários → simulação de filas → monitor intraday com alerta Slack de teste, sobre o NYC 311 (canal telefone), em `portfolio-ds/dimensionamento-equipe/`.

**Architecture:** Pacote `src/` com um módulo por etapa, testado com pytest (testes antes do código). Um script `scripts/run_all.py` executa tudo e grava `results/results.json`; o README e o notebook só usam números desse arquivo. Parte matemática (Erlang, simulação, previsão, monitor) é Python puro/pandas; só `pipeline.py` usa Spark.

**Tech Stack:** Python (versão aceita pelo PySpark, ver Task 1), PySpark (API de DataFrame apenas), pandas, numpy, statsmodels (Poisson GLM), PyYAML, requests, pytest, matplotlib, jupyter.

**Spec:** `docs/superpowers/specs/2026-11-24-dimensionamento-equipe-design.md`

## Global Constraints

- Sem commit nem push; não criar contas. Onde um plano normal commitaria, o passo é "não commitar".
- Base: NYC 311 Service Requests (NYC Open Data), canal telefone. Recorte: 2 anos completos recentes, 1º ano treina, 2º testa (anos confirmados no dado na Task 8).
- Premissas fictícias (em `config/premissas.yaml`, ditas como fictícias no README): tempo médio de atendimento 360 s, folga 30%, cenários 80/20 (80% em 20 s) e 90/30 (90% em 30 s).
- Regra simples de referência: média das 4 observações da mesma hora e dia da semana com defasagem de 7, 14, 21 e 28 dias.
- Modelo: Poisson GLM com hora × dia da semana, feriados e tendência; métricas WAPE e MAPE só no ano de teste, mesma métrica para modelo e regra.
- Simulação: eventos discretos, chegadas de Poisson, atendimento exponencial; variação lognormal; semente fixa; réplicas.
- Webhook do Slack só em variável de ambiente `SLACK_WEBHOOK_URL`; nos testes é simulado.
- PySpark: somente API de DataFrame (sem RDD). Databricks: `databricks_entry.py` marcado "preparado, não executado".
- README.md e README.en.md; todo número do README vem de `results/results.json`.
- Download do dado e instalação de Java/PySpark só com autorização explícita do Sérgio (informar arquivo, fonte e tamanho).
- Fora do escopo deste plano: a pergunta em linguagem natural (item opcional da spec); só entra se o Sérgio pedir depois.

## Review Focus

- Hora sem nenhuma chamada: a série tem de ser preenchida com zero e o Erlang deve devolver 0 pessoas, sem erro de divisão.
- Tráfego (erlangs) maior ou igual ao número de agentes: fila instável; `service_level` deve devolver 0.0 e `agents_needed` deve crescer até estabilizar.
- Tráfego muito alto (centenas de erlangs): fatorial estoura; o Erlang C deve usar a recorrência do Erlang B, não fatoriais.
- Horário de verão de Nova York (hora duplicada e hora inexistente): a agregação deve usar um fuso explícito e não perder nem duplicar contagem.
- Linhas ruins no bruto: data de abertura nula, canal com maiúsculas/espaços diferentes ("PHONE", " phone"), chave duplicada: devem ser tratadas e contadas, não derrubar o pipeline.
- Falha do webhook (erro de rede ou resposta não-200): o monitor registra e segue, sem lançar exceção.

---

## File Structure

```
dimensionamento-equipe/
  README.md  README.en.md  requirements.txt  .gitignore  pytest.ini
  config/premissas.yaml
  src/__init__.py config.py erlang.py simulation.py pipeline.py forecast.py staffing.py monitor.py databricks_entry.py
  scripts/run_all.py  scripts/atualizar_readme.py
  tests/ test_config.py test_erlang.py test_simulation.py test_pipeline.py test_forecast.py test_staffing.py test_monitor.py test_readme.py conftest.py
  notebooks/analise.ipynb
  data/raw  data/processed  results/   (data/ fora do versionamento)
```

Cada módulo tem uma responsabilidade; só `pipeline.py` importa pyspark.

### Task 1: Ambiente e esqueleto

**Files:** Create: `requirements.txt`, `.gitignore`, `pytest.ini`, `src/__init__.py`, `tests/conftest.py`, pastas vazias.

**Interfaces:** Produces: ambiente virtual `.venv` da pasta onde `import pyspark` e `pytest` funcionam; `pytest.ini` com `pythonpath = .`.

- [ ] **Step 1: Verificar pré-requisitos.** Rodar `java -version` e `py -0` (lista versões de Python). Esperado hoje: Java ausente, só Python 3.15.
- [ ] **Step 2: Pedir autorização ao Sérgio** para instalar JDK 17 (ex.: Temurin via `winget install EclipseAdoptium.Temurin.17.JDK`) e, se o Python 3.15 não for aceito pelo PySpark, uma versão suportada (ex.: 3.12) para o `.venv` desta pasta. Não prosseguir sem o sim.
- [ ] **Step 3: Criar `.venv` e `requirements.txt`** (`pyspark`, `pandas`, `numpy`, `statsmodels`, `pyyaml`, `requests`, `matplotlib`, `jupyter`, `nbformat`, `pytest`) e instalar.
- [ ] **Step 4: Verificar** com `python -c "from pyspark.sql import SparkSession; s=SparkSession.builder.master('local[1]').getOrCreate(); print(s.range(3).count())"`. Esperado: imprime `3`.
- [ ] **Step 5: `.gitignore`** com `data/`, `results/*.parquet`, `.venv/`, `__pycache__/`. Não commitar.

### Task 2: Configuração de premissas

**Files:** Create: `config/premissas.yaml`, `src/config.py`; Test: `tests/test_config.py`

**Interfaces:** Produces:
```python
@dataclass(frozen=True) class Scenario: name: str; sl_target: float; wait_seconds: int
@dataclass(frozen=True) class Premissas: aht_seconds: int; shrinkage: float; scenarios: tuple[Scenario, ...]; alert_threshold: float; train_year: int; test_year: int
def load_premissas(path: str | Path) -> Premissas
```

- [ ] **Step 1: Teste** `test_load_premissas_values`: o arquivo real carrega `aht_seconds == 360`, `shrinkage == 0.30`, dois cenários `("80/20", 0.80, 20)` e `("90/30", 0.90, 30)`. `test_invalid_shrinkage_rejected`: `shrinkage` 1.0 ou negativa levanta `ValueError`.
- [ ] **Step 2:** rodar `pytest tests/test_config.py -v`; esperado FAIL.
- [ ] **Step 3:** implementar `load_premissas` com validação (shrinkage em [0,1), metas em (0,1], `alert_threshold` padrão 0.30 para desvio relativo; `train_year`/`test_year` com placeholders 0 até a Task 8).
- [ ] **Step 4:** rodar; esperado PASS. Não commitar.

### Task 3: Erlang C

**Files:** Create: `src/erlang.py`; Test: `tests/test_erlang.py`

**Interfaces:** Produces:
```python
def erlang_c(traffic: float, agents: int) -> float          # prob. de esperar
def service_level(traffic: float, agents: int, aht_s: float, wait_s: float) -> float
def average_speed_of_answer(traffic: float, agents: int, aht_s: float) -> float
def agents_needed(calls_per_hour: float, aht_s: float, sl_target: float, wait_s: float, shrinkage: float = 0.0) -> int
```
`traffic = calls_per_hour * aht_s / 3600` (erlangs). `agents_needed` devolve o mínimo de agentes presentes; com `shrinkage` devolve `ceil(n / (1 - shrinkage))`.

- [ ] **Step 1: Testes** (valores calculáveis à mão, não copiados de sites):
  - `test_mm1`: `erlang_c(0.5, 1) == pytest.approx(0.5)`.
  - `test_two_agents_one_erlang`: `erlang_c(1.0, 2) == pytest.approx(1/3)`.
  - `test_matches_reference_recurrence`: para `A` em {2, 10, 50, 200} e `N = ceil(A)+1..+5`, comparar com implementação de referência dentro do teste usando a relação `C = B / (1 - (A/N)(1 - B))` e `B` por recorrência do Erlang B.
  - `test_service_level_mm1`: `service_level(0.5, 1, aht_s=360, wait_s=0) == pytest.approx(0.5)`.
  - `test_unstable_queue`: `service_level(5, 5, 360, 20) == 0.0` e `erlang_c(6, 5) == 1.0`.
  - `test_zero_traffic`: `agents_needed(0, 360, 0.8, 20) == 0`.
  - `test_monotonic`: `service_level` não decresce ao somar agentes (A=10, N de 11 a 30).
  - `test_agents_needed_meets_target_minimally`: para 200 chamadas/h, 360 s, 80/20: `service_level` com N atende a meta e com N-1 não atende.
  - `test_shrinkage`: `agents_needed(..., shrinkage=0.30) == ceil(agents_needed(..., 0.0)/0.7)`.
  - `test_large_traffic_no_overflow`: `erlang_c(300, 310)` retorna float entre 0 e 1.
  - `test_stricter_target_needs_more`: 90/30 nunca pede menos pessoas que 80/20... (atenção: espera 30 s é mais folgada que 20 s; comparar usando metas na mesma janela, 90/20 ≥ 80/20).
- [ ] **Step 2:** rodar; esperado FAIL.
- [ ] **Step 3:** implementar usando a recorrência do Erlang B (nunca fatorial). `agents_needed` parte de `floor(traffic)+1` e incrementa.
- [ ] **Step 4:** rodar; esperado PASS.

### Task 4: Simulação de filas

**Files:** Create: `src/simulation.py`; Test: `tests/test_simulation.py`

**Interfaces:** Consumes: `erlang.service_level`, `erlang.erlang_c`. Produces:
```python
@dataclass(frozen=True) class SimResult: service_level: float; prob_wait: float; avg_wait_s: float; n_calls: int
def simulate_queue(calls_per_hour: float, aht_s: float, agents: int, wait_s: float, n_calls: int, seed: int, service: str = "exp", cv: float = 1.0) -> SimResult
def compare_with_erlang(calls_per_hour: float, aht_s: float, agents: int, wait_s: float, replicas: int = 20, n_calls: int = 20000, seed: int = 42, service: str = "exp") -> dict   # chaves: sim_mean, sim_ci_low, sim_ci_high, erlang, abs_diff
```
`service` ∈ {"exp","lognormal"}; lognormal com média `aht_s` e coeficiente de variação `cv`. Descarta aquecimento de 10% das chamadas. Fila FIFO, agentes sem folga.

- [ ] **Step 1: Testes:**
  - `test_determinism`: mesma semente, mesmo `SimResult`.
  - `test_mm1_wait_probability`: `simulate_queue(30, 60, 1, 0, 50000, seed=1).prob_wait` ≈ 0,5 com tolerância 0,02.
  - `test_matches_erlang_c`: cenário 200 chamadas/h, 360 s, N que atenda 80/20; `abs_diff` do nível de serviço ≤ 0,02 e o Erlang dentro (ou a menos de 0,01) do intervalo da simulação.
  - `test_zero_agents_rejected`: `agents=0` com chamadas levanta `ValueError`.
  - `test_lognormal_differs_when_cv_high`: com `cv=2.0` o nível de serviço simulado difere do exponencial (documenta onde o Erlang C erra); só afirma que `abs_diff` vira maior que no caso exponencial para o mesmo cenário.
- [ ] **Step 2:** FAIL. **Step 3:** implementar com heap de tempos de liberação dos agentes. **Step 4:** PASS. A tolerância 0,02 vira constante `SIM_TOLERANCE` citada no README.

### Task 5: Pipeline PySpark

**Files:** Create: `src/pipeline.py`; Test: `tests/test_pipeline.py`, `tests/conftest.py` (fixture `spark` com `local[1]`, `shuffle.partitions=1`)

**Interfaces:** Produces:
```python
def build_spark(app_name: str = "wfm") -> SparkSession
def clean_and_aggregate(df: DataFrame, channel: str = "PHONE", tz: str = "America/New_York") -> tuple[DataFrame, dict]
    # DataFrame: hour_ts (timestamp UTC), calls (long); dict: contagens descartadas {"null_ts":..,"other_channel":..,"duplicates":..}
def run_pipeline(raw_path: str, out_path: str, start: str, end: str) -> dict
```
Colunas de entrada esperadas (confirmar na Task 8): `unique_key`, `created_date`, `open_data_channel_type`. Saída Parquet em `out_path`.

- [ ] **Step 1: Testes** com DataFrame sintético pequeno:
  - `test_counts_per_hour`: 3 chamadas na hora 10h e 1 na 11h → 3 e 1.
  - `test_filters_channel_case_and_spaces`: "PHONE", " phone ", "ONLINE" → só as duas primeiras contam; `other_channel == 1`.
  - `test_drops_null_timestamp_and_duplicates`: contabiliza `null_ts` e `duplicates`.
  - `test_fills_missing_hours_with_zero`: chamadas às 10h e 13h → 11h e 12h aparecem com 0.
  - `test_dst_spring_forward_and_fall_back`: em 2023-03-12 (hora inexistente 02h) e 2023-11-05 (01h duplicada) a soma das contagens é igual ao número de linhas e não há `hour_ts` duplicado.
- [ ] **Step 2:** FAIL. **Step 3:** implementar só com `pyspark.sql.functions` (`date_trunc` em UTC após converter do fuso de NY; preencher horas por `sequence`). **Step 4:** PASS. Teste do `run_pipeline` com um CSV mínimo gravado em `tmp_path`.

### Task 6: Previsão

**Files:** Create: `src/forecast.py`; Test: `tests/test_forecast.py`

**Interfaces:** Produces (série horária = `pd.Series` indexada por `DatetimeIndex` UTC horário contínuo):
```python
def baseline_same_hour_4w(series: pd.Series) -> pd.Series      # média dos lags 7,14,21,28 dias
def build_features(index: pd.DatetimeIndex, tz: str = "America/New_York", holidays: Iterable[date] = ()) -> pd.DataFrame
def fit_poisson(train: pd.Series, holidays: Iterable[date] = ()) -> FittedModel
def predict(model: FittedModel, index: pd.DatetimeIndex) -> pd.Series
def wape(actual: pd.Series, pred: pd.Series) -> float
def mape(actual: pd.Series, pred: pd.Series) -> float            # ignora horas com real == 0, devolve também a contagem ignorada em mape_details
def evaluate(series: pd.Series, train_year: int, test_year: int, holidays=()) -> dict   # wape/mape modelo e regra, ganho relativo
```
Feriados: lista fixa de feriados federais dos EUA gerada por `pandas.tseries.holiday.USFederalHolidayCalendar`.

- [ ] **Step 1: Testes:**
  - `test_baseline_exact_on_periodic_series`: série semanal perfeitamente periódica → baseline igual ao real depois de 28 dias.
  - `test_metrics`: `wape([10,10],[8,12]) == pytest.approx(0.2)`; `mape` ignora real zero.
  - `test_model_recovers_hourly_pattern`: série sintética Poisson com padrão conhecido por hora × dia (semente fixa) → WAPE do modelo menor que o da regra e abaixo de 0,15 no teste.
  - `test_no_leakage`: `evaluate` só ajusta com `train_year`; alterar valores do ano de teste não muda os coeficientes (comparar predições com séries de teste distintas).
  - `test_same_metric_for_both`: `evaluate` devolve as quatro métricas sob as mesmas chaves e o mesmo conjunto de horas (baseline com NaN no começo é cortado para ambos).
  - `test_holiday_feature`: dia de feriado ganha coluna marcada.
- [ ] **Step 2:** FAIL. **Step 3:** implementar com `statsmodels` GLM Poisson (dummies hora × dia da semana, flag de feriado, tendência linear em dias). **Step 4:** PASS.

### Task 7: Dimensionamento por cenário

**Files:** Create: `src/staffing.py`; Test: `tests/test_staffing.py`

**Interfaces:** Consumes: `erlang.agents_needed`, `config.Premissas`. Produces:
```python
def staffing_plan(forecast: pd.Series, premissas: Premissas) -> pd.DataFrame   # colunas: hour, scenario, calls, agents_present, agents_scheduled
def scenario_cost(plan: pd.DataFrame) -> pd.DataFrame                           # por cenário: soma de agent-hours presentes e escalados, pico
```

- [ ] **Step 1: Testes:** `test_plan_shape` (uma linha por hora × cenário); `test_zero_calls_zero_agents`; `test_scheduled_ge_present`; `test_90_30_costs_more_than_80_20_when_same_window` usando um cenário auxiliar 90/20 e 80/20 (comparação válida na mesma janela); `test_scenario_cost_sums`.
- [ ] **Step 2:** FAIL. **Step 3:** implementar (previsão arredondada para cima apenas no cálculo do Erlang, mantendo o valor original em `calls`). **Step 4:** PASS.

### Task 8: Monitor intraday e alerta

**Files:** Create: `src/monitor.py`; Test: `tests/test_monitor.py`

**Interfaces:** Produces:
```python
def compare_intraday(forecast: pd.Series, actual: pd.Series) -> pd.DataFrame     # hour, forecast, actual, deviation (relativa)
def find_alerts(df: pd.DataFrame, threshold: float, min_calls: int = 20) -> pd.DataFrame
def format_alert(row: pd.Series) -> str
def send_slack_alert(webhook_url: str, text: str, post: Callable = requests.post) -> bool   # False em falha, nunca lança
def run_monitor(forecast, actual, threshold, webhook_url: str | None, post=requests.post) -> dict   # {"alerts": n, "sent": n}
```
`deviation = (actual - forecast) / max(forecast, 1)`; alerta quando `abs(deviation) > threshold` e `forecast >= min_calls`.

- [ ] **Step 1: Testes:** `test_alert_above_threshold_only`; `test_min_calls_suppresses_noise`; `test_slack_payload_and_url` (post falso captura URL e `json={"text": ...}`); `test_webhook_failure_does_not_raise` (post lança `requests.ConnectionError` e depois devolve status 500 → retorna `False`); `test_no_webhook_url_dry_run` (sem URL conta alertas, `sent == 0`, nada é enviado).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS.

### Task 9: Dados reais e execução completa

**Files:** Create: `scripts/run_all.py`; Output: `data/raw/`, `data/processed/`, `results/results.json`

**Interfaces:** Consumes todos os módulos. Produces `results/results.json` com chaves: `data` (fonte, período, linhas lidas, descartes), `forecast` (WAPE/MAPE modelo e regra, ganho relativo), `staffing` (por cenário: agent-hours, pico), `simulation` (por cenário: Erlang, simulação, IC, diferença; variação lognormal), `monitor` (nº de alertas no dia de teste), `premissas` (cópia).

- [ ] **Step 1: Pedir autorização do download** ao Sérgio, informando dataset (NYC 311 Service Requests, NYC Open Data), filtro (colunas e anos) e tamanho estimado (verificar via API antes). Consultar a API com `$limit=5` para confirmar os nomes de campo (`created_date`, `open_data_channel_type`, `unique_key`) e a existência do valor `PHONE`, e escolher os 2 anos completos mais recentes. Registrar os anos em `config/premissas.yaml`. Se os nomes diferirem, ajustar `pipeline.py` com teste primeiro.
- [ ] **Step 2:** baixar só as colunas necessárias, só os dois anos, para `data/raw/` (CSV paginado por ano).
- [ ] **Step 3:** implementar `scripts/run_all.py`: pipeline → série → `evaluate` → `staffing_plan` no ano de teste → `compare_with_erlang` em 3 horas representativas (pico, média, vale) por cenário → monitor num dia de teste (webhook só se `SLACK_WEBHOOK_URL` existir) → grava `results.json`.
- [ ] **Step 4:** rodar `python scripts/run_all.py`. Esperado: termina sem erro e escreve `results/results.json`. Conferir à mão: soma das contagens horárias = linhas PHONE do filtro; se não bater, parar e investigar.
- [ ] **Step 5:** se o modelo **não** ganhar da regra, registrar isso no resultado e no README sem maquiar.

### Task 10: Notebook, Databricks e READMEs

**Files:** Create: `notebooks/analise.ipynb`, `src/databricks_entry.py`, `scripts/atualizar_readme.py`, `README.md`, `README.en.md`; Test: `tests/test_readme.py`

**Interfaces:** `atualizar_readme.py` lê `results/results.json` e preenche, entre marcadores `<!-- RESULTADOS:INICIO -->` / `<!-- RESULTADOS:FIM -->`, as tabelas dos dois READMEs.

- [ ] **Step 1: Teste** `test_readme_numbers_match_results`: cada número entre os marcadores aparece em `results.json` (ou é derivado por formatação); `test_readme_declares_fictional_team`: os dois READMEs contêm o aviso de equipe e premissas fictícias; `test_readme_databricks_not_executed`: contém "preparado, não executado" / "prepared, not executed".
- [ ] **Step 2:** FAIL. **Step 3:** escrever os READMEs (PT e EN) com: objetivo, aviso de equipe fictícia, premissas, como rodar (`pytest`, `run_all.py`), estrutura, limites (horário de abertura como chegada; Erlang C assume atendimento exponencial), status do Databricks. Tabelas vêm do script.
- [ ] **Step 4:** `databricks_entry.py`: lê de um caminho de volume e chama `pipeline.clean_and_aggregate` e `forecast.evaluate`; sem execução aqui.
- [ ] **Step 5:** notebook importa o pacote, lê `results.json`, mostra: série horária e sazonalidade, previsto × real, pessoas por hora e custo dos cenários, simulação × Erlang (exponencial e lognormal), exemplo de alerta. Executar todo o notebook e confirmar que roda sem erro (`jupyter nbconvert --execute`).
- [ ] **Step 6:** rodar `pytest -v` na pasta inteira; esperado: tudo PASS.

### Task 11: Registro na base de currículos

**Files:** Modify: `projetos.yaml` da base de currículos (Dropbox)

- [ ] **Step 1:** ler o arquivo e o formato dos outros projetos; adicionar o projeto com resumo baseado só em `results.json` e `fonte` apontando para a pasta e o README.
- [ ] **Step 2:** **perguntar ao Sérgio** antes de colocar em qualquer versão do currículo (versão Dados no limite de 2 páginas). Não editar versões.

---

## Self-review

- **Spec:** objetivos 1–7 → Tasks 5, 6, 3/7, 4, 8, 10; cenários → Tasks 3 e 7; Databricks preparado → Task 10; registro → Task 11; item opcional 8 explicitamente fora (nota nas restrições).
- **Tipos:** `Scenario`/`Premissas` (Task 2) usados em 7; `erlang.*` (3) usados em 4 e 7; `forecast.evaluate` (6) usada em 9/10; assinaturas conferidas.
- **Proporção:** código só onde o algoritmo não decorre da assinatura e dos testes.

