import pytest

from src.pipeline import build_spark


@pytest.fixture(scope="session")
def spark():
    s = build_spark("wfm-tests")
    yield s
    s.stop()
