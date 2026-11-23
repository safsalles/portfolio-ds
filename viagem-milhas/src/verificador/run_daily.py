import os
import sys
from datetime import date
from pathlib import Path

from verificador.alerts import notify, price_alerts
from verificador.collector import CollectorError, fetch_offers
from verificador.config import Config, load_config
from verificador.history import HistoryRecord, has_ok_record, last_price, upsert_record
from verificador.models import Offer
from verificador.promos import fetch_feed, find_promos, load_seen, save_seen
from verificador.rules import cheapest_compliant


def _describe_layovers(offer: Offer) -> str:
    parts = []
    for layover in offer.outbound.layovers + offer.inbound.layovers:
        if layover.minutes is None:
            parts.append(f"{layover.airport} ?")
        else:
            parts.append(f"{layover.airport} {layover.minutes // 60}h{layover.minutes % 60:02d}")
    return " | ".join(parts)


def _airlines(offer: Offer) -> str:
    names = dict.fromkeys(offer.outbound.airlines + offer.inbound.airlines)
    return "+".join(names)


def _check_promos(cfg: Config, notify_fn, feed_fn) -> None:
    entries: list[dict] = []
    for url in cfg.promos.feeds:
        try:
            entries += feed_fn(url)
        except Exception:
            continue  # um feed fora do ar nao pode derrubar a coleta de precos
    seen = load_seen(cfg.paths.seen_promos)
    promos = find_promos(entries, list(cfg.promos.keywords), cfg.promos.max_milheiro, seen)
    for p in promos:
        notify_fn(
            "Promoção de milhas",
            f"{p.program}: milheiro a R$ {p.milheiro_brl:.2f}. {p.title} {p.link}",
            cfg.paths.alerts_log,
        )
        seen.add(p.link)
    if promos:
        save_seen(cfg.paths.seen_promos, seen)


def run(cfg: Config, api_key: str, today: str, fetch=fetch_offers, notify_fn=notify, feed_fn=fetch_feed) -> int:
    log = cfg.paths.alerts_log
    code = 0
    try:
        offers = fetch(cfg, api_key)
    except CollectorError as exc:
        if not has_ok_record(cfg.paths.history, today):  # falha nao apaga o preco bom do dia
            upsert_record(cfg.paths.history, HistoryRecord(today, None, "", "", None, "error"))
        notify_fn("Verificador: falha na coleta", str(exc), log)
        code = 1
    else:
        best, discarded = cheapest_compliant(offers, cfg.rules.min_layover_minutes, cfg.rules.brazil_airports)
        if best is None:
            if not has_ok_record(cfg.paths.history, today):
                upsert_record(cfg.paths.history, HistoryRecord(today, None, "", "", None, "empty"))
            if not offers:
                reason = "A API não devolveu nenhuma oferta."
            else:
                reason = (
                    f"{len(offers)} ofertas, nenhuma passa nas suas regras; "
                    f"{discarded} descartadas por escala sem duração informada."
                )
            notify_fn("Verificador: nenhuma oferta válida hoje", reason, log)
            code = 1
        else:
            previous = last_price(cfg.paths.history, today)
            first_ok_today = not has_ok_record(cfg.paths.history, today)
            upsert_record(
                cfg.paths.history,
                HistoryRecord(today, best.total_price_brl, _airlines(best), _describe_layovers(best), best.fare, "ok"),
            )
            if first_ok_today:
                for message in price_alerts(previous, best.total_price_brl, cfg.alerts.drop_pct, cfg.alerts.target_brl):
                    notify_fn("Verificador: preço da passagem", message, log)
    _check_promos(cfg, notify_fn, feed_fn)
    return code


def main(notify_fn=notify) -> int:
    os.chdir(Path(__file__).resolve().parents[2])  # raiz do projeto, para os caminhos relativos do config
    cfg = load_config("config.toml")
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        notify_fn(
            "Verificador: chave ausente",
            "A variável de ambiente SERPAPI_KEY não está definida.",
            cfg.paths.alerts_log,
        )
        return 1
    return run(cfg, api_key, date.today().isoformat(), notify_fn=notify_fn)


if __name__ == "__main__":
    sys.exit(main())
