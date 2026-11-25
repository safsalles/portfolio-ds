"""O app tem que abrir e rodar sem data/raw, data/processed e sem os Parquet de results/."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = (
    "from streamlit.testing.v1 import AppTest\n"
    "at = AppTest.from_file('app/app.py', default_timeout=180).run()\n"
    "assert not at.exception, at.exception\n"
    "text = ' '.join(m.value for m in at.markdown)\n"
    "assert 'Fontes misturadas' in text\n"
    "print('APP_OK')\n"
)


def minimal_copy(dst: Path, with_results: bool = True) -> Path:
    for folder in ("app", "src", "config"):
        shutil.copytree(ROOT / folder, dst / folder, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data" / "exemplos", dst / "data" / "exemplos")
    (dst / "results").mkdir()
    if with_results:
        shutil.copy(ROOT / "results" / "results.json", dst / "results" / "results.json")
    return dst


def run_app(cwd: Path):
    return subprocess.run([sys.executable, "-I", "-c", SCRIPT], cwd=cwd, capture_output=True, text=True, timeout=300)


def test_app_independent_of_raw_data(tmp_path):
    root = minimal_copy(tmp_path / "proj")
    assert not (root / "data" / "raw").exists() and not (root / "data" / "processed").exists()
    assert not list(root.rglob("*.parquet"))
    r = run_app(root)
    assert "APP_OK" in r.stdout, r.stderr[-2000:]


def test_negative_control_detects_missing_results(tmp_path):
    root = minimal_copy(tmp_path / "proj", with_results=False)
    r = run_app(root)
    assert "APP_OK" not in r.stdout  # sem results.json o app não pode abrir: o teste acima é capaz de falhar
