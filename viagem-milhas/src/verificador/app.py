"""Interface do Verificador de voos (Streamlit).

Abrir:  powershell -File scripts\\app.ps1
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Funciona de qualquer pasta e sem PYTHONPATH: acha o codigo (src) e usa a raiz do projeto como pasta de trabalho.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(Path(__file__).resolve().parents[2])

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from verificador import collector  # noqa: E402
from verificador.calculator import estimated_bag_cost  # noqa: E402
from verificador.config import load_config  # noqa: E402
from verificador.report import build_report  # noqa: E402
from verificador.setup import CABINS, build_config_toml, form_defaults, parse_form  # noqa: E402
from verificador.snapshots import compare_best, list_snapshots, load_snapshot, offer_rows, save_snapshot  # noqa: E402
from verificador.ui_helpers import delta_text, format_brl, snapshot_label  # noqa: E402

CONFIG_PATH = os.environ.get("VERIFICADOR_CONFIG", "config.toml")
LABELS = {
    "origin": "Origem da ida", "dest": "Destino da ida", "out_date": "Data da ida",
    "back_from": "A volta sai de", "back_to": "A volta chega em", "back_date": "Data da volta",
    "adults": "Passageiros", "cabin": "Classe", "carry_on": "Malas de mão", "checked": "Malas despachadas",
    "fee": "Preço da mala", "hours": "Escala mínima", "max_hours": "Escala máxima", "avoid": "Aeroportos a evitar",
    "currency": "Moeda",
    "drop": "Queda para avisar", "target": "Valor-alvo",
}

st.set_page_config(page_title="Verificador de voos", page_icon="✈️", layout="wide")
st.title("✈️ Verificador de voos")


def load_cfg():
    return load_config(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else None


def show_result(snap: dict, older, prefix: str, cfg) -> None:
    best = snap["best_total_brl"]
    passing = sum(1 for o in snap["offers"] if o["compliant"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Melhor preço que passa nas regras", format_brl(best))
    c2.metric("Ofertas que passam / total", f"{passing} / {len(snap['offers'])}")
    if older is not None:
        c3.metric("Em relação à consulta anterior", delta_text(compare_best(best, older.best_total_brl)))
    if best is not None and cfg is not None and cfg.baggage.checked > 0:
        bag = estimated_bag_cost(cfg.baggage)
        st.caption(f"Com bagagem despachada estimada (+{format_brl(bag)}): **{format_brl(best + bag)}**")
    only_ok = st.checkbox("Mostrar só as que passam nas regras", key=f"{prefix}_only")
    rows = [r for r in offer_rows(snap) if not only_ok or r["Passa nas regras"] == "Sim"]
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        column_config={"Total (R$)": st.column_config.NumberColumn(format="R$ %.2f")},
    )


cfg = load_cfg()
tab_trip, tab_now, tab_saved, tab_hist = st.tabs(["Minha viagem", "Consultar agora", "Consultas salvas", "Histórico"])

# ---------------------------------------------------------------- Minha viagem
with tab_trip:
    st.write("Escolha a viagem que o verificador vai acompanhar. Ao salvar, a configuração é gravada em "
             f"`{CONFIG_PATH}`.")
    if os.environ.get("SERPAPI_KEY"):
        st.caption("Chave da SerpApi: definida ✅")
    else:
        st.warning("A variável de ambiente SERPAPI_KEY ainda não está definida. Crie uma conta gratuita em "
                   "serpapi.com e rode `setx SERPAPI_KEY \"SUA_CHAVE\"` (depois reabra o terminal).")
    d = form_defaults(cfg)
    today = date.today()

    def d_or(text: str, offset_days: int) -> date:
        return date.fromisoformat(text) if text else today + timedelta(days=offset_days)

    with st.form("viagem"):
        st.subheader("Ida")
        c1, c2, c3 = st.columns(3)
        origin = c1.text_input("Origem (3 letras, ex.: GRU)", d["origin"], key="f_origin")
        dest = c2.text_input("Destino (ex.: LIS)", d["dest"], key="f_dest")
        out_date = c3.date_input("Data da ida", d_or(d["out_date"], 60), key="f_out_date", format="DD/MM/YYYY")
        st.subheader("Volta")
        c1, c2, c3 = st.columns(3)
        back_from = c1.text_input("Sai de (em branco = destino da ida)", d["back_from"], key="f_back_from")
        back_to = c2.text_input("Chega em (em branco = origem da ida)", d["back_to"], key="f_back_to")
        back_date = c3.date_input("Data da volta", d_or(d["back_date"], 74), key="f_back_date", format="DD/MM/YYYY")
        st.subheader("Passageiros e bagagem")
        c1, c2, c3, c4 = st.columns(4)
        adults = c1.number_input("Passageiros adultos", 1, 9, int(d["adults"]), 1, key="f_adults")
        cabin = c2.selectbox("Classe", CABINS, index=CABINS.index(d["cabin"]) if d["cabin"] in CABINS else 0, key="f_cabin")
        carry_on = c3.number_input("Malas de mão (por pessoa)", 0, 5, int(d["carry_on"]), 1, key="f_carry_on")
        checked = c4.number_input("Malas despachadas (por trecho)", 0, 5, int(d["checked"]), 1, key="f_checked")
        fee = st.number_input("Preço estimado de UMA mala despachada, por trecho (R$)", 0.0, 100000.0,
                              float(d["fee"]), 50.0, key="f_fee")
        st.subheader("Regras e avisos")
        c1, c2, c3, c4 = st.columns(4)
        hours = c1.number_input("Escala mínima (horas)", 0.0, 48.0, float(d["hours"]), 0.5, key="f_hours",
                                help="Use 4 se precisa passar pela imigração. 0 = sem mínimo.")
        max_hours = c2.number_input("Escala máxima (horas)", 0.0, 96.0, float(d["max_hours"]), 0.5, key="f_max_hours",
                                    help="Quanto tempo você aceita ficar parado numa conexão. 0 = sem limite.")
        avoid = c3.text_input("Aeroportos onde NÃO aceita escala (opcional)", d["avoid"], key="f_avoid")
        currency = c4.text_input("Moeda", d["currency"], key="f_currency")
        c1, c2 = st.columns(2)
        drop = c1.number_input("Avisar se o preço cair (%)", 0.1, 100.0, float(d["drop"]), 0.5, key="f_drop")
        target = c2.number_input("Avisar se ficar abaixo de (0 = desligado)", 0.0, 10_000_000.0,
                                 float(d["target"]), 100.0, key="f_target")
        submitted = st.form_submit_button("Salvar viagem")

    if submitted:
        raw = {
            "origin": origin, "dest": dest, "out_date": out_date.isoformat(),
            "back_from": back_from, "back_to": back_to, "back_date": back_date.isoformat(),
            "adults": adults, "cabin": cabin, "carry_on": carry_on, "checked": checked, "fee": fee,
            "hours": hours, "max_hours": max_hours, "avoid": avoid, "currency": currency, "drop": drop,
            "target": target,
        }
        values, errors = parse_form(raw, today)
        if errors:
            for key, message in errors.items():
                st.error(f"**{LABELS.get(key, key)}:** {message}")
        else:
            os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(build_config_toml(values))
            cfg = load_cfg()
            st.success(f"Viagem salva em {CONFIG_PATH}. Já pode consultar na aba **Consultar agora**.")

# ------------------------------------------------------------ Consultar agora
with tab_now:
    if cfg is None:
        st.info("Salve a viagem na aba **Minha viagem** primeiro.")
    else:
        t = cfg.trip
        st.write(f"**{t.outbound[0]} → {t.outbound[1]}** em {t.outbound[2]} · volta **{t.inbound[0]} → {t.inbound[1]}** "
                 f"em {t.inbound[2]} · {t.adults} adulto(s)")
        st.caption("Cada consulta usa até 4 das 250 consultas gratuitas do mês na SerpApi e fica guardada em "
                   "**Consultas salvas**, para você rever depois.")
        if st.button("Consultar agora", type="primary"):
            api_key = os.environ.get("SERPAPI_KEY")
            if not api_key:
                st.error("A variável de ambiente SERPAPI_KEY não está definida. Veja o aviso na aba Minha viagem.")
            else:
                try:
                    with st.spinner("Consultando o Google Voos..."):
                        offers = collector.fetch_offers(cfg, api_key)
                except collector.CollectorError as exc:
                    st.error(f"A consulta falhou: {exc}")
                else:
                    if not offers:
                        st.warning("A busca não devolveu nenhuma oferta.")
                    else:
                        previous = list_snapshots(cfg.paths.snapshots)
                        path = save_snapshot(cfg.paths.snapshots, cfg, offers, "manual")
                        st.session_state["last_consult"] = {
                            "path": path,
                            "older": previous[0].path if previous else None,
                        }
        last = st.session_state.get("last_consult")
        if last and os.path.exists(last["path"]):
            st.success("Consulta salva.")
            older = next((m for m in list_snapshots(cfg.paths.snapshots) if m.path == last["older"]), None)
            show_result(load_snapshot(last["path"]), older, "now", cfg)

# ------------------------------------------------------------ Consultas salvas
with tab_saved:
    metas = list_snapshots(cfg.paths.snapshots if cfg else "data/snapshots")
    if not metas:
        st.info("Ainda não há consultas salvas. A rotina diária e o botão **Consultar agora** gravam cada consulta aqui.")
    else:
        i = st.selectbox("Consulta", range(len(metas)), format_func=lambda n: snapshot_label(metas[n]), key="saved_pick")
        older = metas[i + 1] if i + 1 < len(metas) else None
        if older is not None:
            st.caption(f"Comparando com a consulta anterior: {snapshot_label(older)}")
        show_result(load_snapshot(metas[i].path), older, "saved", cfg)

# -------------------------------------------------------------------- Histórico
with tab_hist:
    history_path = cfg.paths.history if cfg else "data/history.csv"
    if not os.path.exists(history_path):
        st.info("Ainda não há histórico. Ele é gravado todo dia pela rotina das 08:00.")
    else:
        df = pd.read_csv(history_path)
        ok = df[df["status"] == "ok"].copy()
        if not ok.empty:
            ok["date"] = pd.to_datetime(ok["date"])
            st.subheader("Menor preço por dia (R$)")
            st.line_chart(ok.set_index("date")["total_price_brl"])
        st.dataframe(df, hide_index=True)
    others = os.path.join(os.path.dirname(history_path) or "data", "outras_fontes.csv")
    bag_cost = estimated_bag_cost(cfg.baggage) if cfg else 0.0
    st.subheader("Relatório")
    st.code(build_report(history_path, others, bag_cost), language=None)
    alerts_log = cfg.paths.alerts_log if cfg else "data/alerts.log"
    if os.path.exists(alerts_log):
        st.subheader("Avisos recentes")
        with open(alerts_log, encoding="utf-8", errors="replace") as f:
            st.code("".join(f.readlines()[-10:]), language=None)
