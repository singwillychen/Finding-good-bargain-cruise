from .base import RawPrice, RawSailing, SourceAdapter


def get_adapter(name: str) -> SourceAdapter:
    if name == "vtg":
        from .vtg import VacationsToGoAdapter

        return VacationsToGoAdapter()
    if name == "cruisedirect":
        from .cruisedirect import CruiseDirectAdapter

        return CruiseDirectAdapter()
    if name == "demo":
        from .demo import DemoAdapter

        return DemoAdapter()
    raise ValueError(f"unknown source: {name}")


__all__ = ["RawPrice", "RawSailing", "SourceAdapter", "get_adapter"]
