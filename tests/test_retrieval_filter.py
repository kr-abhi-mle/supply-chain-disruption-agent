"""The Chroma filter built from an event. No index needed."""
from src.agents.retrieval_agent import build_where
from src.models import DisruptionEvent


def event(**fields):
    base = dict(disruption_type="weather", states=["SP"], cities=[], direction="outbound",
                delay_days=5, product_focus="furniture", interpretation="")
    base.update(fields)
    return DisruptionEvent(**base)


def test_outbound_filters_on_the_seller_state():
    assert build_where(event()) == {"seller_state": {"$in": ["SP"]}}


def test_inbound_filters_on_the_customer_state():
    assert build_where(event(direction="inbound", states=["RS"])) == {"customer_state": {"$in": ["RS"]}}


def test_both_directions_use_or():
    assert build_where(event(direction="both", states=["RJ"])) == {"$or": [
        {"seller_state": {"$in": ["RJ"]}}, {"customer_state": {"$in": ["RJ"]}}]}


def test_cities_are_used_instead_of_states():
    where = build_where(event(states=["PR"], cities=["curitiba"]))
    assert where == {"seller_city": {"$in": ["curitiba"]}}


def test_several_states_go_in_one_in_clause():
    assert build_where(event(states=["MG", "ES"])) == {"seller_state": {"$in": ["MG", "ES"]}}
