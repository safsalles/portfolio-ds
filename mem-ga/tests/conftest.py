import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMALL_DATA = ROOT / "exemplos" / "recrutamento-pequeno" / "data"


def load_example(folder, name, file="exemplo.py"):
    """Carrega um arquivo de uma pasta de exemplos com um nome próprio.

    Os dois exemplos se chamam exemplo.py, então importar pelo nome faria um esconder o outro.
    """
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "exemplos" / folder / file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def pequeno():
    return load_example("recrutamento-pequeno", "exemplo_pequeno")


@pytest.fixture(scope="session")
def grande():
    return load_example("recrutamento-grande", "exemplo_grande")


@pytest.fixture(scope="session")
def gerador():
    return load_example("recrutamento-grande", "gerar_dados_grande", "gerar_dados.py")
