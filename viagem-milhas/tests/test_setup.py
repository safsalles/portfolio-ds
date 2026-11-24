from verificador.config import Baggage, load_config
from verificador.setup import run_wizard

TODAY = "2026-11-23"

# ordem das perguntas: origem, destino, data ida, volta sai de, volta chega em, data volta,
# adultos, classe, malas de mao, malas despachadas, preco da mala (so se despachadas > 0),
# escala minima (h), escala maxima (h; 0 = sem limite), aeroportos a evitar, moeda, queda %, valor-alvo
BASE = ["gru", "lis", "2027-03-10", "", "", "2027-03-24", "2", "", "1", "1", "500", "4", "", "", "BRL", "", "18000"]


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
    answers = ["gru", "lis", "2027-03-10", "", "", "2027-03-24", "1", "", "0", "0", "6", "", "", "", "", ""]
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
    answers[13] = "gru, vcp"

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


def test_wizard_saves_the_maximum_layover(tmp_path):
    path = tmp_path / "config.toml"
    answers = list(BASE)
    answers[12] = "10"  # escala maxima: 10 horas

    run(answers, path)

    assert load_config(str(path)).rules.max_layover_minutes == 600


def test_wizard_no_maximum_by_default(tmp_path):
    path = tmp_path / "config.toml"

    run(BASE, path)

    assert load_config(str(path)).rules.max_layover_minutes is None


def test_wizard_rejects_a_maximum_below_the_minimum(tmp_path):
    path = tmp_path / "config.toml"
    answers = list(BASE)
    answers[12] = "3"  # minimo e' 4h -> reprovado
    answers.insert(13, "8")  # pergunta de novo

    code, messages = run(answers, path)

    assert code == 0
    assert load_config(str(path)).rules.max_layover_minutes == 480
    assert any("maior" in m for m in messages)


def test_wizard_accepts_city_names_and_lets_you_pick_when_ambiguous(tmp_path):
    path = tmp_path / "config.toml"
    # origem "rio de janeiro" -> um unico resultado, escolhido sozinho; destino "lisboa" -> 2 opcoes -> escolhe a 1a
    answers = ["rio de janeiro", "lisboa", "1"] + BASE[2:]

    code, messages = run(answers, path)

    assert code == 0
    cfg = load_config(str(path))
    assert cfg.trip.outbound[:2] == ("GIG,SDU", "LIS")
    assert cfg.trip.inbound[:2] == ("LIS", "GIG,SDU")
    assert any("Encontrei" in m for m in messages)


def test_wizard_unknown_place_asks_again(tmp_path):
    path = tmp_path / "config.toml"

    code, messages = run(["atlantida"] + BASE, path)

    assert code == 0
    assert load_config(str(path)).trip.outbound[0] == "GRU"
    assert any("Não achei esse lugar" in m for m in messages)


def test_wizard_enter_at_the_option_list_retypes_the_place(tmp_path):
    path = tmp_path / "config.toml"
    answers = ["lisboa", "", "gru"] + BASE[1:]  # 1o lugar: lista -> Enter -> digita de novo

    code, _ = run(answers, path)

    assert code == 0
    assert load_config(str(path)).trip.outbound[0] == "GRU"


def test_wizard_overwrite_keeps_paths_and_promos_of_the_old_config(tmp_path):
    old = open("tests/fixtures/config_test.toml", encoding="utf-8").read()
    path = tmp_path / "config.toml"
    path.write_text(old.replace('history = "data/history.csv"', 'history = "meu/hist.csv"').replace('"smiles" = 12', '"smiles" = 9'), encoding="utf-8")

    code, _ = run(["s"] + BASE, path)

    cfg = load_config(str(path))
    assert code == 0
    assert cfg.trip.outbound[1] == "LIS"  # a viagem nova
    assert cfg.paths.history == "meu/hist.csv" and cfg.promos.max_milheiro["smiles"] == 9.0  # o resto foi mantido
