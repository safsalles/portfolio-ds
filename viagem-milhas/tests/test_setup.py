from verificador.config import Baggage, load_config
from verificador.setup import run_wizard

TODAY = "2026-11-23"

# ordem das perguntas: origem, destino, data ida, volta sai de, volta chega em, data volta,
# adultos, classe, malas de mao, malas despachadas, preco da mala (so se despachadas > 0),
# escala minima (h), aeroportos a evitar, moeda, queda %, valor-alvo
BASE = ["gru", "lis", "2027-03-10", "", "", "2027-03-24", "2", "", "1", "1", "500", "4", "", "BRL", "", "18000"]


def run(answers, path, today=TODAY):
    it = iter(answers)
    messages = []
    code = run_wizard(ask=lambda prompt: next(it), path=str(path), out=messages.append, today=today)
    return code, messages


def test_wizard_writes_a_config_that_loads(tmp_path):
    path = tmp_path / "config.toml"

    code, _ = run(BASE, path)

    assert code == 0
    cfg = load_config(str(path))
    assert cfg.trip.outbound == ("GRU", "LIS", "2027-03-10")
    assert cfg.trip.inbound == ("LIS", "GRU", "2027-03-24")  # volta = ida invertida por padrao
    assert cfg.trip.adults == 2
    assert cfg.trip.cabin == "economy"
    assert cfg.trip.currency == "BRL"
    assert cfg.rules.min_layover_minutes == 240
    assert cfg.rules.avoid_airports == frozenset()
    assert cfg.alerts.drop_pct == 5.0 and cfg.alerts.target_brl == 18000
    assert cfg.baggage == Baggage(carry_on=1, checked=1, checked_bag_fee_brl=500.0)


def test_wizard_open_jaw_return_from_another_city(tmp_path):
    path = tmp_path / "config.toml"
    answers = list(BASE)
    answers[3], answers[4] = "ber", "gig"  # volta sai de Berlim e chega no Rio

    run(answers, path)

    assert load_config(str(path)).trip.inbound == ("BER", "GIG", "2027-03-24")


def test_wizard_skips_fee_question_when_no_checked_bags(tmp_path):
    path = tmp_path / "config.toml"
    answers = ["gru", "lis", "2027-03-10", "", "", "2027-03-24", "1", "", "0", "0", "6", "", "", "", ""]
    # sem pergunta de preco da mala; escala 6h; aeroportos vazio; moeda vazia (BRL); queda vazia; alvo vazio

    code, _ = run(answers, path)

    cfg = load_config(str(path))
    assert code == 0
    assert cfg.baggage == Baggage(carry_on=0, checked=0, checked_bag_fee_brl=0.0)
    assert cfg.rules.min_layover_minutes == 360
    assert cfg.trip.currency == "BRL"


def test_wizard_asks_again_on_invalid_airport_code(tmp_path):
    path = tmp_path / "config.toml"

    code, messages = run(["XX1"] + BASE, path)

    assert code == 0
    assert load_config(str(path)).trip.outbound[0] == "GRU"
    assert any("3 letras" in m for m in messages)


def test_wizard_rejects_past_date_and_return_before_outbound(tmp_path):
    path = tmp_path / "config.toml"
    answers = list(BASE)
    answers.insert(2, "2020-01-01")  # data de ida no passado -> reprovada, pergunta de novo
    answers.insert(6, "2027-03-05")  # volta antes da ida -> reprovada, pergunta de novo

    code, messages = run(answers, path)

    assert code == 0
    cfg = load_config(str(path))
    assert cfg.trip.outbound[2] == "2027-03-10" and cfg.trip.inbound[2] == "2027-03-24"
    assert any("passado" in m for m in messages)
    assert any("depois da ida" in m for m in messages)


def test_wizard_parses_avoid_airports_list(tmp_path):
    path = tmp_path / "config.toml"
    answers = list(BASE)
    answers[12] = "gru, vcp"

    run(answers, path)

    assert load_config(str(path)).rules.avoid_airports == frozenset({"GRU", "VCP"})


def test_wizard_does_not_overwrite_without_confirmation(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("ORIGINAL", encoding="utf-8")

    code, _ = run(["n"], path)

    assert code == 1
    assert path.read_text(encoding="utf-8") == "ORIGINAL"


def test_wizard_overwrites_when_confirmed(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("ORIGINAL", encoding="utf-8")

    code, _ = run(["s"] + BASE, path)

    assert code == 0
    assert load_config(str(path)).trip.outbound[1] == "LIS"
