from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "planilha" / "dimensionamento_equipe.xlsx"
SHEETS = ["Comece aqui", "Calculadora", "Contratar ou demitir", "Escala do dia", "Chegadas", "Previsão", "Cálculos"]


def wb():
    return load_workbook(FILE)


def test_sheets_and_hidden_calculations():
    w = wb()
    assert w.sheetnames == SHEETS
    assert w["Cálculos"].sheet_state == "hidden"


def test_inputs_are_editable_and_have_project_premises():
    c = wb()["Calculadora"]
    assert [c[f"C{r}"].value for r in range(6, 10)] == [6, 20, 0.8, 0.3]
    assert all(c[f"C{r}"].protection.locked is False for r in range(5, 10))
    assert c.protection.sheet and not c.protection.password


def test_results_are_formulas_not_typed_numbers():
    w = wb()
    for ref in ("C13", "C14", "C15", "C16", "C17", "C18"):
        assert str(w["Calculadora"][ref].value).startswith("=")
    assert all(str(w["Escala do dia"][f"C{r}"].value).startswith("=") for r in range(5, 29))
    assert str(w["Previsão"]["H5"].value).startswith("=")


def test_honest_warnings_present():
    w = wb()
    text = " ".join(str(c.value) for s in ("Comece aqui", "Calculadora") for row in w[s].iter_rows() for c in row if c.value)
    assert "fictíci" in text and "exponencial" in text and "desist" in text


def test_context_notes_avoid_misreading():
    w = wb()
    prev = str(w["Previsão"]["B3"].value)
    assert "ano inteiro" in prev and "19,8%" in prev and "20,0%" in prev and "empate" in prev
    calc = " ".join(str(c.value) for row in w["Calculadora"].iter_rows() for c in row if c.value)
    assert "3,2 minutos" in calc


def test_readmes_link_to_spreadsheet():
    url = "https://github.com/safsalles/portfolio-ds/raw/main/dimensionamento-equipe/planilha/dimensionamento_equipe.xlsx"
    for name in ("README.md", "README.en.md"):
        assert url in (ROOT / name).read_text(encoding="utf-8")
