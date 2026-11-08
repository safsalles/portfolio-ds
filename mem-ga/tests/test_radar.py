import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

from mem.radar import COLORS, MUTED, interactive, plot_radar  # noqa: E402

LABELS = ["a", "b", "c", "d"]


def panel(title):
    return (title, [
        ("Média", np.full(4, 0.5), MUTED, "dash"),
        ("Conjunto", np.array([0.2, 0.9, 0.4, 0.7]), COLORS[0], "fill"),
        ("Outro", np.array([0.8, 0.1, 0.6, 0.3]), COLORS[1], "line"),
    ])


@pytest.mark.parametrize("n_panels", [1, 2])
def test_salva_um_png_nao_vazio(tmp_path, n_panels):
    path = tmp_path / "radar.png"
    plot_radar(LABELS, [panel(f"P{i}") for i in range(n_panels)], path, note="nota de rodapé")
    assert path.stat().st_size > 10_000


def test_sem_show_nao_abre_janela(tmp_path, monkeypatch):
    monkeypatch.setattr(plt, "show", lambda: pytest.fail("não deveria abrir a janela"))
    plot_radar(LABELS, [panel("P")], tmp_path / "radar.png")


def test_fecha_a_figura_depois_de_salvar(tmp_path):
    before = len(plt.get_fignums())
    plot_radar(LABELS, [panel("P")], tmp_path / "radar.png")
    assert len(plt.get_fignums()) == before


def test_interactive_e_falso_sem_terminal():
    # O pytest captura a saída, então não há terminal do outro lado.
    assert interactive() is False
