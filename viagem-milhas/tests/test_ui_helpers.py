from datetime import datetime

from verificador.snapshots import SnapshotMeta
from verificador.ui_helpers import delta_text, format_brl, snapshot_label


def test_format_brl_uses_brazilian_separators():
    assert format_brl(19152.0) == "R$ 19.152,00"
    assert format_brl(1234567.5) == "R$ 1.234.567,50"
    assert format_brl(None) == "—"


def test_snapshot_label_shows_when_source_best_and_count():
    meta = SnapshotMeta("x.json", datetime(2026, 11, 24, 8, 0, 0), "agendada", 21440.0, 10)

    assert snapshot_label(meta) == "24/11/2026 08:00 · agendada · melhor R$ 21.440,00 · 10 ofertas"


def test_snapshot_label_without_a_compliant_offer():
    meta = SnapshotMeta("x.json", datetime(2026, 11, 24, 18, 30, 0), "manual", None, 1)

    assert snapshot_label(meta) == "24/11/2026 18:30 · manual · nenhuma passa nas regras · 1 oferta"


def test_delta_text_says_cheaper_or_pricier():
    assert delta_text((-252.0, -1.316)) == "R$ 252,00 mais barato (−1,3%)"
    assert delta_text((300.0, 1.5)) == "R$ 300,00 mais caro (+1,5%)"
    assert delta_text((0.0, 0.0)) == "mesmo preço"
    assert delta_text(None) == "sem como comparar"
