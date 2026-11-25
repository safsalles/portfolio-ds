import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from atualizar_readme import BEGIN, END, render  # noqa: E402

RESULTS = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
FILES = {"pt": ROOT / "README.md", "en": ROOT / "README.en.md"}


def block(text: str) -> str:
    return text.split(BEGIN)[1].split(END)[0].strip()


def test_readme_numbers_match_results():
    for lang, path in FILES.items():
        assert block(path.read_text(encoding="utf-8")) == render(RESULTS, lang).strip()


def test_readme_declares_fictional_team():
    assert "fictíci" in FILES["pt"].read_text(encoding="utf-8").lower()
    assert "fictional" in FILES["en"].read_text(encoding="utf-8").lower()


def test_readme_documents_databricks_execution_and_its_limit():
    pt = FILES["pt"].read_text(encoding="utf-8")
    en = FILES["en"].read_text(encoding="utf-8")
    assert "executado no Databricks Free Edition" in pt and "só o pipeline" in pt
    assert "run on Databricks Free Edition" in en and "only the pipeline" in en
    assert "preparado, não executado" not in pt and "prepared, not executed" not in en
    for text in (pt, en):
        assert "docs/databricks_execucao.png" in text
    assert (ROOT / "docs" / "databricks_execucao.png").stat().st_size > 10_000


def test_databricks_numbers_match_local_run():
    db = json.loads((ROOT / "results" / "databricks_run.json").read_text(encoding="utf-8"))
    local = RESULTS["data"]
    assert db["rows_in"] == local["rows_in"]
    assert db["chamadas"] == local["total_calls"]
    assert db["horas"] == local["n_hours"]
    pt = FILES["pt"].read_text(encoding="utf-8")
    assert f"{db['chamadas']:,}".replace(",", ".") in pt and f"{db['horas']:,}".replace(",", ".") in pt

def test_render_reports_model_not_beating_baseline_honestly():
    f = RESULTS["forecast"]["reajuste_mensal"]
    txt = render(RESULTS, "pt")
    assert f"{f['wape_baseline'] * 100:.1f}".replace(".", ",") + "%" in txt


def test_render_has_analyzer_section():
    a = RESULTS["analisador"]["atendimento_technion"]
    for lang in ("pt", "en"):
        txt = render(RESULTS, lang)
        assert "AIC" in txt and "BIC" in txt
        assert a["melhor"] in txt  # a proposta aparece com o nome da distribuição
        assert all(row["name"] in txt for row in a["ranking"])  # ranking completo, não só o vencedor


def test_render_states_mixed_sources():
    assert "NYC 311" in render(RESULTS, "pt") and "Technion" in render(RESULTS, "pt")
    assert "mixed" in render(RESULTS, "en").lower() and "Technion" in render(RESULTS, "en")


def test_render_reports_bank_validation_as_measured():
    v = RESULTS["validacao_banco"]
    txt = render(RESULTS, "pt")
    assert f"{v['real_mean_wait_s']:.1f}".replace(".", ",") in txt
    assert f"{v['sim_mean_wait_s']:.1f}".replace(".", ",") in txt
    assert "abandono" in txt.lower()


def test_render_has_agent_sweep_and_calls_it_calibration_not_validation():
    v = RESULTS["validacao_banco"]
    txt = render(RESULTS, "pt")
    assert all(f"| {r['agentes']} |" in txt for r in v["varredura"])
    assert "calibra" in txt.lower() and str(v["agentes_mais_proximo_espera"]) in txt
    assert "calibrat" in render(RESULTS, "en").lower()


def test_flow_diagram_is_single_source():
    from atualizar_readme import FLOW_BEGIN, FLOW_END, flow_text

    for lang, path in FILES.items():
        text = path.read_text(encoding="utf-8")
        assert FLOW_BEGIN in text and FLOW_END in text
        injected = text.split(FLOW_BEGIN)[1].split(FLOW_END)[0]
        assert flow_text(lang).strip() in injected
        assert "NYC 311" in flow_text(lang) and "Technion" in flow_text(lang)


def test_validation_text_does_not_claim_an_unproven_cause():
    pt, en = render(RESULTS, "pt"), render(RESULTS, "en")
    assert "não consta nos dados" not in pt and "is not in the data" not in en
    assert "fila vazia" in pt and "empty queue" in en
    assert "não está demonstrado" in pt and "not been established" in en
    for path in FILES.values():
        text = path.read_text(encoding="utf-8")
        assert "número de atendentes ativos hora a hora não está" not in text
        assert "number of active agents hour by hour is not in the data" not in text


def test_render_publishes_the_whole_investigation_honestly():
    inv = RESULTS["investigacao"]
    pt, en = render(RESULTS, "pt"), render(RESULTS, "en")
    assert len(inv["cenarios"]) >= 13
    for row in inv["cenarios"]:
        assert row["rotulo_pt"] in pt and row["rotulo_en"] in en
    low = pt.lower()
    assert "refutada" in low and "circular" in low and "não está demonstrado" in low
    assert "refuted" in en.lower() and "circular" in en.lower()
    text = json.dumps(inv)
    assert "server" not in text  # só agregados, sem nomes de atendentes
