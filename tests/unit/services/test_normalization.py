"""Tests for currency normalization utilities."""

import pytest

from app.services.normalization import normalize_to_eur


class TestNormalizeToEur:
    """Tests for normalize_to_eur function."""

    def test_normalize_eur_base_returns_copy_with_eur(self) -> None:
        """When base is EUR, returns copy with EUR=1.0 added."""
        rates = {"USD": 1.0823, "GBP": 0.8543}
        result = normalize_to_eur("EUR", rates)

        assert result["EUR"] == 1.0
        assert result["USD"] == 1.0823
        assert result["GBP"] == 0.8543
        # Ensure original is not modified
        assert "EUR" not in rates

    def test_normalize_eur_base_preserves_existing_eur(self) -> None:
        """When base is EUR and EUR already exists, it's overwritten to 1.0."""
        rates = {"EUR": 0.99, "USD": 1.0823}
        result = normalize_to_eur("EUR", rates)

        assert result["EUR"] == 1.0
        assert result["USD"] == 1.0823

    def test_normalize_non_eur_base_divides_by_eur_rate(self) -> None:
        """When base is not EUR, divides all rates by EUR rate."""
        # If base is USD and EUR=0.9 in USD terms,
        # then to get rates in EUR terms: rate / eur_rate
        rates = {"EUR": 0.9, "GBP": 0.75, "JPY": 145.0}
        result = normalize_to_eur("USD", rates)

        assert result["EUR"] == 1.0
        assert result["GBP"] == pytest.approx(0.75 / 0.9)
        assert result["JPY"] == pytest.approx(145.0 / 0.9)

    def test_missing_eur_rate_raises_value_error(self) -> None:
        """Raises ValueError if EUR rate is missing when base is not EUR."""
        rates = {"USD": 1.0, "GBP": 0.8}

        with pytest.raises(ValueError, match="EUR rate missing"):
            normalize_to_eur("USD", rates)

    def test_zero_eur_rate_raises_value_error(self) -> None:
        """Raises ValueError if EUR rate is zero."""
        rates = {"EUR": 0, "USD": 1.0}

        with pytest.raises(ValueError, match="EUR rate is zero"):
            normalize_to_eur("USD", rates)

    def test_preserves_all_currencies(self) -> None:
        """All input currencies are present in output."""
        rates = {"EUR": 0.85, "USD": 1.0, "GBP": 0.72, "JPY": 130.0, "CHF": 0.92}
        result = normalize_to_eur("USD", rates)

        assert set(result.keys()) == set(rates.keys())

    def test_empty_rates_with_eur_base(self) -> None:
        """Empty rates dict with EUR base returns just EUR=1.0."""
        rates: dict[str, float] = {}
        result = normalize_to_eur("EUR", rates)

        assert result == {"EUR": 1.0}

    def test_empty_rates_with_non_eur_base_raises(self) -> None:
        """Empty rates dict with non-EUR base raises ValueError."""
        rates: dict[str, float] = {}

        with pytest.raises(ValueError, match="EUR rate missing"):
            normalize_to_eur("USD", rates)
