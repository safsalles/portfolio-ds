"""Assistente de configuracao: pergunta a viagem e gera o config.toml.

Uso:  python -m verificador.setup
"""
import json
import os
import re
import sys
from datetime import date

from verificador.config import load_config
from verificador.places import looks_like_codes, search_places

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


_NOT_FOUND = "Não achei esse lugar. Digite o nome de uma cidade (ex.: Lisboa) ou o código de 3 letras do aeroporto (ex.: LIS)."


def _codes(raw: str) -> str:
    return ",".join(c.strip().upper() for c in raw.split(","))


def _iata(default=None):
    """Um ou mais codigos de aeroporto (ex.: GRU ou LHR,LGW). Nomes de cidade sao resolvidos antes, em _ask_place."""

    def parse(raw):
        if raw == "" and default:
            return default
        if not looks_like_codes(raw):
            raise ValueError(_NOT_FOUND)
        return _codes(raw)

    return parse


def _ask_place(ask, out, prompt, default=None):
    """Pergunta um lugar: aceita o codigo (GRU) ou o nome (Lisboa) e mostra opcoes quando houver mais de uma."""
    while True:
        raw = ask(prompt).strip()
        if raw == "" and default:
            return default
        if looks_like_codes(raw):
            return _codes(raw)
        results = search_places(raw)
        if not results:
            out("  -> " + _NOT_FOUND)
            continue
        if len(results) == 1:
            out(f"  -> {results[0].label}")
            return results[0].codes
        out("  Encontrei:")
        for i, place in enumerate(results, 1):
            out(f"   {i}) {place.label}")
        choice = ask("  Digite o número da opção (ou Enter para digitar de novo): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            return results[int(choice) - 1].codes


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


def _max_hours(min_hours):
    """Escala maxima em horas (0 ou em branco = sem limite); precisa ser maior que a minima."""

    def parse(raw):
        value = _number(0, 96, 0, integer=False)(raw)
        if value > 0 and min_hours is not None and value <= min_hours:
            raise ValueError("A escala máxima precisa ser maior que a mínima.")
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


DEFAULT_PATHS = {
    "history": "data/history.csv",
    "seen_promos": "data/seen_promos.json",
    "alerts_log": "data/alerts.log",
    "snapshots": "data/snapshots",
}


def merge_existing(values: dict, cfg) -> dict:
    """Junta o que veio do formulario/assistente com o que ja existia e NAO e' perguntado
    (feeds e limites de promocao, caminhos dos dados, envio da mala de mao a API), para nao perder nada ao salvar."""
    return {
        **values,
        "feeds": list(cfg.promos.feeds),
        "keywords": list(cfg.promos.keywords),
        "max_milheiro": dict(cfg.promos.max_milheiro),
        "paths": {
            "history": cfg.paths.history,
            "seen_promos": cfg.paths.seen_promos,
            "alerts_log": cfg.paths.alerts_log,
            "snapshots": cfg.paths.snapshots,
        },
        "send_to_api": cfg.baggage.send_to_api,
    }


def _toml_list(items) -> str:
    return "[" + ", ".join(json.dumps(i, ensure_ascii=False) for i in items) + "]"


def build_config_toml(v: dict) -> str:
    milheiro = "\n".join(f'"{k}" = {val:g}' for k, val in v.get("max_milheiro", DEFAULT_MILHEIRO).items())
    paths = {**DEFAULT_PATHS, **v.get("paths", {})}
    return f"""# Gerado por: python -m verificador.setup  (pode editar a mao)
[trip]
outbound = {_toml_list(v["outbound"])}
inbound = {_toml_list(v["inbound"])}
adults = {v["adults"]}
cabin = {json.dumps(v["cabin"])}
currency = {json.dumps(v["currency"])}

# Escala minima e maxima em minutos (maxima 0 = sem limite); aeroportos onde voce NAO aceita escala (opcional).
[rules]
min_layover_minutes = {v["min_layover_minutes"]}
max_layover_minutes = {v["max_layover_minutes"]}
avoid_airports = {_toml_list(v["avoid_airports"])}

# Avisa se o preco cair drop_pct % ou mais, ou ficar abaixo de target_brl (0 = desligado).
[alerts]
drop_pct = {v["drop_pct"]:g}
target_brl = {v["target_brl"]:g}

# Vigia de promocoes de milhas: avisa se o milheiro citado ficar abaixo do limite (R$).
[promos]
feeds = {_toml_list(v.get("feeds", DEFAULT_FEEDS))}
keywords = {_toml_list(v.get("keywords", DEFAULT_KEYWORDS))}

[promos.max_milheiro]
{milheiro}

[paths]
history = {json.dumps(paths["history"])}
seen_promos = {json.dumps(paths["seen_promos"])}
alerts_log = {json.dumps(paths["alerts_log"])}
snapshots = {json.dumps(paths["snapshots"])}

# carry_on: malas de mao POR PESSOA; checked: malas despachadas por trecho; checked_bag_fee_brl: preco de UMA mala por trecho.
# send_to_api: enviar a mala de mao ao Google Voos. ATENCAO: filtra a busca e pode esconder ofertas validas; deixe false.
[baggage]
carry_on = {v["carry_on"]}
checked = {v["checked"]}
checked_bag_fee_brl = {v["checked_bag_fee_brl"]:g}
send_to_api = {"true" if v.get("send_to_api") else "false"}
"""


def parse_form(raw: dict, today: date) -> tuple[dict | None, dict]:
    """Valida o formulario da interface (texto de cada campo) com as MESMAS regras do assistente.

    Devolve (valores, {}) se tudo estiver certo, ou (None, {campo: mensagem}) com todos os erros de uma vez.
    """
    errors: dict[str, str] = {}

    def field(key, parser):
        try:
            return parser(str(raw.get(key, "")).strip())
        except ValueError as exc:
            errors[key] = str(exc)
            return None

    origin = field("origin", _iata())
    dest = field("dest", _iata())
    out_date = field("out_date", _iso_date(today))
    # Em branco = padrao (volta invertida). Se o padrao nao existe porque a ida deu erro, nao acrescenta outro erro.
    back_from = field("back_from", _iata(dest)) if dest or str(raw.get("back_from", "")).strip() else None
    back_to = field("back_to", _iata(origin)) if origin or str(raw.get("back_to", "")).strip() else None
    back_date = field("back_date", _iso_date(today, not_before=out_date))
    adults = field("adults", _number(1, 9, 1))
    cabin = field("cabin", _cabin)
    carry_on = field("carry_on", _number(0, 5, 1))
    checked = field("checked", _number(0, 5, 0))
    fee = 0.0
    if checked:  # o preco da mala so importa se houver mala despachada
        fee = field("fee", _number(0, 100000, 0.0, integer=False))
    hours = field("hours", _number(0, 48, 0, integer=False))
    max_hours = field("max_hours", _max_hours(hours))
    avoid = field("avoid", _airports)
    currency = field("currency", _currency)
    drop = field("drop", _number(0.1, 100, 5.0, integer=False))
    target = field("target", _number(0, 10_000_000, 0.0, integer=False))
    if errors:
        return None, errors
    return {
        "outbound": [origin, dest, out_date.isoformat()],
        "inbound": [back_from, back_to, back_date.isoformat()],
        "adults": adults,
        "cabin": cabin,
        "currency": currency,
        "min_layover_minutes": int(round(hours * 60)),
        "max_layover_minutes": int(round(max_hours * 60)),
        "avoid_airports": avoid,
        "drop_pct": drop,
        "target_brl": target,
        "carry_on": carry_on,
        "checked": checked,
        "checked_bag_fee_brl": fee,
    }, {}


def form_defaults(cfg) -> dict:
    """Valores iniciais do formulario: os da configuracao atual, ou padroes sensatos se nao houver."""
    if cfg is None:
        return {
            "origin": "", "dest": "", "out_date": "", "back_from": "", "back_to": "", "back_date": "",
            "adults": "1", "cabin": "economy", "carry_on": "1", "checked": "0", "fee": "0",
            "hours": "0", "max_hours": "0", "avoid": "", "currency": "BRL", "drop": "5", "target": "0",
        }
    return {
        "origin": cfg.trip.outbound[0], "dest": cfg.trip.outbound[1], "out_date": cfg.trip.outbound[2],
        "back_from": cfg.trip.inbound[0], "back_to": cfg.trip.inbound[1], "back_date": cfg.trip.inbound[2],
        "adults": str(cfg.trip.adults), "cabin": cfg.trip.cabin,
        "carry_on": str(cfg.baggage.carry_on), "checked": str(cfg.baggage.checked),
        "fee": f"{cfg.baggage.checked_bag_fee_brl:g}",
        "hours": f"{cfg.rules.min_layover_minutes / 60:g}",
        "max_hours": f"{(cfg.rules.max_layover_minutes or 0) / 60:g}",
        "avoid": ", ".join(sorted(cfg.rules.avoid_airports)),
        "currency": cfg.trip.currency, "drop": f"{cfg.alerts.drop_pct:g}", "target": f"{cfg.alerts.target_brl:g}",
    }


def run_wizard(ask=input, path: str = "config.toml", out=print, today: str | None = None) -> int:
    today_date = date.fromisoformat(today) if today else date.today()
    if os.path.exists(path):
        answer = ask(f"Já existe um {path}. Sobrescrever? [s/N] ").strip().lower()
        if answer not in ("s", "sim", "y", "yes"):
            out("Nada foi alterado.")
            return 1

    out("Vamos configurar a sua viagem (Enter aceita o valor entre colchetes).")
    origin = _ask_place(ask, out, "Ida: de onde você sai (cidade ou código, ex.: Rio de Janeiro ou GIG): ")
    dest = _ask_place(ask, out, "Ida: para onde você vai (cidade ou código, ex.: Lisboa ou LIS): ")
    out_date = _loop(ask, out, "Data da ida (AAAA-MM-DD): ", _iso_date(today_date))
    back_from = _ask_place(ask, out, f"Volta sai de [{dest}]: ", dest)
    back_to = _ask_place(ask, out, f"Volta chega em [{origin}]: ", origin)
    back_date = _loop(ask, out, "Data da volta (AAAA-MM-DD): ", _iso_date(today_date, not_before=out_date))
    adults = _loop(ask, out, "Passageiros adultos [1]: ", _number(1, 9, 1))
    cabin = _loop(ask, out, "Classe (economy, premium_economy, business, first) [economy]: ", _cabin)
    carry_on = _loop(ask, out, "Malas de mão por pessoa [1]: ", _number(0, 5, 1))
    checked = _loop(ask, out, "Malas despachadas por trecho [0]: ", _number(0, 5, 0))
    fee = 0.0
    if checked > 0:
        fee = _loop(ask, out, "Preço estimado de UMA mala despachada, por trecho, em R$ [0]: ", _number(0, 100000, 0.0, integer=False))
    hours = _loop(ask, out, "Escala mínima em horas (ex.: 4 se precisa passar pela imigração) [0]: ", _number(0, 48, 0, integer=False))
    max_hours = _loop(ask, out, "Escala máxima em horas (0 = sem limite) [0]: ", _max_hours(hours))
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
        "max_layover_minutes": int(round(max_hours * 60)),
        "avoid_airports": avoid,
        "drop_pct": drop,
        "target_brl": target,
        "carry_on": carry_on,
        "checked": checked,
        "checked_bag_fee_brl": fee,
    }
    if os.path.exists(path):  # sobrescrevendo: mantem o que o assistente nao pergunta
        try:
            values = merge_existing(values, load_config(path))
        except Exception:
            pass  # arquivo antigo ilegivel: grava so o novo
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
