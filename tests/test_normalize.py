from datetime import date

from cruise_tracker import normalize as n


def test_ship_key_strips_prefixes_and_punctuation():
    assert n.ship_key("MSC Bellissima") == n.ship_key("Bellissima") == "bellissima"
    assert n.ship_key("Diamond Princess") == "diamond-princess"
    assert n.ship_key("Norwegian Spirit") == n.ship_key("NORWEGIAN  spirit") == "spirit"


def test_cabin_type():
    assert n.cabin_type("Inside") == "interior"
    assert n.cabin_type("Oceanview Stateroom") == "oceanview"
    assert n.cabin_type("Balcony") == "balcony"
    assert n.cabin_type("Mini-Suite w/ Veranda") == "suite"
    assert n.cabin_type("???") is None


def test_port_code_matches_site_text():
    assert n.port_code("Keelung (Taipei), Taiwan") == "keelung"
    assert n.port_code("Tokyo (Yokohama), Japan") == "yokohama"
    assert n.port_code("Incheon (Seoul), South Korea") == "incheon"
    assert n.port_code("Nowhere") is None


def test_infer_region():
    assert n.infer_region("keelung", "keelung", ["Naha, Okinawa", "Ishigaki"]) == "japan"
    assert n.infer_region("yokohama", "vancouver", ["Honolulu"]) == "transpacific"
    assert n.infer_region("yokohama", "singapore", ["Hong Kong", "Keelung"]) in {"japan", "southeast_asia", "china", "taiwan"}


def test_match_key_is_source_independent():
    a = n.match_key("MSC Cruises", "MSC Bellissima", date(2026, 12, 1), 5)
    b = n.match_key("MSC", "Bellissima", date(2026, 12, 1), 5)
    assert a == b


def test_port_label():
    assert n.port_label("Naha, Okinawa") == "那霸（沖繩）"
    assert n.port_label("Somewhere, Japan") == "Somewhere"
