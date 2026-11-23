from verificador.models import Layover, Leg, Offer
from verificador.rules import cheapest_compliant, is_compliant, leg_is_compliant

BR = frozenset({"GIG", "GRU", "VCP", "CGH", "SDU"})


def make_offer(price, out_layovers=(), in_layovers=()):
    outbound = Leg("GIG", "BUD", ("KLM",), tuple(Layover(a, m) for a, m in out_layovers))
    inbound = Leg("BER", "GIG", ("KLM",), tuple(Layover(a, m) for a, m in in_layovers))
    return Offer(price, outbound, inbound, "Light")


def test_rejects_layover_under_240():
    assert is_compliant(make_offer(19152, [("AMS", 239)]), 240, BR) is False
    assert is_compliant(make_offer(19152, [("AMS", 240)]), 240, BR) is True


def test_rejects_brazil_layover_in_any_leg():
    assert is_compliant(make_offer(17243, in_layovers=[("GRU", 600)]), 240, BR) is False
    assert is_compliant(make_offer(17243, out_layovers=[("GRU", 600)]), 240, BR) is False


def test_rejects_unknown_duration():
    assert is_compliant(make_offer(19152, [("AMS", None)]), 240, BR) is False


def test_no_layovers_is_compliant():
    assert is_compliant(make_offer(19152), 240, BR) is True


def test_cheapest_compliant_picks_lowest_price_among_passing():
    failing_cheapest = make_offer(17243, in_layovers=[("GRU", 130)])
    best = make_offer(19152, [("AMS", 420)], [("AMS", 325)])
    pricier = make_offer(20000, [("AMS", 420)], [("AMS", 325)])

    offer, discarded = cheapest_compliant([pricier, failing_cheapest, best], 240, BR)

    assert offer == best
    assert discarded == 0


def test_cheapest_compliant_counts_unknown_duration_discards():
    unknown = make_offer(15000, [("AMS", None)])
    ok = make_offer(19152, [("AMS", 420)])

    offer, discarded = cheapest_compliant([unknown, ok], 240, BR)

    assert offer == ok
    assert discarded == 1


def test_returns_none_when_all_fail():
    offer, discarded = cheapest_compliant([make_offer(17243, [("GRU", 100)])], 240, BR)

    assert offer is None
    assert discarded == 0


def test_leg_is_compliant_checks_only_that_leg():
    leg_ok = Leg("GIG", "BUD", ("KLM",), (Layover("AMS", 420),))
    leg_short = Leg("BER", "GIG", ("KLM",), (Layover("AMS", 140),))
    leg_brazil = Leg("BER", "GIG", ("TK",), (Layover("GRU", 600),))

    assert leg_is_compliant(leg_ok, 240, BR) is True
    assert leg_is_compliant(leg_short, 240, BR) is False
    assert leg_is_compliant(leg_brazil, 240, BR) is False

