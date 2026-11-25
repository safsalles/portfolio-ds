"""Preenche as tabelas dos READMEs com os números de results/results.json.

Uso: python scripts/atualizar_readme.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEGIN, END = "<!-- RESULTADOS:INICIO -->", "<!-- RESULTADOS:FIM -->"
FLOW_BEGIN, FLOW_END = "<!-- FLUXO:INICIO -->", "<!-- FLUXO:FIM -->"


def flow_source(lang: str) -> str:
    """Diagrama Mermaid: um arquivo só por idioma, usado pelo app e injetado nos READMEs."""
    return (ROOT / "app" / f"fluxo_dados.{lang}.mmd").read_text(encoding="utf-8")


def flow_text(lang: str) -> str:
    return "```mermaid\n" + flow_source(lang).strip() + "\n```"

T = {
    "pt": {
        "dec": ",", "thou": ".",
        "data": "### Dados", "fcst": "### Previsão por hora (ano de teste, medida fora da amostra)",
        "staff": "### Pessoas necessárias por cenário (premissas fictícias)",
        "sim": "### Simulação de filas × Erlang C (nível de serviço)",
        "mon": "### Monitoramento intraday",
        "h_method": "Método", "rule": "Regra simples (média das 4 semanas)",
        "single": "Modelo Poisson, ajuste único no ano de treino",
        "monthly": "Modelo Poisson, reajustado todo mês só com dados passados",
        "gain": "Ganho do modelo reajustado sobre a regra (WAPE)",
        "src": "Fonte", "period": "Treino / teste", "rows": "Linhas lidas (todas no canal telefone, sem nulos nem duplicadas)",
        "hours": "Horas na série",
        "sc": "Cenário", "ah_p": "Pessoas-hora presentes", "ah_s": "Pessoas-hora escaladas (com folga)",
        "pk_p": "Pico presentes", "pk_s": "Pico escaladas",
        "hr": "Hora", "calls": "Chamadas/h previstas", "ag": "Agentes", "erl": "Erlang C",
        "sx": "Simulação (atend. exponencial)", "sl": "Simulação (atend. lognormal)",
        "peak": "pico", "median": "mediana", "valley": "vale",
        "thr": "Limite de desvio para alerta", "cmp": "Horas comparadas", "al": "Horas em alerta",
        "day": "Dia com mais alertas", "wh": "Webhook do Slack configurado nesta execução",
        "yes": "sim", "no": "não",
        "an_h": "### Analisador de entrada: tempo de atendimento (base real do Technion)",
        "an_intro": "{n_total} atendimentos reais ({n_used} usados no ajuste, amostra aleatória com semente fixa). Critério de ordenação definido antes de rodar: AIC (menor é melhor).",
        "an_cols": "| Posição | Distribuição | AIC | BIC | KS | Erro quadrático | Parâmetros |",
        "an_prop": "Distribuição proposta (melhor AIC): **{best}**. Pelo erro quadrático, a melhor é **{sq}**: os critérios não concordam. A exponencial, hipótese do Erlang C, ficou em {pos}º lugar por AIC. Com centenas de milhares de pontos qualquer teste de aderência rejeita todas as candidatas, por isso o p-valor não é usado para decidir.",
        "arr_h": "### Analisador de entrada: chegadas do NYC 311 (intervalos entre chamadas, dias úteis)",
        "arr_cols": "| Faixa | Intervalos (total) | Usados no ajuste | 1º | 2º | 3º |",
        "arr_note": "Cada faixa mistura horas com taxas diferentes, então intervalos que não são exponenciais são esperados; isso, sozinho, não refuta chegadas de Poisson.",
        "val_h": "### Validação com o banco real (Technion)",
        "val_cols": "| Métrica | Real | Simulada |",
        "val_wait": "Espera média (s)", "val_sl": "Atendidas em até {w} s",
        "val_info": "Janela: dias úteis do banco, {h}h às {h1}h; {n} ligações atendidas em {d} dias; {a} atendentes na simulação; abandono real na janela: {ab}.",
        "iv_h": "### Por que a simulação não reproduz o banco? (investigação)",
        "iv_intro": "Dias úteis do banco, {h}h às {h1}h, {n} ligações atendidas. Cada passo foi um teste, na ordem em que foi feito; os números saem de `scripts/investigar_espera.py`. Intervalo A: tempo até o atendente pegar a próxima ligação quando o cliente já esperava. Intervalo B: o mesmo, com alguém na fila o intervalo todo.",
        "iv_cols": "| Cenário | Espera média (s) | Atendidas em até {w} s | Mediana (s) |",
        "iv_1": "1. **Posições vazias: hipótese refutada.** A primeira explicação foi que nem todas as 8 posições estavam ocupadas. No dado há em média {pres} atendentes presentes na janela, e simular com eles deixa a espera ainda menor.",
        "iv_2": "2. **Intervalo entre ligações: explica pouco.** Com cliente esperando, o intervalo médio foi de {a} s (A) e {b} s (B). Somado a cada ligação sobre os atendentes medidos, a simulação continua abaixo da metade da espera real.",
        "iv_3": "3. **Pausas em bloco: explicam a ordem de grandeza, não o formato.** Tirar o atendente durante as pausas (corte principal de 5 min; 2 e 10 min como sensibilidade) leva os atendentes disponíveis de {pres} para {av5} e a espera média para {w5} s. A fração atendida na meta e a mediana continuam longe das reais, o resultado muda muito com o corte, e há circularidade: as pausas saem do próprio dia simulado.",
        "iv_4": "4. **Atraso fixo com gente livre: não encontrado.** Nas ligações sem ninguém à frente e com no máximo metade dos atendentes ocupada ({share} do total entre 7h e 24h), a mediana da espera foi {med} s (média {mean} s). O critério fixado antes, mediana de pelo menos {crit} s, não foi atendido.",
        "iv_end": "**Conclusão:** o motivo da diferença não está demonstrado. Para quem dimensiona equipe, contar só as pessoas presentes subestima a espera, e a forma como se trata as pausas muda muito o resultado. Não testado: pausas aprendidas em outros meses (o único teste destes que seria de previsão) e abandono. Combinações da tabela que chegam perto da média real não são tratadas como explicação, porque erram a fração atendida e a mediana.",
        "sw_h": "Quantos atendentes tornam a simulação parecida com o banco? (calibração)",
        "sw_cols": "| Agentes | Espera média simulada (s) | Atendidas em até {w} s (simulada) |",
        "sw_note": "Com **{n}** agentes a simulação chega mais perto da espera real do banco. Isso é uma **calibração**: esse número não é a quantidade de pessoas que havia no banco nem prova que o modelo está certo. O motivo da diferença não está demonstrado, e a simulação começa com a fila vazia no início da janela, o que a deixa mais otimista.",
        "mixed": "**Fontes misturadas:** o cenário padrão usa as chegadas do NYC 311 e o atendimento do Technion; as duas bases não têm relação entre si.",
        "assump": "Premissas fictícias usadas: atendimento de {aht} s e folga de {shr}.",
        "tol": "Tolerância declarada entre simulação e Erlang C: {tol}. Coeficiente de variação do atendimento lognormal: {cv}.",
    },
    "en": {
        "dec": ".", "thou": ",",
        "data": "### Data", "fcst": "### Hourly forecast (test year, out-of-sample)",
        "staff": "### Staff required per scenario (fictional assumptions)",
        "sim": "### Queue simulation × Erlang C (service level)",
        "mon": "### Intraday monitoring",
        "h_method": "Method", "rule": "Simple rule (average of the last 4 weeks)",
        "single": "Poisson model, fitted once on the training year",
        "monthly": "Poisson model, refitted every month with past data only",
        "gain": "Gain of the refitted model over the rule (WAPE)",
        "src": "Source", "period": "Train / test", "rows": "Rows read (all phone channel, no nulls or duplicates)",
        "hours": "Hours in the series",
        "sc": "Scenario", "ah_p": "Agent-hours present", "ah_s": "Agent-hours scheduled (with shrinkage)",
        "pk_p": "Peak present", "pk_s": "Peak scheduled",
        "hr": "Hour", "calls": "Forecast calls/h", "ag": "Agents", "erl": "Erlang C",
        "sx": "Simulation (exponential service)", "sl": "Simulation (lognormal service)",
        "peak": "peak", "median": "median", "valley": "valley",
        "thr": "Deviation threshold for an alert", "cmp": "Hours compared", "al": "Hours in alert",
        "day": "Day with most alerts", "wh": "Slack webhook configured in this run",
        "yes": "yes", "no": "no",
        "an_h": "### Input analyzer: service times (real Technion data)",
        "an_intro": "{n_total} real served calls ({n_used} used in the fit, random sample with a fixed seed). Ranking criterion fixed before running: AIC (lower is better).",
        "an_cols": "| Rank | Distribution | AIC | BIC | KS | Squared error | Parameters |",
        "an_prop": "Proposed distribution (best AIC): **{best}**. By squared error the best is **{sq}**: the criteria do not agree. The exponential, Erlang C's assumption, ranked {pos} by AIC. With hundreds of thousands of points any goodness-of-fit test rejects every candidate, so the p-value is not used to decide.",
        "arr_h": "### Input analyzer: NYC 311 arrivals (gaps between calls, weekdays)",
        "arr_cols": "| Band | Gaps (total) | Used in the fit | 1st | 2nd | 3rd |",
        "arr_note": "Each band mixes hours with different rates, so non-exponential gaps are expected; on its own that does not refute Poisson arrivals.",
        "val_h": "### Validation against the real bank (Technion)",
        "val_cols": "| Metric | Real | Simulated |",
        "val_wait": "Mean wait (s)", "val_sl": "Answered within {w} s",
        "val_info": "Window: bank weekdays, {h}h to {h1}h; {n} served calls over {d} days; {a} agents in the simulation; real abandonment in the window: {ab}.",
        "iv_h": "### Why doesn't the simulation reproduce the bank? (investigation)",
        "iv_intro": "Bank weekdays, {h}h to {h1}h, {n} served calls. Each step was a test, in the order it was run; the numbers come from `scripts/investigar_espera.py`. Gap A: time until the agent takes the next call when that caller was already waiting. Gap B: the same, with someone in the queue during the whole gap.",
        "iv_cols": "| Scenario | Mean wait (s) | Answered within {w} s | Median (s) |",
        "iv_1": "1. **Empty positions: hypothesis refuted.** The first explanation was that not all 8 positions were staffed. The data shows {pres} agents present on average in the window, and simulating with them makes the wait even shorter.",
        "iv_2": "2. **Gap between calls: explains little.** With a caller waiting, the mean gap was {a} s (A) and {b} s (B). Added to every call on top of the measured agents, the simulation stays below half of the real wait.",
        "iv_3": "3. **Breaks as blocks: they explain the order of magnitude, not the shape.** Removing the agent during breaks (main cut-off 5 min; 2 and 10 min as sensitivity) takes available agents from {pres} to {av5} and the mean wait to {w5} s. The share answered within target and the median stay far from the real ones, the result depends heavily on the cut-off, and there is circularity: the breaks come from the very day being simulated.",
        "iv_4": "4. **Fixed delay with idle agents: not found.** For calls with nobody ahead and at most half of the agents busy ({share} of calls between 7h and 24h), the median wait was {med} s (mean {mean} s). The criterion set beforehand, a median of at least {crit} s, was not met.",
        "iv_end": "**Conclusion:** the reason for the gap has not been established. For staffing, counting only the people present underestimates the wait, and how breaks are treated changes the result a lot. Not tested: breaks learned from other months (the only one of these that would be a forecast test) and abandonment. Table combinations that get close to the real mean are not treated as an explanation, because they miss the share answered and the median.",
        "sw_h": "How many agents make the simulation look like the bank? (calibration)",
        "sw_cols": "| Agents | Simulated mean wait (s) | Answered within {w} s (simulated) |",
        "sw_note": "With **{n}** agents the simulation gets closest to the bank's real wait. This is a **calibration**: that number is not how many people the bank had, nor proof that the model is right. The reason for the gap has not been established, and the simulation starts with an empty queue at the beginning of the window, which makes it more optimistic.",
        "mixed": "**Mixed sources:** the default scenario uses NYC 311 arrivals and Technion service times; the two datasets are unrelated to each other.",
        "assump": "Fictional assumptions used: {aht} s handling time and {shr} shrinkage.",
        "tol": "Declared tolerance between simulation and Erlang C: {tol}. Lognormal service coefficient of variation: {cv}.",
    },
}


def render(r: dict, lang: str) -> str:
    t = T[lang]

    def num(x, nd=0):
        s = f"{x:,.{nd}f}"
        return s.replace(",", "§").replace(".", t["dec"]).replace("§", t["thou"])

    def pct(x, nd=1):
        return num(x * 100, nd) + "%"

    d, f1, f2 = r["data"], r["forecast"]["ajuste_unico"], r["forecast"]["reajuste_mensal"]
    p = r["premissas_ficticias"]
    L = [t["data"], "", f"- {t['src']}: {d['fonte']}", f"- {t['period']}: {d['treino']} / {d['teste']}",
         f"- {t['rows']}: {num(d['rows_in'])}", f"- {t['hours']}: {num(d['horas_na_serie'])}", "",
         t["fcst"], "", f"| {t['h_method']} | WAPE | MAPE |", "|---|---:|---:|",
         f"| {t['rule']} | {pct(f2['wape_baseline'])} | {pct(f2['mape_baseline'])} |",
         f"| {t['single']} | {pct(f1['wape_model'])} | {pct(f1['mape_model'])} |",
         f"| {t['monthly']} | {pct(f2['wape_model'])} | {pct(f2['mape_model'])} |", "",
         f"{t['gain']}: {pct(f2['gain_wape_rel'])}", "",
         t["staff"], "", f"| {t['sc']} | {t['ah_p']} | {t['ah_s']} | {t['pk_p']} | {t['pk_s']} |", "|---|---:|---:|---:|---:|"]
    for s in r["staffing"]:
        L.append(f"| {s['scenario']} | {num(s['agent_hours_present'])} | {num(s['agent_hours_scheduled'])} | "
                 f"{num(s['peak_present'])} | {num(s['peak_scheduled'])} |")
    L += ["", t["assump"].format(aht=p["aht_seconds"], shr=pct(p["shrinkage"], 0)), "", t["sim"], "",
          f"| {t['hr']} | {t['sc']} | {t['calls']} | {t['ag']} | {t['erl']} | {t['sx']} | {t['sl']} |",
          "|---|---|---:|---:|---:|---:|---:|"]
    for c in r["simulation"]["casos"]:
        L.append(f"| {t[{'pico': 'peak', 'mediana': 'median', 'vale': 'valley'}[c['hora']]]} | {c['cenario']} | "
                 f"{num(c['chamadas_hora_prevista'], 1)} | {c['agentes_presentes']} | {pct(c['erlang'])} | "
                 f"{pct(c['sim_exp'])} | {pct(c['sim_lognormal'])} |")
    an = r["analisador"]["atendimento_technion"]
    names = [x["name"] for x in an["ranking"]]
    sq_best = min(an["ranking"], key=lambda x: x["sq_error"])["name"]
    L += ["", t["an_h"], "", t["an_intro"].format(n_total=num(an["n_total"]), n_used=num(an["n_usado"])), "",
          t["an_cols"], "|---:|---|---:|---:|---:|---:|---|"]
    for x in an["ranking"]:
        prm = "; ".join(f"{k}={num(v, 3)}" for k, v in x["params"].items())
        L.append(f"| {x['rank']} | {x['name']} | {num(x['aic'])} | {num(x['bic'])} | {num(x['ks_stat'], 3)} | {num(x['sq_error'] * 1e4, 2)}e-4 | {prm} |")
    L += ["", t["an_prop"].format(best=an["melhor"], sq=sq_best, pos=names.index("expon") + 1), "",
          t["arr_h"], "", t["arr_cols"], "|---|---:|---:|---|---|---|"]
    for c in r["analisador"]["chegadas_nyc"]:
        top = [x["name"] for x in c["ranking"]] + ["-"] * 3
        L.append(f"| {c['faixa']} | {num(c['n_total'])} | {num(c['n_usado'])} | {top[0]} | {top[1]} | {top[2]} |")
    v = r["validacao_banco"]
    L += ["", t["arr_note"], "", t["val_h"], "", t["val_cols"], "|---|---:|---:|",
          f"| {t['val_wait']} | {num(v['real_mean_wait_s'], 1)} | {num(v['sim_mean_wait_s'], 1)} |",
          f"| {t['val_sl'].format(w=v['meta_espera_s'])} | {pct(v['real_service_level'])} | {pct(v['sim_service_level'])} |", "",
          t["val_info"].format(h=v["hora"], h1=v["hora"] + 1, n=num(v["n_calls"]), d=num(v["n_days"]), a=v["agentes"], ab=pct(v["abandoned_share"])),
          ""]
    L += [t["sw_h"], "", t["sw_cols"].format(w=v["meta_espera_s"]), "|---:|---:|---:|"]
    for s_ in v["varredura"]:
        L.append(f"| {s_['agentes']} | {num(s_['sim_mean_wait_s'], 1)} | {pct(s_['sim_service_level'])} |")
    L += ["", t["sw_note"].format(n=v["agentes_mais_proximo_espera"])]
    iv = r["investigacao"]
    label = "rotulo_pt" if lang == "pt" else "rotulo_en"
    L += ["", t["iv_h"], "", t["iv_intro"].format(h=iv["hora"], h1=iv["hora"] + 1, n=num(iv["ligacoes_janela"])), "",
          t["iv_cols"].format(w=iv["meta_espera_s"]), "|---|---:|---:|---:|"]
    for c in iv["cenarios"]:
        j = c["janela"]
        L.append(f"| {c[label]} | {num(j['espera_media_s'], 1)} | {pct(j['nivel_servico'])} | {num(j['mediana_s'], 0)} |")
    av, gp, free = iv["disponiveis_na_janela"], iv["intervalos"], iv["livre"]
    w5 = next(c for c in iv["cenarios"] if c["chave"] == "pausas5")["janela"]["espera_media_s"]
    L += ["", t["iv_1"].format(pres=num(av["0"], 1)),
          t["iv_2"].format(a=num(gp["A"]["media_s"], 1), b=num(gp["B"]["media_s"], 1)),
          t["iv_3"].format(pres=num(av["0"], 1), av5=num(av["5"], 1), w5=num(w5, 1)),
          t["iv_4"].format(share=pct(free["dia"]["fracao_do_total"]), med=num(free["dia"]["mediana_s"], 0),
                           mean=num(free["dia"]["media_s"], 1), crit=free["criterio_mediana_s"]),
          "", t["iv_end"], "", t["mixed"]]
    sim = r["simulation"]
    L += ["", t["tol"].format(tol=num(sim["tolerancia"], 2), cv=num(sim["cv_lognormal"], 1)), "", t["mon"], "",
          f"- {t['thr']}: {pct(r['monitor']['limite_desvio'], 0)}", f"- {t['cmp']}: {num(r['monitor']['horas_comparadas'])}",
          f"- {t['al']}: {num(r['monitor']['horas_em_alerta'])}", f"- {t['day']}: {r['monitor']['dia_com_mais_alertas']}",
          f"- {t['wh']}: {t['yes'] if r['monitor']['webhook_configurado'] else t['no']}"]
    return "\n".join(L)


def update(path: Path, lang: str, results: dict) -> None:
    text = path.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN)
    tail = rest.split(END)[1]
    text = f"{head}{BEGIN}\n{render(results, lang)}\n{END}{tail}"
    if FLOW_BEGIN in text and FLOW_END in text:
        a, rest = text.split(FLOW_BEGIN, 1)
        text = f"{a}{FLOW_BEGIN}\n{flow_text(lang)}\n{FLOW_END}{rest.split(FLOW_END, 1)[1]}"
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    res = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
    update(ROOT / "README.md", "pt", res)
    update(ROOT / "README.en.md", "en", res)
    print("READMEs atualizados")





