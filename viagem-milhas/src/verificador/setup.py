"""Assistente de configuracao: pergunta a viagem e gera o config.toml.

Uso:  python -m verificador.setup
"""
import json
import os
import re
import sys
from datetime import date

CABINS = ("economy", "premium_economy", "business", "first")
DEFAULT_FEEDS = ("https://passageirodeprimeira.com/feed/", "https://pontospravoar.com/feed/")
DEFAULT_KEYWORDS = ("flying blue", "smiles", "livelo", "tap", "milheiro", "bônus")
DEFAULT_MILHEIRO = {"flying blue": 35, "tap": 35, "livelo": 35, "smiles": 12}
_IATA = re.compile(r"^[A-Za-z]{3}$")


def _loop(ask, out, prompt, parse):
    while True:
        try:
            return parse(ask(prompt).strip())
        except ValueError as exc:
            out(f"  -> {exc}")


def _iata(default=None):
    def parse(raw):
        if raw == "" and default:
            return default
        if not _IATA.match(raw):
            raise ValueError("Use o código do aeroporto ou da cidade com 3 letras (ex.: GRU).")
        return raw.upper()

    return parse


def _iso_date(today: date, not_before: date | None = None):
    def parse(raw):
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            raise ValueError("Use o formato AAAA-MM-DD (ex.: 2027-03-10).") from None
        if d < today:
            raise ValueError("Essa data está no passado.")
        if not_before and d < not_before:
            raise ValueError("A volta precisa ser no mesmo dia ou depois da ida.")
        return d

    return parse


def _number(lo, hi, default, integer=True):
    def parse(raw):
        if raw == "":
            return default
        try:
            value = int(raw) if integer else float(raw.replace(",", "."))
        except ValueError:
            raise ValueError("Digite um número.") from None
        if not lo <= value <= hi:
            raise ValueError(f"Digite um valor entre {lo} e {hi}.")
        return value

    return parse


def _cabin(raw):
    if raw == "":
        return "economy"
    if raw not in CABINS:
        raise ValueError("Escolha uma de: " + ", ".join(CABINS) + ".")
    return raw


def _airports(raw):
    codes = [c for c in re.split(r"[,\s]+", raw) if c]
    if not all(_IATA.match(c) for c in codes):
        raise ValueError("Informe códigos de 3 letras separados por vírgula (ou deixe em branco).")
    return [c.upper() for c in codes]


def _currency(raw):
    if raw == "":
        return "BRL"
    if not _IATA.match(raw):
        raise ValueError("Use o código da moeda com 3 letras (ex.: BRL, USD, EUR).")
    return raw.upper()


def _toml_list(items) -> str:
    return "[" + ", ".join(json.dumps(i, ensure_ascii=False) for i in items) + "]"


def build_config_toml(v: dict) -> str:
    milheiro = "\n".join(f'"{k}" = {val}' for k, val in DEFAULT_MILHEIRO.items())
    return f"""# Gerado por: python -m verificador.setup  (pode editar a mao)
[trip]
outbound = {_toml_list(v["outbound"])}
inbound = {_toml_list(v["inbound"])}
adults = {v["adults"]}
cabin = {json.dumps(v["cabin"])}
currency = {json.dumps(v["currency"])}

# Escala minima em minutos; aeroportos onde voce NAO aceita escala (opcional).
[rules]
min_layover_minutes = {v["min_layover_minutes"]}
avoid_airports = {_toml_list(v["avoid_airports"])}

# Avisa se o preco cair drop_pct % ou mais, ou ficar abaixo de target_brl (0 = desligado).
[alerts]
drop_pct = {v["drop_pct"]:g}
target_brl = {v["target_brl"]:g}

# Vigia de promocoes de milhas: avisa se o milheiro citado ficar abaixo do limite (R$).
[promos]
feeds = {_toml_list(DEFAULT_FEEDS)}
keywords = {_toml_list(DEFAULT_KEYWORDS)}

[promos.max_milheiro]
{milheiro}

[paths]
history = "data/history.csv"
seen_promos = "data/seen_promos.json"
alerts_log = "data/alerts.log"

# carry_on: malas de mao POR PESSOA; checked: malas despachadas por trecho; checked_bag_fee_brl: preco de UMA mala por trecho.
# send_to_api: enviar a mala de mao ao Google Voos. ATENCAO: filtra a busca e pode esconder ofertas validas; deixe false.
[baggage]
carry_on = {v["carry_on"]}
checked = {v["checked"]}
checked_bag_fee_brl = {v["checked_bag_fee_brl"]:g}
send_to_api = false
"""


def run_wizard(ask=input, path: str = "config.toml", out=print, today: str | None = None) -> int:
    today_date = date.fromisoformat(today) if today else date.today()
    if os.path.exists(path):
        answer = ask(f"Já existe um {path}. Sobrescrever? [s/N] ").strip().lower()
        if answer not in ("s", "sim", "y", "yes"):
            out("Nada foi alterado.")
            return 1

    out("Vamos configurar a sua viagem (Enter aceita o valor entre colchetes).")
    origin = _loop(ask, out, "Ida: aeroporto/cidade de origem (ex.: GRU): ", _iata())
    dest = _loop(ask, out, "Ida: destino (ex.: LIS): ", _iata())
    out_date = _loop(ask, out, "Data da ida (AAAA-MM-DD): ", _iso_date(today_date))
    back_from = _loop(ask, out, f"Volta sai de [{dest}]: ", _iata(dest))
    back_to = _loop(ask, out, f"Volta chega em [{origin}]: ", _iata(origin))
    back_date = _loop(ask, out, "Data da volta (AAAA-MM-DD): ", _iso_date(today_date, not_before=out_date))
    adults = _loop(ask, out, "Passageiros adultos [1]: ", _number(1, 9, 1))
    cabin = _loop(ask, out, "Classe (economy, premium_economy, business, first) [economy]: ", _cabin)
    carry_on = _loop(ask, out, "Malas de mão por pessoa [1]: ", _number(0, 5, 1))
    checked = _loop(ask, out, "Malas despachadas por trecho [0]: ", _number(0, 5, 0))
    fee = 0.0
    if checked > 0:
        fee = _loop(ask, out, "Preço estimado de UMA mala despachada, por trecho, em R$ [0]: ", _number(0, 100000, 0.0, integer=False))
    hours = _loop(ask, out, "Escala mínima em horas (ex.: 4 se precisa passar pela imigração) [0]: ", _number(0, 48, 0, integer=False))
    avoid = _loop(ask, out, "Aeroportos onde NÃO aceita escala, separados por vírgula (opcional): ", _airports)
    currency = _loop(ask, out, "Moeda [BRL]: ", _currency)
    drop = _loop(ask, out, "Avisar se o preço cair quantos % [5]: ", _number(0.1, 100, 5.0, integer=False))
    target = _loop(ask, out, "Avisar se ficar abaixo de quanto (0 = desligado) [0]: ", _number(0, 10_000_000, 0.0, integer=False))

    values = {
        "outbound": [origin, dest, out_date.isoformat()],
        "inbound": [back_from, back_to, back_date.isoformat()],
        "adults": adults,
        "cabin": cabin,
        "currency": currency,
        "min_layover_minutes": int(round(hours * 60)),
        "avoid_airports": avoid,
        "drop_pct": drop,
        "target_brl": target,
        "carry_on": carry_on,
        "checked": checked,
        "checked_bag_fee_brl": fee,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_config_toml(values))
    out(f"Configuração salva em {path}.")
    out("Próximo passo: defina a variável SERPAPI_KEY e rode  python -m verificador.run_daily")
    return 0


def main() -> int:
    return run_wizard()


if __name__ == "__main__":
    sys.exit(main())
