import pytest

from src.models import AffectedItem


@pytest.fixture
def make_item():
    """An affected item with a 2-day buffer (promised 22 Aug, arrives 20 Aug). Override any field."""
    def _make(**overrides) -> AffectedItem:
        fields = dict(
            id="o1-1", order_id="o1", order_item_id=1, product_id="p1", seller_id="s1",
            customer_id="c1", order_status="delivered", purchase_date="2018-08-01",
            promised_date="2018-08-22", baseline_eta="2018-08-20", seller_city="sao paulo",
            seller_state="SP", customer_city="recife", customer_state="PE",
            category="housewares", category_pt="utilidades_domesticas", weight_kg=1.0,
            volume_l=5.0, is_bulky=False, is_time_sensitive=False, price=100.0, freight_value=20.0,
        )
        fields.update(overrides)
        return AffectedItem(**fields)
    return _make
