# Simulador customizável com analisador de entrada: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Estender `dimensionamento-equipe` com um analisador de entrada (estilo Arena), simulação com distribuições escolhidas pelo usuário, validação contra a base real do Technion e um app Streamlit que funciona sem o usuário carregar nada.

**Architecture:** Três módulos novos de biblioteca (`distributions`, `input_analyzer`, `scenario`) mais a generalização de `simulation.py`; scripts de preparo/análise geram dados de exemplo e `results/results.json`; o app Streamlit é uma camada fina sobre `app/logic.py`. Todo número vem de código rodado.

**Tech Stack:** Python 3.12 (`C:\venvs\wfm`), numpy, scipy (já presente via statsmodels), pandas, PyYAML, matplotlib, Streamlit (novo, precisa de autorização), pytest.

**Spec:** `docs/superpowers/specs/2026-11-25-simulador-customizavel-design.md` (estende `2026-11-24-dimensionamento-equipe-design.md`).

## Global Constraints

- Sem commit nem push até o Sérgio pedir; sem criar contas. Passos de commit abaixo dizem "não commitar".
- Specs primeiro, testes antes do código (RED visto antes do GREEN).
- Todo número do README, do notebook e do app sai de código rodado (`results/results.json` ou saída do motor).
- O projeto e o app funcionam **sem o usuário carregar nada**; upload é opcional. O app nunca baixa nada sozinho.
- Amostras derivadas committadas em `data/exemplos/`, teto de cerca de 5 MB no total, com `FONTES.md` (origem, termos, agradecimento ao Technion SEE Center, documentação de Guedj e Mandelbaum, 2000).
- Critério de ordenação do analisador: **AIC**; mostrar também BIC, estatística KS e erro quadrático; p-valor só informativo, com aviso de que perde sentido em amostras grandes.
- Candidatas: exponencial, gama, Weibull, lognormal, Erlang, normal, beta, triangular, uniforme.
- Cenário padrão do app: chegadas do NYC 311 (previsão por hora) + atendimento = melhor ajuste nos tempos do Technion, com ranking visível; README e app dizem que as fontes são misturadas.
- Validação com o banco: reportar a diferença como saiu, com a ressalva do abandono; nunca prometer que bate.
- README em português e inglês; teste existente `tests/test_readme.py` continua exigindo bloco gerado igual ao `render`.
- Baixar `AnonymousBank.rar` (10,6 MB, `see-center.iem.technion.ac.il`) e instalar Streamlit só com o sim do Sérgio no momento. Não enviar e-mail ao professor Mandelbaum; o README só registra a pendência.
- Fora do escopo: abandono de fila na simulação, múltiplas filas, prioridades, hospedar o app, Datadog/Salesforce.
- Todos os 53 testes atuais continuam passando (Spark: rodar no terminal do Sérgio com `JAVA_HOME` do Temurin 17).

## Review Focus

- Amostra com valores todos iguais (variância zero) ou com menos pontos que o mínimo: erro claro (`ValueError`), nunca exceção crua do scipy. (Task 2)
- CSV do usuário com vírgula decimal ("1,5"), cabeçalho, coluna inexistente, valores gigantes: tratado e contado, sem quebrar. (Tasks 2 e 8)
- Timestamps com resolução de 1 s geram intervalos iguais a zero entre chegadas: o analisador de chegadas não pode descartá-los em silêncio nem quebrar. (Task 7)
- Distribuição escolhida que gera valores negativos (normal): truncar em zero sem laço infinito. (Task 1)
- Cenário instável (tráfego ≥ agentes) ou `n_calls` enorme no app: simulação termina e o app avisa em vez de travar. (Tasks 4 e 8)

---

## File Structure

```
dimensionamento-equipe/
  src/distributions.py         # DistSpec, build_sampler, describe  (único lugar com a lista de distribuições)
  src/input_analyzer.py        # clean_values, fit_distributions, FitResult
  src/scenario.py              # SimScenario, load_scenario, run_scenario
  src/simulation.py            # generalizado (custom samplers, trace replay)
  src/validacao_banco.py       # replay do banco do Technion
  scripts/preparar_technion.py # .rar extraído -> data/exemplos/technion_chamadas.csv.gz
  scripts/analisar_entradas.py # ajusta e grava results/results.json (chaves novas)
  app/logic.py  app/app.py     # camada Streamlit
  config/cenario_exemplo.yaml
  data/exemplos/ (technion_chamadas.csv.gz, nyc311_horario.csv.gz, FONTES.md)
  tests/ test_distributions.py test_input_analyzer.py test_scenario.py test_simulation.py (ampliado)
         test_validacao_banco.py test_technion_prep.py test_app.py test_independencia.py
```

`distributions.py` não estava na spec: existe só para a lista de distribuições não ficar duplicada entre analisador, cenário e simulador (ruling do plano).

### Task 1: Distribuições e amostradores

**Files:** Create: `src/distributions.py`; Test: `tests/test_distributions.py`

**Interfaces:** Produces:
```python
@dataclass(frozen=True) class DistSpec: dist: str; params: dict[str, float]
Sampler = Callable[[np.random.Generator, int], np.ndarray]
DISTRIBUTIONS: dict[str, tuple[str, ...]]   # nome -> nomes dos parâmetros
def build_sampler(spec: DistSpec) -> Sampler
def describe(spec: DistSpec, n: int = 200_000, seed: int = 0) -> dict   # {"mean":..., "cv":...} amostrados
```
Parametrizações: `expon{mean}`, `lognormal{mean,cv}`, `gamma{mean,cv}`, `weibull{shape,scale}`, `erlang{k,mean}`, `normal{mean,sd}` (truncada em >0 por reamostragem com teto de tentativas), `triangular{low,mode,high}`, `uniform{low,high}`, `beta{low,high,a,b}`. Parâmetro desconhecido, ausente ou fora do domínio: `ValueError`.

- [ ] **Step 1: Testes** `test_sampler_mean_cv` (parametrizado sobre as 9 distribuições com parâmetros fixos: média e CV amostrados dentro de 3% do teórico, `rng` com semente), `test_normal_truncated_positive` (média 1, sd 5: nenhum valor ≤ 0 em 10 mil amostras e termina em menos de 2 s), `test_unknown_dist_rejected`, `test_bad_params_rejected` (cv ≤ 0, high < low, shape ≤ 0, parâmetro faltando), `test_sampler_deterministic_with_seed`.
- [ ] **Step 2:** `pytest tests/test_distributions.py -q`; esperado: FAIL (módulo não existe).
- [ ] **Step 3:** Implementar. Lognormal e gama a partir de média e CV; normal truncada reamostra os negativos até no máximo 100 rodadas e depois levanta `ValueError`.
- [ ] **Step 4:** rodar; esperado PASS. Não commitar.

### Task 2: Analisador de entrada

**Files:** Create: `src/input_analyzer.py`; Test: `tests/test_input_analyzer.py`

**Interfaces:** Consumes: `distributions.DistSpec`. Produces:
```python
CANDIDATES = ("expon","gamma","weibull","lognormal","erlang","normal","beta","triangular","uniform")
@dataclass(frozen=True) class FitResult: name: str; spec: DistSpec; aic: float; bic: float; ks_stat: float; ks_p: float; sq_error: float; rank: int
def clean_values(values: Iterable) -> tuple[np.ndarray, dict]   # dict: kept, dropped_empty, dropped_non_numeric, dropped_nonpositive
def fit_distributions(values: np.ndarray, candidates: Sequence[str] = CANDIDATES, min_points: int = 30) -> list[FitResult]
def histogram_with_fits(values: np.ndarray, fits: Sequence[FitResult], bins: int = 40) -> matplotlib.figure.Figure
```
`clean_values` aceita números, strings com vírgula decimal ("1,5") e vazios; descarta o que não for finito e positivo e conta cada motivo. `fit_distributions` ajusta com localização fixa em 0 (durações), Erlang como gama com forma inteira, devolve ordenado por AIC crescente com `rank` 1..n; levanta `ValueError` claro para menos de `min_points` ou variância zero.

- [ ] **Step 1: Testes:** `test_recovers_source_distribution` (amostras sintéticas de lognormal, gama, exponencial e Weibull, 20 mil pontos, semente: a de origem fica entre as 2 primeiras por AIC; para exponencial, `expon` ou `gamma`/`weibull` com forma ≈ 1 contam como correto: o teste exige `expon` entre as 3 primeiras); `test_ranking_sorted_by_aic`; `test_ks_in_unit_interval`; `test_clean_values_counts` (entrada `[1, "2,5", "", "abc", -3, 0, None, float("nan"), 7]` → kept 3, e contagens corretas); `test_too_few_points_error` e `test_constant_sample_error` (`ValueError`); `test_huge_outliers_do_not_crash` (inclui 1e9); `test_histogram_figure_returns_figure`.
- [ ] **Step 2:** rodar; esperado FAIL. **Step 3:** implementar com `scipy.stats` (`fit` com `floc=0`; AIC/BIC pela log-verossimilhança; erro quadrático entre histograma normalizado e a densidade). **Step 4:** PASS.

### Task 3: Cenário em YAML

**Files:** Create: `src/scenario.py`, `config/cenario_exemplo.yaml`; Test: `tests/test_scenario.py`

**Interfaces:** Consumes: `distributions.DistSpec`, `build_sampler`; `simulation` (Task 4, importado dentro de `run_scenario` para evitar ciclo). Produces:
```python
@dataclass(frozen=True) class SimScenario:
    name: str; service: DistSpec; arrival: DistSpec | None   # None = Poisson pela taxa
    calls_per_hour: float; agents: int; wait_seconds: int; sl_target: float
def load_scenario(path: str | Path) -> SimScenario
def run_scenario(sc: SimScenario, n_calls: int = 20000, replicas: int = 20, seed: int = 42) -> dict   # chaves: sim_mean, sim_ci_low, sim_ci_high, erlang | None, stable (bool)
```
`erlang` só é calculado quando serviço e chegadas são exponenciais/Poisson; senão `None`.

- [ ] **Step 1: Testes:** `test_load_example` (o YAML de exemplo carrega); `test_invalid_agents_rejected` (agentes < 1); `test_unknown_distribution_rejected`; `test_bad_param_rejected`; `test_run_scenario_exp_matches_erlang` (exp/Poisson: `abs(sim_mean - erlang) <= 0.02`); `test_non_exponential_has_no_erlang` (`erlang is None`); `test_unstable_scenario_flagged` (tráfego ≥ agentes: `stable is False`, retorna sem travar).
- [ ] **Step 2:** FAIL. **Step 3:** implementar; exemplo: serviço `lognormal{mean:360,cv:1.0}`, 100 chamadas/h, 10 agentes, meta 80/20. **Step 4:** PASS.

### Task 4: Simulação generalizada

**Files:** Modify: `src/simulation.py`; Test: `tests/test_simulation.py` (acrescentar; os testes atuais não mudam)

**Interfaces:** Consumes: `distributions.Sampler`. Produces:
```python
def simulate_custom(arrival_sampler: Sampler | None, service_sampler: Sampler, calls_per_hour: float, agents: int, wait_s: float, n_calls: int, seed: int) -> SimResult
def simulate_trace(arrival_times_s: np.ndarray, service_sampler: Sampler, agents: int, wait_s: float, seed: int) -> SimResult
```
`arrival_sampler=None` = Poisson (intervalos exponenciais de média `3600/calls_per_hour`). `simulate_queue` passa a chamar `simulate_custom` (assinatura e resultados atuais preservados).

- [ ] **Step 1: Testes novos:** `test_custom_exp_reproduces_erlang` (exp/Poisson dentro de `SIM_TOLERANCE` do Erlang C); `test_custom_deterministic_with_seed`; `test_deterministic_arrivals_wait_less_than_poisson` (intervalos constantes de 3600/cph, mesmo serviço exponencial, mesma carga: `prob_wait` menor que no Poisson); `test_trace_constant_service_exact` (3 chegadas em 0, 1, 2 s, 1 agente, serviço constante de 10 s: esperas 0, 9, 18); `test_unstable_terminates` (tráfego > agentes, 2000 chamadas: retorna).
- [ ] **Step 2:** FAIL. **Step 3:** extrair o laço atual para `simulate_custom`; `simulate_trace` usa os instantes dados. **Step 4:** PASS e rodar a suíte inteira: os testes antigos continuam passando.

### Task 5: Dados do Technion (preparo e exemplos)

**Files:** Create: `scripts/preparar_technion.py`, `data/exemplos/FONTES.md`; Modify: `.gitignore` (acrescentar `!data/exemplos/` depois de `data/`); Test: `tests/test_technion_prep.py`

**Interfaces:** Produces:
```python
def parse_technion(lines: Iterable[str]) -> pd.DataFrame   # colunas: month, day, entry_s, type, outcome, q_time_s, ser_time_s
def prepare(raw_dir: Path, out_path: Path) -> dict          # grava CSV gz; devolve {"files","calls","served","abandoned","period"}
```
`entry_s` = segundos desde 00:00 da hora de `vru_entry`; `type` ∈ PS/PE/IN/NE/NW/TT; `outcome` ∈ AGENT/HANG/PHANTOM.

- [ ] **Step 1: Pedir o sim do Sérgio** para baixar `https://see-center.iem.technion.ac.il/databases/AnonymousBank/Data/AnonymousBank.rar` (10,6 MB) para uma pasta nova `data/raw/technion/`. Sem o sim, parar aqui.
- [ ] **Step 2:** baixar e confirmar a extração com `tar -xf` (Windows) ou outro extrator disponível; se nenhum abrir `.rar`, parar e perguntar. Listar os 12 arquivos e imprimir as 3 primeiras linhas de um deles.
- [ ] **Step 3: Testes** com até 5 linhas **reais** coladas como fixture (formato confirmado no Step 2): `test_parse_columns_and_types`, `test_parse_served_has_positive_service`, `test_abandoned_has_zero_service`, `test_prepare_counts_match_documentation` (arquivo real: 12 arquivos, 20 a 30 mil chamadas por mês, período 01/01/1999–31/12/1999; teste marcado para pular se `data/raw/technion` não existir).
- [ ] **Step 4:** rodar; FAIL. **Step 5:** implementar `parse_technion` e `prepare`; saída `data/exemplos/technion_chamadas.csv.gz`. **Step 6:** PASS. Escrever `FONTES.md` (origem, termos, agradecimento, a pendência de avisar o professor Mandelbaum). Conferir `du`: arquivos de `data/exemplos/` somam no máximo cerca de 5 MB.
- [ ] **Step 7:** gerar `data/exemplos/nyc311_horario.csv.gz` a partir de `data/processed/hourly.parquet` (colunas `hour_ts`, `calls`) numa função `exportar_nyc_horario(parquet, out)` em `scripts/analisar_entradas.py` (Task 7), testada lá.

### Task 6: Validação contra o banco

**Files:** Create: `src/validacao_banco.py`; Test: `tests/test_validacao_banco.py`

**Interfaces:** Consumes: `simulation.simulate_trace`, `distributions.Sampler`. Produces:
```python
def replay_validation(calls: pd.DataFrame, service_sampler: Sampler, agents: int, wait_s: float, day_type: str, hours: tuple[int, int], seed: int = 0) -> dict
# chaves: n_calls, real_mean_wait_s, sim_mean_wait_s, real_service_level, sim_service_level, abandoned_share
```
Filtra `calls` (saída de `parse_technion`) por tipo de dia (`"weekday"` Dom–Qui, como na documentação, ou `"weekend"`) e faixa de horas; usa só ligações que chegaram a ser atendidas para a espera real; reporta a fração de abandono da faixa.

- [ ] **Step 1: Testes:** `test_self_consistency` (gera um traço sintético com o próprio simulador, 8 agentes, serviço lognormal; o replay devolve diferença de espera média abaixo de 10% da real); `test_reports_abandoned_share` (traço com 20% de `HANG`: `abandoned_share` ≈ 0,2); `test_empty_window_error` (faixa sem ligações: `ValueError` claro).
- [ ] **Step 2:** FAIL. **Step 3:** implementar. **Step 4:** PASS.

### Task 7: Análise das entradas e resultados

**Files:** Create: `scripts/analisar_entradas.py`; Modify: `scripts/atualizar_readme.py` (novas seções em `render`, textos PT e EN), `README.md`, `README.en.md`; Test: `tests/test_readme.py` (ampliar), `tests/test_analisar_entradas.py`

**Interfaces:** Consumes: `input_analyzer`, `validacao_banco`, `scenario`. Produces: `results/results.json` ganha as chaves `analisador` (`atendimento_technion`: ranking completo com `name, aic, bic, ks_stat, sq_error, rank` e `n`; `chegadas_nyc`: ranking por faixa de hora; `proposta`: nome e parâmetros da melhor distribuição de atendimento) e `validacao_banco` (saída de `replay_validation` e a ressalva). Funções:
```python
def intervalos_chegada(timestamps: pd.Series, jitter_seed: int = 0) -> np.ndarray   # segundos; empates (0 s) recebem ruído uniforme em [0,1)
def exportar_nyc_horario(parquet: Path, out: Path) -> None
def main(skip_spark_inputs: bool = False) -> None
```

- [ ] **Step 1: Testes:** `test_intervalos_ties_do_not_vanish` (timestamps repetidos no mesmo segundo: nenhum intervalo ≤ 0 e a contagem de intervalos = n−1); `test_intervalos_mean_close_to_true` (Poisson sintético de taxa conhecida: média dos intervalos ≈ 1/taxa em 2%); `test_exportar_nyc_horario_roundtrip`; no `test_readme.py`: `test_render_has_analyzer_section` (o `render` contém a tabela de ranking e a frase da proposta) e `test_render_states_mixed_sources`.
- [ ] **Step 2:** FAIL. **Step 3:** implementar o script (ajusta o atendimento nos `ser_time_s` dos atendidos do Technion e as chegadas do NYC 311 por faixa 0–5 h, 9–17 h e 18–23 h usando `data/raw/nyc311_phone.csv` quando existir; sem o CSV bruto, reaproveita o ranking já gravado em `results.json`); rodar a validação com 8 agentes (documentação), serviço = proposta, faixa de dias úteis 10–11 h.
- [ ] **Step 4:** rodar `python scripts/analisar_entradas.py`; esperado: `results.json` com as chaves novas. Conferir à mão `n` = número de atendidos da `prepare`.
- [ ] **Step 5:** ampliar `render` (PT e EN) e rodar `python scripts/atualizar_readme.py`; PASS em `tests/test_readme.py`. Texto do README: o que a base é, por que foi usada, o ranking, a ressalva de p-valor em amostra grande, a validação com o abandono, fontes misturadas. Nenhuma afirmação de melhor ajuste fora do bloco gerado.

### Task 8: App Streamlit

**Files:** Create: `app/logic.py`, `app/app.py`; Modify: `requirements.txt` (streamlit); Test: `tests/test_app.py`

**Interfaces:** Consumes: `input_analyzer`, `scenario`, `distributions`, `results/results.json`, `data/exemplos/*`. Produces:
```python
def load_defaults(root: Path) -> dict   # {"fits": [...], "proposal": DistSpec, "calls_per_hour": float, "source_note": str}
def analyze_upload(file_bytes: bytes, column: str | None) -> dict   # {"values", "report", "fits"} ou {"error": str}; nunca levanta
def simulate(service: DistSpec, arrival: DistSpec | None, calls_per_hour: float, agents: int, wait_s: int, sl_target: float, n_calls: int = 20000) -> dict
MAX_CALLS = 200_000
```
`simulate` limita `n_calls` a `MAX_CALLS` e devolve `stable=False` com aviso quando tráfego ≥ agentes.

- [ ] **Step 1: Pedir o sim do Sérgio** para instalar `streamlit` em `C:\venvs\wfm`. Sem o sim, parar aqui.
- [ ] **Step 2: Testes:** `test_load_defaults_without_raw_or_results_parquet` (usa só `results.json` e `data/exemplos`); `test_analyze_upload_valid_csv` (vírgula decimal e cabeçalho); `test_analyze_upload_invalid_returns_error` (arquivo vazio, só texto, coluna inexistente: `{"error": ...}`); `test_simulate_caps_n_calls`; `test_simulate_unstable_flag`; `test_app_runs_without_upload` com `streamlit.testing.v1.AppTest.from_file("app/app.py")`: `at.run()` sem exceção e com o ranking e a frase de fontes misturadas presentes; `test_app_with_invalid_upload_shows_error_not_exception`.
- [ ] **Step 3:** FAIL. **Step 4:** implementar `logic.py` (puro) e `app.py` (menu de distribuição de atendimento e de chegadas com parâmetros, upload opcional, ranking e histograma com curvas, botão simular, comparação com Erlang C quando aplicável, caixa de "o que é esta base e por que usamos"). **Step 5:** PASS.

### Task 9: Independência, documentação e registro

**Files:** Create: `tests/test_independencia.py`; Modify: `README.md`, `README.en.md`, `notebooks/analise.ipynb`, `scripts/gerar_figuras.py` (figura do ranking), `Dropbox\Carreira\base\projetos.yaml` (texto da entrada `dimensionamento-equipe`)

- [ ] **Step 1: Teste** `test_app_independent_of_raw_data`: copia só `app/`, `src/`, `config/`, `data/exemplos/` e `results/results.json` para uma pasta temporária (sem `data/raw`, sem `data/processed`, sem parquets) e roda o `AppTest` nela sem exceção.
- [ ] **Step 2:** FAIL se algum caminho depender dos arquivos brutos; corrigir o código, não o teste. PASS.
- [ ] **Step 3:** documentar no README (PT e EN, fora dos marcadores): como abrir o app (`streamlit run app/app.py`), como trazer o seu arquivo, `FONTES.md`, a pendência de avisar o professor Mandelbaum. Acrescentar ao notebook uma seção do analisador com o ranking e executar o notebook inteiro (`jupyter nbconvert --execute`), sem erro e sem caminhos locais.
- [ ] **Step 4:** suíte completa: `pytest` no terminal do Sérgio (inclui Spark); esperado: todos passam, com a contagem real registrada.
- [ ] **Step 5:** atualizar a entrada `dimensionamento-equipe` no `projetos.yaml` só com fatos verificados (sem afirmar que o ajuste "venceu" nada fora do `results.json`); **perguntar ao Sérgio** antes de pôr em qualquer versão do currículo. Não commitar; depois, perguntar se as mudanças vão para a branch do PR nº 8 ou para um PR novo.

---

## Self-review

- **Spec:** objetivos 1 → Task 2; 2 → Tasks 1 e 4; 3 → Task 3; 4 → Task 8; 5 → Tasks 5 e 7; 6 → Tasks 8 e 9; 7 → Task 6. Restrições de download, Streamlit, aviso ao professor e fontes misturadas: Tasks 5, 8, 7 e 9.
- **Tipos:** `DistSpec`/`Sampler` (Task 1) usados em 2, 3, 4, 6, 8; `simulate_custom`/`simulate_trace` (4) usados em 3 e 6; `FitResult` (2) alimenta 7 e 8; `parse_technion` (5) alimenta 6 e 7. Nomes conferidos.
- **Review Focus:** variância zero e amostra pequena (Task 2), vírgula decimal e coluna inexistente (Tasks 2 e 8), intervalos zero (Task 7), normal truncada (Task 1), cenário instável e `n_calls` enorme (Tasks 4 e 8): cada linha tem teste na tarefa dona.
- **Ordem e bloqueios:** as Tasks 5 e 8 param no pedido de autorização; as demais seguem sem depender de download ou instalação.
- **Proporção:** o plano traz assinaturas, nomes de testes e valores da spec, sem os corpos do código.
