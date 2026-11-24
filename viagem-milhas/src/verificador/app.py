"""Interface do Verificador de voos (Streamlit).

Abrir:  powershell -File scripts\\app.ps1
"""
import os
import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

# Funciona de qualquer pasta e sem PYTHONPATH: acha o codigo (src) e usa a raiz do projeto como pasta de trabalho.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(Path(__file__).resolve().parents[2])

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from verificador import collector  # noqa: E402
from verificador import promos
from verificador.programas import ProgramInput, evaluate, load_inputs, max_miles_worth, save_inputs
from verificador.calculator import estimated_bag_cost  # noqa: E402
from verificador.config import load_config  # noqa: E402
from verificador.places import describe_codes, looks_like_codes, search_places  # noqa: E402
from verificador.report import build_report  # noqa: E402
from verificador.setup import CABINS, build_config_toml, form_defaults, merge_existing, parse_form  # noqa: E402
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


def place_field(label: str, key: str, default: str, help_text: str = "") -> str:
    """Campo de lugar: aceita o codigo (GRU) ou o nome (Lisboa) e mostra as opcoes encontradas."""
    text = st.text_input(label, default, key=f"f_{key}", help=help_text,
                         placeholder="Cidade ou código (ex.: Lisboa ou LIS)").strip()
    codes = ""
    if text:
        if looks_like_codes(text):
            codes = ",".join(c.strip().upper() for c in text.split(","))
        else:
            results = search_places(text)
            if results:
                labels = {r.codes: r.label for r in results}
                codes = st.selectbox("Escolha o lugar", list(labels), format_func=labels.get, key=f"f_{key}_pick")
            else:
                st.caption("❌ Não achei esse lugar. Tente o nome da cidade ou o código do aeroporto.")
    if codes:
        st.caption("✔ " + describe_codes(codes))
    return codes or text


def run_consultation(cfg) -> None:
    """Faz a consulta, salva todas as ofertas e guarda o resultado na sessao (veja show_last_consult)."""
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        st.error("A variável de ambiente SERPAPI_KEY não está definida. Veja o aviso na aba Minha viagem.")
        return
    try:
        with st.spinner("Consultando o Google Voos..."):
            offers = collector.fetch_offers(cfg, api_key)
    except collector.CollectorError as exc:
        st.error(f"A consulta falhou: {exc}")
        return
    if not offers:
        st.warning("A busca não devolveu nenhuma oferta.")
        return
    previous = list_snapshots(cfg.paths.snapshots)
    path = save_snapshot(cfg.paths.snapshots, cfg, offers, "manual")
    st.session_state["last_consult"] = {"path": path, "older": previous[0].path if previous else None}


def show_last_consult(cfg, prefix: str) -> None:
    last = st.session_state.get("last_consult")
    if last and os.path.exists(last["path"]):
        st.success("Consulta salva.")
        older = next((m for m in list_snapshots(cfg.paths.snapshots) if m.path == last["older"]), None)
        show_result(load_snapshot(last["path"]), older, prefix, cfg)


cfg = load_cfg()
tab_trip, tab_now, tab_saved, tab_hist, tab_miles = st.tabs(
    ["Minha viagem", "Consultar agora", "Consultas salvas", "Histórico", "Milhas"])

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

    st.subheader("Ida")
    c1, c2, c3 = st.columns(3)
    with c1:
        origin = place_field("Origem (cidade ou código)", "origin", d["origin"], "Ex.: Rio de Janeiro, São Paulo ou GRU")
    with c2:
        dest = place_field("Destino (cidade ou código)", "dest", d["dest"], "Ex.: Lisboa, Londres, Nova York ou LIS")
    out_date = c3.date_input("Data da ida", d_or(d["out_date"], 60), key="f_out_date", format="DD/MM/YYYY")
    st.subheader("Volta")
    c1, c2, c3 = st.columns(3)
    with c1:
        back_from = place_field("Sai de (em branco = destino da ida)", "back_from", d["back_from"])
    with c2:
        back_to = place_field("Chega em (em branco = origem da ida)", "back_to", d["back_to"])
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
    save_clicked = st.button("Salvar viagem")
    consult_clicked = st.button("Salvar e consultar agora", type="primary")

    if save_clicked or consult_clicked:
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
            if cfg is not None:  # mantem feeds, limites de promocao, caminhos e envio da mala de mao ao salvar
                values = merge_existing(values, cfg)
            os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(build_config_toml(values))
            cfg = load_cfg()
            st.success(f"Viagem salva em {CONFIG_PATH}.")
            if consult_clicked:
                run_consultation(cfg)
                show_last_consult(cfg, "trip")

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
            run_consultation(cfg)
        show_last_consult(cfg, "now")

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

# ------------------------------------------------------------------------ Milhas
@st.cache_data(ttl=3600, show_spinner=False)
def scan_feeds(feeds: tuple, keywords: tuple, limits: tuple):
    entries = []
    for url in feeds:
        try:
            entries += promos.fetch_feed(url)
        except Exception:
            pass
    return promos.scan_promos(entries, list(keywords), dict(limits))


with tab_miles:
    if cfg is None:
        st.info("Salve a viagem na aba **Minha viagem** primeiro.")
    else:
        metas_m = list_snapshots(cfg.paths.snapshots)
        best_cash, fallback = None, False
        if metas_m:
            snap_m = load_snapshot(metas_m[0].path)
            best_cash = snap_m["best_total_brl"]
            if best_cash is None and snap_m["offers"]:  # nenhuma passa nas regras: usa a mais barata e avisa
                best_cash, fallback = min(o["total_price_brl"] for o in snap_m["offers"]), True
        if best_cash is None:
            st.info("Faça uma consulta (aba **Consultar agora**) para eu comparar as milhas com o preço em dinheiro da sua viagem.")
        else:
            bag = estimated_bag_cost(cfg.baggage)
            cash = best_cash + bag
            if fallback:
                st.warning("Nenhuma oferta da última consulta passa nas suas regras de escala; estou usando a mais barata de todas como referência.")
            st.write(f"Viagem **{cfg.trip.outbound[0]} → {cfg.trip.outbound[1]}** · melhor preço em dinheiro da última consulta "
                     f"({metas_m[0].saved_at.strftime('%d/%m/%Y %H:%M')}): **{format_brl(best_cash)}**"
                     + (f" + malas estimadas {format_brl(bag)} = **{format_brl(cash)}**" if bag else ""))
            with st.expander("Ajustar taxas das milhas (opcional)"):
                taxes = st.number_input("Taxas em dinheiro da passagem de milhas (R$)", 0.0, 1_000_000.0, 0.0, 50.0, key="m_taxes",
                                        help="As passagens de milhas também cobram taxas. Deixe 0 se não souber.")
            found = scan_feeds(tuple(cfg.promos.feeds), tuple(cfg.promos.keywords), tuple(cfg.promos.max_milheiro.items()))
            best_promo = {}
            for f in found:
                if f.program not in best_promo or f.milheiro_brl < best_promo[f.program]:
                    best_promo[f.program] = f.milheiro_brl
            progs_path = os.path.join(os.path.dirname(cfg.paths.history) or "data", "milhas_programas.csv")
            today_iso = date.today().isoformat()
            base = load_inputs(progs_path, list(cfg.promos.max_milheiro))
            origins = {}
            for i in base:
                if i.program in best_promo:
                    origins[i.program] = "promoção achada hoje"
                elif i.milheiro_brl > 0:
                    origins[i.program] = f"anotado em {i.price_date[8:]}/{i.price_date[5:7]}" if i.price_date else "anotado por você"
                else:
                    origins[i.program] = "sem preço: anote"
            BUY_PAGES = {
                "smiles": "https://www.smiles.com.br/comprar-milhas",
                "livelo": "https://www.livelo.com.br/compre-pontos",
                "tap": "https://www.flytap.com/pt-br/milesandgo",
                "flying blue": "https://www.flyingblue.com/pt/earn/buy-miles",
            }
            with st.expander("Como atualizar o preço de compra de cada programa (precisa de login)", expanded=False):
                st.markdown(
                    "Os sites dos programas só mostram o preço do milheiro **depois do login**, e o login é sempre seu "
                    "(o programa e o Claude nunca digitam sua senha).\n\n"
                    "1. Clique nos botões abaixo e **entre na sua conta** em cada site, no Chrome.\n"
                    "2. **Deixe as abas abertas.**\n"
                    "3. Volte aqui e peça ao Claude: *\"leia o preço do milheiro nas abas abertas e anote no painel\"*. "
                    "Ele só lê o preço, não compra nada.\n"
                    "4. Ou anote você mesmo na tabela abaixo e clique em **Salvar saldos e preços**.")
                cols = st.columns(max(1, len(cfg.promos.max_milheiro)))
                for col, name in zip(cols, cfg.promos.max_milheiro):
                    if name in BUY_PAGES:
                        col.link_button(f"Abrir {name}", BUY_PAGES[name])
            st.subheader("Suas milhas e o preço de compra de cada programa")
            st.caption("O preço do milheiro é atualizado sozinho quando um blog publica promoção; senão vale o último que você anotou. "
                       "Preencha o saldo que você já tem e, se souber, as milhas que a passagem pede.")
            edited = st.data_editor(
                pd.DataFrame([{
                    "Programa": i.program, "Saldo de milhas": i.balance,
                    "Preço atual do milheiro (R$)": best_promo.get(i.program, i.milheiro_brl),
                    "Bônus de transferência (%)": i.bonus_pct, "Milhas que a passagem pede": i.miles,
                } for i in base]),
                hide_index=True, disabled=["Programa"], key="m_editor",
                column_config={"Saldo de milhas": st.column_config.NumberColumn(min_value=0, step=1000),
                               "Preço atual do milheiro (R$)": st.column_config.NumberColumn(format="R$ %.2f", min_value=0.0),
                               "Bônus de transferência (%)": st.column_config.NumberColumn(min_value=0.0),
                               "Milhas que a passagem pede": st.column_config.NumberColumn(min_value=0, step=1000)})
            by_name = {i.program: i for i in base}
            inputs = []
            for _, r in edited.iterrows():
                old = by_name[r["Programa"]]
                price = float(r["Preço atual do milheiro (R$)"])
                changed = price != old.milheiro_brl
                inputs.append(ProgramInput(r["Programa"], price, float(r["Bônus de transferência (%)"]),
                                           int(r["Milhas que a passagem pede"]), taxes, int(r["Saldo de milhas"]),
                                           today_iso if changed else old.price_date))
            rows = []
            for i in inputs:
                res = evaluate(i, cash)
                limit_miles = max_miles_worth(cash, taxes, res.effective_milheiro) if res.effective_milheiro else (
                    max_miles_worth(cash, taxes, i.milheiro_brl / (1 + i.bonus_pct / 100)) if i.milheiro_brl > 0 else None)
                rows.append({
                    "Programa": i.program,
                    "Saldo": f"{i.balance:,}".replace(",", "."),
                    "Preço atual do milheiro": format_brl(i.milheiro_brl) if i.milheiro_brl > 0 else "—",
                    "Origem do preço": origins[i.program],
                    "Compensa se a passagem pedir até": f"{limit_miles:,} milhas".replace(",", ".") if limit_miles else "—",
                    "Comprando só o que falta": format_brl(res.miles_cost_brl) if res.miles_cost_brl else "—",
                    "Resultado": "—" if res.saving_brl is None else (
                        f"Milhas ganham ({format_brl(res.saving_brl)} de economia)" if res.miles_win
                        else f"Dinheiro ganha ({format_brl(-res.saving_brl)} a menos)"),
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            st.subheader("Simulador: e se eu comprar milhas a este preço?")
            st.caption("Os sites dos programas não mostram o preço do milheiro sem login (a página da Smiles, por exemplo, só mostra o bônus). "
                       "Digite o preço que você viu e veja como a viagem ficaria; preencha acima as milhas que a passagem pede.")
            sim_price = st.number_input("Preço do milheiro para simular (R$)", 0.0, 1000.0, 25.0, 0.5, key="m_sim_price")
            sim_rows = []
            for i in inputs:
                if i.miles <= 0:
                    sim_rows.append({"Programa": i.program, "Custo da viagem em milhas": "informe as milhas da passagem", "Resultado": "—"})
                    continue
                res = evaluate(replace(i, milheiro_brl=sim_price), cash)
                sim_rows.append({
                    "Programa": i.program, "Custo da viagem em milhas": format_brl(res.miles_cost_brl),
                    "Resultado": "—" if res.saving_brl is None else (
                        f"Milhas ganham ({format_brl(res.saving_brl)} de economia)" if res.miles_win
                        else f"Dinheiro ganha ({format_brl(-res.saving_brl)} a menos)")})
            st.dataframe(pd.DataFrame(sim_rows), hide_index=True)
            with_miles = [i for i in inputs if i.miles > 0]
            if with_miles:
                prices = [10, 15, 20, 25, 30, 35, 40]
                st.caption("Custo da viagem em milhas conforme o preço do milheiro:")
                st.dataframe(pd.DataFrame([{"Programa": i.program, **{f"R$ {p}": format_brl(evaluate(replace(i, milheiro_brl=float(p)), cash).miles_cost_brl)
                                                                      for p in prices}} for i in with_miles]), hide_index=True)
            if st.button("Salvar saldos e preços", key="m_save_panel"):
                save_inputs(progs_path, inputs)
                st.success("Salvo. Da próxima vez que abrir, está tudo aqui.")
            if found:
                st.subheader("Promoções achadas agora")
                st.dataframe(
                    pd.DataFrame([{"Programa": f.program, "Milheiro (R$)": f.milheiro_brl, "Título": f.title, "Link": f.link}
                                  for f in sorted(found, key=lambda f: f.milheiro_brl)]),
                    hide_index=True,
                    column_config={"Milheiro (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                                   "Link": st.column_config.LinkColumn("Link")})
            else:
                st.caption("Nenhuma promoção com preço de milheiro nos blogs agora.")
