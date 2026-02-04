"""Currency normalization utilities."""


def normalize_to_eur(base: str, rates: dict[str, float]) -> dict[str, float]:
    """
    Normalize exchange rates to EUR base currency.

    Args:
        base: The current base currency code
        rates: Dictionary of currency codes to exchange rates

    Returns:
        Dictionary of normalized rates with EUR as base (rate 1.0)

    Raises:
        ValueError: If EUR rate is missing or zero when base is not EUR
    """
    if base == "EUR":
        normalized = dict(rates)
        normalized["EUR"] = 1.0
        return normalized

    if "EUR" not in rates:
        raise ValueError("EUR rate missing for base conversion")

    eur_per_base = rates["EUR"]
    if eur_per_base == 0:
        raise ValueError("EUR rate is zero, cannot normalize")

    normalized = {code: rate / eur_per_base for code, rate in rates.items()}
    normalized["EUR"] = 1.0
    return normalized
