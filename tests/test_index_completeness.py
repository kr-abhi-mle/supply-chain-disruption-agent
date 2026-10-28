"""The metadata filter must return exactly what pandas counts. Needs the index."""
import pandas as pd
import pytest

from src import config


@pytest.fixture(scope="module")
def collection():
    from src.build_index import open_collection
    try:
        return open_collection()
    except SystemExit:
        pytest.skip("run python -m src.build_index")


@pytest.mark.parametrize("state", ["SP", "MG", "RS"])
def test_filter_count_equals_pandas_count(collection, state):
    df = pd.read_csv(config.PROCESSED_CSV)
    found = collection.get(where={"seller_state": state}, include=[])
    assert len(found["ids"]) == int((df["seller_state"] == state).sum())


def test_sp_scenario_returns_every_sp_item(collection):
    from src.agents import disruption_parser, retrieval_agent
    event = disruption_parser.run("Heavy rains are delaying all freight leaving Sao Paulo for 5 days", False).event
    items = retrieval_agent.run(event)
    assert len(items) == 7959
    assert len({item.order_id for item in items}) == 7037
    assert sum(item.focus_match for item in items) == config.FOCUS_TOP_K
