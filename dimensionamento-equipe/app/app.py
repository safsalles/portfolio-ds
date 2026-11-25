"""App local: analisador de entrada + simulador de filas customizável.

Abre já com tudo pronto (só usa results/results.json e data/exemplos). Carregar o seu
próprio arquivo é opcional. Rodar com:  streamlit run app/app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app import logic  # noqa: E402
from src.distributions import DISTRIBUTIONS, DistSpec  # noqa: E402

st.set_page_config(page_title="Simulador de filas (WFM)", layout="wide")

PARAM_HELP = {"mean": "média (s)", "cv": "coef. de variação", "shape": "forma", "scale": "escala (s)", "k": "k (inteiro)",
              "sd": "desvio-padrão (s)", "low": "mínimo (s)", "mode": "moda (s)", "high": "máximo (s)", "a": "a", "b": "b"}


@st.cache_data
def defaults():
    return logic.load_defaults(ROOT)


@st.cache_data
def cached_sweep(svc, svc_params, arr, arr_params, cph, wait, target, n_calls, lo, hi):
    """Varredura do número de agentes (em cache: só refaz se o cenário mudar)."""
    service = DistSpec(svc, dict(svc_params))
    arrival = DistSpec(arr, dict(arr_params)) if arr else None
    return logic.sweep_agents(service, arrival, cph, wait, target, range(lo, hi + 1), n_calls=n_calls)


d = defaults()
proposal = d["proposal"]

st.title("Simulador de filas com analisador de entrada")
st.caption("Cenário didático de Workforce Management. Equipe, tempo de atendimento, folga e metas são fictícios.")
st.header("De onde vêm os dados e por quê")
st.mermaid_chart(
    (ROOT / "app" / "fluxo_dados.pt.mmd").read_text(encoding="utf-8"),
    alt="Fluxo dos dados: o NYC 311 dá as chegadas e alimenta previsão e Erlang C; o Technion dá os tempos de atendimento, alimenta o analisador, o simulador e a validação",
)
st.markdown(d["source_note"])

with st.expander("O que é a base do Technion e por que a usamos"):
    st.markdown(
        "É o registro de todas as ligações de um call center de banco em Israel, em 1999: hora de entrada, espera na fila, resultado "
        "e **tempo real de atendimento**. Foi usada porque são poucas as bases públicas com tempos de atendimento reais; o NYC 311 só "
        "traz chegadas. Limites: é antiga, é de outro país e parte dos clientes desiste da fila (o simulador não modela abandono). "
        "Fonte: Technion SEE Center, documentação de I. Guedj e A. Mandelbaum (2000). Detalhes em `data/exemplos/FONTES.md`."
    )

# ---------------------------------------------------------------- 1. Analisador
st.header("1. Analisador de entrada: tempo de atendimento")
override = None
tab_default, tab_upload = st.tabs(["Base do Technion (padrão)", "Meu arquivo (opcional)"])

with tab_default:
    rows = pd.DataFrame(d["fits"])
    rows["parâmetros"] = rows["params"].apply(lambda p: "; ".join(f"{k}={v:.3f}" for k, v in p.items()))
    st.dataframe(
        rows[["rank", "name", "aic", "bic", "ks_stat", "sq_error", "parâmetros"]].rename(
            columns={"rank": "posição", "name": "distribuição", "ks_stat": "KS", "sq_error": "erro quadrático"}
        ),
        hide_index=True,
    )
    best_sq = min(d["fits"], key=lambda x: x["sq_error"])["name"]
    st.markdown(
        f"Distribuição proposta (melhor AIC, critério fixado antes de rodar): **{proposal.dist}**. "
        f"Pelo erro quadrático a melhor é **{best_sq}**: os critérios não concordam. Você pode testar outra no cenário abaixo."
    )
    top = [(f"{x['rank']}. {x['name']}", DistSpec(x["name"], x["params"])) for x in d["fits"][:3]]
    st.pyplot(logic.plot_fits(d["service_values"], top))

with tab_upload:
    st.write("Opcional: carregue um CSV com uma coluna de tempos (em segundos). Vírgula decimal e cabeçalho são aceitos.")
    up = st.file_uploader("Arquivo CSV ou TXT", type=["csv", "txt"])
    col = st.text_input("Nome da coluna (deixe vazio para usar a primeira)", value="")
    if up is not None:
        res = logic.analyze_upload(up.getvalue(), col.strip() or None)
        if "error" in res:
            st.error(res["error"])
        else:
            st.success(f"{res['report']['kept']} valores usados. Descartados: {res['report']}")
            st.dataframe(
                pd.DataFrame(
                    [{"posição": f.rank, "distribuição": f.name, "AIC": f.aic, "BIC": f.bic, "KS": f.ks_stat, "erro quadrático": f.sq_error}
                     for f in res["fits"]]
                ),
                hide_index=True,
            )
            st.pyplot(logic.plot_fits(res["values"], [(f"{f.rank}. {f.name}", f.spec) for f in res["fits"][:3]]))
            choice = st.selectbox("Usar no cenário", [f"{f.rank}. {f.name}" for f in res["fits"]])
            override = res["fits"][int(choice.split(".")[0]) - 1].spec

# ---------------------------------------------------------------- 2. Cenário
st.header("2. Monte o seu cenário")
base = override or proposal
dists = list(DISTRIBUTIONS)
c1, c2 = st.columns(2)
with c1:
    st.subheader("Tempo de atendimento")
    dist = st.selectbox("Distribuição", dists, index=dists.index(base.dist), key=f"svc_{base.dist}")
    defaults_by_dist = {
        "expon": {"mean": d["mean_service"]}, "lognormal": {"mean": d["mean_service"], "cv": 1.0},
        "gamma": {"mean": d["mean_service"], "cv": 1.0}, "weibull": {"shape": 1.0, "scale": d["mean_service"]},
        "erlang": {"k": 2, "mean": d["mean_service"]}, "normal": {"mean": d["mean_service"], "sd": d["mean_service"] / 3},
        "triangular": {"low": 10.0, "mode": d["mean_service"] / 2, "high": d["mean_service"] * 3},
        "uniform": {"low": 10.0, "high": d["mean_service"] * 2},
        "beta": {"low": 10.0, "high": d["mean_service"] * 4, "a": 1.2, "b": 4.0},
    }
    init = base.params if dist == base.dist else defaults_by_dist[dist]
    params = {p: st.number_input(PARAM_HELP.get(p, p), value=float(init[p]), key=f"p_{dist}_{p}", format="%.4f")
              for p in DISTRIBUTIONS[dist]}
with c2:
    st.subheader("Chegadas e equipe")
    mode = st.radio("Chegadas", ["Poisson (pela taxa)", "Intervalo entre chegadas com distribuição própria"])
    cph = st.number_input("Chamadas por hora", min_value=1.0, value=float(d["calls_per_hour"]), key="cph")
    arrival = None
    if mode != "Poisson (pela taxa)":
        a_dist = st.selectbox("Distribuição do intervalo (s)", dists, index=dists.index("gamma"))
        mean_gap = 3600.0 / cph
        a_init = {"expon": {"mean": mean_gap}, "gamma": {"mean": mean_gap, "cv": 1.0},
                  "lognormal": {"mean": mean_gap, "cv": 1.0}, "weibull": {"shape": 1.0, "scale": mean_gap},
                  "erlang": {"k": 2, "mean": mean_gap}, "normal": {"mean": mean_gap, "sd": mean_gap / 3},
                  "triangular": {"low": 1.0, "mode": mean_gap / 2, "high": mean_gap * 3},
                  "uniform": {"low": 1.0, "high": mean_gap * 2}, "beta": {"low": 1.0, "high": mean_gap * 4, "a": 1.2, "b": 4.0}}[a_dist]
        a_params = {p: st.number_input(f"{PARAM_HELP.get(p, p)} (intervalo)", value=float(a_init[p]), key=f"a_{a_dist}_{p}", format="%.4f")
                    for p in DISTRIBUTIONS[a_dist]}
        arrival = DistSpec(a_dist, a_params)
    agents = st.number_input("Agentes", min_value=1, value=int(d["agents"]), step=1, key="agents")
    wait = st.number_input("Meta: atender em até (s)", min_value=0, value=20, step=5, key="wait")
    target = st.slider("... em pelo menos esta fração das chamadas", 0.5, 0.99, 0.80, 0.01, key="target")

n_calls = st.number_input("Chamadas simuladas por réplica", min_value=1000, value=20000, step=1000, key="n_calls")
try:
    with st.spinner("Simulando..."):
        out = logic.simulate(DistSpec(dist, params), arrival, cph, int(agents), int(wait), float(target), int(n_calls))
    if "warning" in out:
        st.warning(out["warning"])
    if out["capped"]:
        st.info(f"Limitei a simulação a {logic.MAX_CALLS:,} chamadas por réplica.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Nível de serviço simulado", f"{out['sim_mean']:.1%}", f"IC 95%: {out['sim_ci_low']:.1%} a {out['sim_ci_high']:.1%}", delta_color="off")
    m2.metric("Meta", f"{target:.0%} em {int(wait)} s", "atingida" if out["meets_target"] else "não atingida", delta_color="off")
    m3.metric("Erlang C", f"{out['erlang']:.1%}" if out["erlang"] is not None else "não se aplica")
    if out["erlang"] is None:
        st.caption("O Erlang C só vale com atendimento exponencial e chegadas de Poisson; com outra distribuição, só a simulação responde.")
    st.header("3. E se contratar ou demitir?")
    st.caption("Mantém o cenário acima e muda só o número de agentes. As faixas instáveis (carga maior que a equipe) aparecem em vermelho.")
    lo, hi = max(1, int(agents) - 6), int(agents) + 8
    sweep = cached_sweep(
        dist, tuple(sorted(params.items())), arrival.dist if arrival else None,
        tuple(sorted(arrival.params.items())) if arrival else (), float(cph), int(wait), float(target), int(n_calls), lo, hi,
    )
    cur = sweep.loc[sweep["agents"] == int(agents)].iloc[0]
    cols = st.columns(5)
    for col, delta, label in zip(cols, (-2, -1, 0, 1, 2), ("Demitir 2", "Demitir 1", "Equipe atual", "Contratar 1", "Contratar 2")):
        row = sweep.loc[sweep["agents"] == int(agents) + delta]
        if row.empty:
            col.metric(label, "—")
            continue
        r_ = row.iloc[0]
        col.metric(f"{label} ({int(r_['agents'])})", f"{r_['service_level']:.1%}",
                   None if delta == 0 else f"{(r_['service_level'] - cur['service_level']) * 100:+.1f} p.p.", border=True)
        col.caption(f"espera média: {min(r_['wait_mean_s'], 999):.0f} s" + (" (instável)" if not r_["stable"] else ""))
    need = logic.min_agents_for_target(sweep, float(target))
    st.markdown(
        f"Pela simulação, o **menor número de agentes que atinge a meta** é **{need}**." if need is not None
        else f"Nenhum número de agentes entre {lo} e {hi} atinge a meta de {target:.0%} em {int(wait)} s."
    )
    plot = sweep.assign(status=sweep["stable"].map({True: "estável", False: "instável"}), espera=sweep["wait_mean_s"].clip(upper=600))
    sl_chart = (
        alt.Chart(plot).mark_line(point=True, color="#7aa2d6").encode(
            x=alt.X("agents:Q", title="Agentes"), y=alt.Y("service_level:Q", title="Nível de serviço", axis=alt.Axis(format="%")),
            color=alt.Color("status:N", scale=alt.Scale(domain=["estável", "instável"], range=["#7aa2d6", "#d65a5a"]), title=None),
            tooltip=["agents", alt.Tooltip("service_level:Q", format=".1%"), alt.Tooltip("wait_mean_s:Q", format=".0f")],
        )
        + alt.Chart(pd.DataFrame({"y": [float(target)]})).mark_rule(strokeDash=[6, 4], color="#e0b341").encode(y="y:Q")
        + alt.Chart(pd.DataFrame({"x": [int(agents)]})).mark_rule(color="#888888").encode(x="x:Q")
    )
    st.altair_chart(sl_chart, alt="Nível de serviço simulado por número de agentes; linha tracejada é a meta e a linha cinza é a equipe atual")
    wait_chart = (
        alt.Chart(plot).mark_line(point=True, color="#7aa2d6").encode(
            x=alt.X("agents:Q", title="Agentes"), y=alt.Y("espera:Q", title="Espera média (s, truncada em 600)"),
            color=alt.Color("status:N", scale=alt.Scale(domain=["estável", "instável"], range=["#7aa2d6", "#d65a5a"]), title=None),
        )
        + alt.Chart(pd.DataFrame({"x": [int(agents)]})).mark_rule(color="#888888").encode(x="x:Q")
    )
    st.altair_chart(wait_chart, alt="Espera média simulada por número de agentes; a linha cinza é a equipe atual")
except ValueError as exc:
    st.error(f"Parâmetros inválidos: {exc}")

# ---------------------------------------------------------------- 4. Validação
st.header("4. Validação contra o banco real")
v = d["validation"]
if v:
    st.table(pd.DataFrame(
        {"Real": [f"{v['real_mean_wait_s']:.1f}", f"{v['real_service_level']:.1%}"],
         "Simulada": [f"{v['sim_mean_wait_s']:.1f}", f"{v['sim_service_level']:.1%}"]},
        index=["Espera média (s)", f"Atendidas em até {v['meta_espera_s']} s"],
    ))
    st.caption(f"{v['n_calls']:,} ligações atendidas em {v['n_days']} dias, {v['hora']}h às {v['hora'] + 1}h, {v['agentes']} agentes "
               f"na simulação; abandono real na janela: {v['abandoned_share']:.1%}. {v['ressalva']}")
    ratio = v["sim_mean_wait_s"] / v["real_mean_wait_s"]
    st.warning(
        title="Real e simulado estão distantes",
        body=f"Com os {v['agentes']} atendentes da documentação, a simulação dá {ratio:.0%} da espera real: ela é otimista demais. "
             "O motivo não está demonstrado. A simulação não modela abandono, pausas nem pós-atendimento, e começa com a fila vazia no início "
             "da janela, o que a deixa mais otimista. Por isso o app não deve ser lido como previsão da espera de um banco real.",
    )
    sweep_v = pd.DataFrame(v.get("varredura", []))
    if not sweep_v.empty:
        nearest = int(v["agentes_mais_proximo_espera"])
        base = alt.Chart(sweep_v).mark_line(point=True, color="#7aa2d6").encode(
            x=alt.X("agentes:Q", title="Agentes na simulação"), y=alt.Y("sim_mean_wait_s:Q", title="Espera média (s)"),
            tooltip=["agentes", alt.Tooltip("sim_mean_wait_s:Q", format=".1f"), alt.Tooltip("sim_service_level:Q", format=".1%")],
        )
        real = alt.Chart(pd.DataFrame({"y": [v["real_mean_wait_s"]]})).mark_rule(strokeDash=[6, 4], color="#e0b341").encode(y="y:Q")
        st.altair_chart(base + real, alt="Espera média simulada por número de agentes, com a espera real do banco como linha tracejada")
        st.caption(
            f"Linha tracejada: espera real. Com **{nearest}** agentes a simulação chega mais perto dela. Isso é uma **calibração**: esse número "
            "não é a quantidade de pessoas que havia no banco nem prova que o modelo está certo."
        )



