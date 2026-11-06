import pytest

from mem_ga import build_scorer, load_dataset


@pytest.fixture(scope="session")
def dataset():
    return load_dataset()


@pytest.fixture(scope="session")
def scorer(dataset):
    return build_scorer(dataset)


@pytest.fixture(scope="session")
def find(dataset):
    def _find(names):
        return [dataset.players.index(name) for name in names]

    return _find
