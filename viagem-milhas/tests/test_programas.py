from verificador.programas import ProgramInput, evaluate, load_inputs, save_inputs


def test_cost_in_miles_uses_the_transfer_bonus():
    r = evaluate(ProgramInput("livelo", 30.0, 100.0, 100000, 400.0), cash_brl=5000.0)

    assert r.effective_milheiro == 15.0          # R$ 30 com 100% de bonus = R$ 15 por milheiro
    assert r.miles_cost_brl == 1900.0            # 100 milheiros x 15 + 400 de taxas
    assert r.saving_brl == 3100.0 and r.miles_win


def test_cash_wins_when_miles_cost_more():
    r = evaluate(ProgramInput("smiles", 30.0, 0.0, 100000, 0.0), cash_brl=2000.0)

    assert not r.miles_win and r.saving_brl == -1000.0


def test_missing_data_gives_no_verdict():
    r = evaluate(ProgramInput("tap", 0.0, 0.0, 0, 0.0), cash_brl=2000.0)

    assert r.miles_cost_brl is None and r.saving_brl is None and not r.miles_win


def test_inputs_roundtrip(tmp_path):
    path = str(tmp_path / "p.csv")
    save_inputs(path, [ProgramInput("smiles", 14.0, 10.0, 90000, 250.0)])

    assert load_inputs(path, ["smiles", "tap"]) == [
        ProgramInput("smiles", 14.0, 10.0, 90000, 250.0), ProgramInput("tap", 0.0, 0.0, 0, 0.0)]


def test_max_miles_that_still_beat_cash():
    from verificador.programas import max_miles_worth
    assert max_miles_worth(20000.0, 400.0, 20.0) == 980000   # (20000-400)/20 milheiros
    assert max_miles_worth(0.0, 0.0, 20.0) is None and max_miles_worth(1000.0, 0.0, 0.0) is None


def test_pick_milheiro_prefers_a_found_promo_over_the_configured_limit():
    from verificador.programas import pick_milheiro
    assert pick_milheiro("smiles", {"smiles": 14.0}, {"smiles": 16.0}) == (14.0, "promoção achada")
    assert pick_milheiro("tap", {"smiles": 14.0}, {"tap": 30.0}) == (30.0, "seu limite")


def test_balance_is_not_charged_only_the_missing_miles_are_bought():
    r = evaluate(ProgramInput("smiles", 20.0, 0.0, 100000, 300.0, balance=40000), cash_brl=5000.0)

    assert r.miles_cost_brl == 1500.0  # 60 milheiros x 20 + 300 de taxas


def test_balance_and_price_date_roundtrip(tmp_path):
    path = str(tmp_path / "p.csv")
    save_inputs(path, [ProgramInput("smiles", 14.0, 0.0, 0, 0.0, balance=25000, price_date="2026-11-24")])

    got = load_inputs(path, ["smiles"])[0]
    assert got.balance == 25000 and got.price_date == "2026-11-24"
