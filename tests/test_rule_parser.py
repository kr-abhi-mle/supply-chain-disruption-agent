"""The rule-based parser and the shared validation, on the phase 3 table. No key needed."""
import pytest

from src.agents import disruption_parser, rule_parser


def parse(query):
    return disruption_parser.run(query, use_llm=False)


@pytest.mark.parametrize("query, states, cities, direction, days", [
    ("Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days", ["SP"], [], "outbound", 5),
    ("Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days", ["RS"], [], "inbound", 10),
    ("Truckers' strike in Curitiba, shipments out of the city stuck for a week", [], ["curitiba"], "outbound", 7),
    ("Port issues around Rio de Janeiro affecting shipments both ways for 3 days", ["RJ"], [], "both", 3),
    ("Storm in Belo Horizonte, deliveries arriving in the city delayed 48 hours", [], ["belo horizonte"], "inbound", 2),
    ("A road collapse in Bahia is holding up freight", ["BA"], [], "outbound", 3),
])
def test_phase3_table(query, states, cities, direction, days):
    event = parse(query).event
    assert (event.states, event.cities, event.direction, event.delay_days) == (states, cities, direction, days)


def test_no_location_gives_empty_places():
    event = parse("Something bad happened").event
    assert event.states == [] and event.cities == []
    assert "No Brazilian city or state" in event.interpretation


def test_defaults_are_listed():
    result = parse("A road collapse in Bahia is holding up freight")
    assert result.event.disruption_type == "infrastructure"
    text = " ".join(result.assumptions)
    assert "assumed 3 days" in text and "outbound" in text and "product focus" in text


def test_state_name_with_accents():
    assert parse("Chuvas em São Paulo, freight leaving for 4 days").event.states == ["SP"]


def test_uppercase_codes_count_but_common_words_do_not():
    event = parse("Floods in MG are delaying trucks going to the coast, es muy malo").event
    assert event.states == ["MG"]


def test_state_name_is_not_also_read_as_a_city():
    # "Rio Grande do Sul" contains the city name "rio grande"; the state must win.
    event = parse("Flooding in Rio Grande do Sul for 10 days").event
    assert event.states == ["RS"] and event.cities == []


def test_city_of_sao_paulo_means_the_city():
    event = parse("Strike in the city of Sao Paulo, shipments leaving delayed 2 days").event
    assert event.cities == ["sao paulo"] and event.states == []


def test_sao_paulo_alone_is_read_as_the_state_and_says_so():
    result = parse("Rain leaving Sao Paulo for 5 days")
    assert result.event.states == ["SP"]
    assert any("read as the state SP" in note for note in result.assumptions)


@pytest.mark.parametrize("phrase, days", [
    ("for 5 days", 5), ("for five days", 5), ("for a week", 7), ("for two weeks", 14),
    ("for 48 hours", 2), ("for 30 hours", 2),
])
def test_durations(phrase, days):
    assert rule_parser.find_days(phrase) == days


def test_long_delays_are_clamped_to_30_days():
    result = parse("Flooding in Rio Grande do Sul, deliveries into the state stuck for 60 days")
    assert result.event.delay_days == 30
    assert any("clamped" in note for note in result.assumptions)


def test_mixed_direction_words_mean_both():
    assert parse("Strike: trucks from Parana into Santa Catarina delayed 3 days").event.direction == "both"


def test_porto_alegre_is_not_a_port_closure():
    event = parse("A bridge collapse near Porto Alegre stops freight leaving the city for three weeks").event
    assert event.disruption_type == "infrastructure" and event.delay_days == 21


def test_the_word_port_is_still_a_port_closure():
    assert parse("Port issues around Rio de Janeiro for 3 days").event.disruption_type == "port_closure"
    assert parse("Customs strike at the ports of Parana for 3 days").event.disruption_type == "strike"


def test_a_duration_the_query_does_not_state_is_listed_as_an_estimate():
    from src.models import DisruptionEvent
    guessed = DisruptionEvent(disruption_type="infrastructure", states=[], cities=["feira de santana"],
                              direction="outbound", delay_days=7, product_focus="x", interpretation="")
    _, assumptions = disruption_parser.validate(guessed, "The BR-116 is shut near Feira de Santana until next Friday")
    assert "No exact duration in the query: Gemini estimated 7 days" in assumptions
