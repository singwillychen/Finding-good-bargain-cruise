"""Does a sailing/deal match a user's Watch?"""

from .models import Deal, Watch
from .scoring import collect_prices


def deal_matches(watch: Watch, deal: Deal) -> bool:
    s = deal.sailing
    if watch.embark_port_ids and s.embark_port_id not in watch.embark_port_ids:
        return False
    if watch.region_ids and s.region_id not in watch.region_ids:
        return False
    if watch.disembark_port_ids and s.disembark_port_id not in watch.disembark_port_ids:
        return False
    if watch.cruise_line_ids and s.ship.cruise_line_id not in watch.cruise_line_ids:
        return False
    if watch.date_from and s.depart_date < watch.date_from:
        return False
    if watch.date_to and s.depart_date > watch.date_to:
        return False
    if watch.nights_min and s.nights < watch.nights_min:
        return False
    if watch.nights_max and s.nights > watch.nights_max:
        return False

    price = deal.best_price_pp
    if watch.cabin_types:
        sp = collect_prices(s, watch.cabin_types)
        if sp is None:
            return False
        price = sp.best.price
    if watch.max_price_pp and price > watch.max_price_pp:
        return False
    if watch.max_price_per_night and price / max(s.nights, 1) > watch.max_price_per_night:
        return False
    return True
