"""Tests for HTTP caching utilities."""

from fastapi import Request, Response

from app.utils.caching import (
    apply_cache_headers,
    build_etag,
    check_etag_match,
    create_not_modified_response,
)


class TestBuildEtag:
    """Tests for build_etag function."""

    def test_deterministic_same_payload(self) -> None:
        """Same payload produces same ETag."""
        payload = {"base": "EUR", "rates": {"USD": 1.0823}}

        etag1 = build_etag(payload)
        etag2 = build_etag(payload)

        assert etag1 == etag2

    def test_different_payloads_different_etags(self) -> None:
        """Different payloads produce different ETags."""
        payload1 = {"base": "EUR", "rates": {"USD": 1.0823}}
        payload2 = {"base": "EUR", "rates": {"USD": 1.0824}}

        etag1 = build_etag(payload1)
        etag2 = build_etag(payload2)

        assert etag1 != etag2

    def test_key_order_independent(self) -> None:
        """Key order does not affect ETag (sorted keys)."""
        payload1 = {"a": 1, "b": 2, "c": 3}
        payload2 = {"c": 3, "a": 1, "b": 2}

        etag1 = build_etag(payload1)
        etag2 = build_etag(payload2)

        assert etag1 == etag2

    def test_nested_key_order_independent(self) -> None:
        """Nested dict key order does not affect ETag."""
        payload1 = {"rates": {"USD": 1.08, "GBP": 0.85}}
        payload2 = {"rates": {"GBP": 0.85, "USD": 1.08}}

        etag1 = build_etag(payload1)
        etag2 = build_etag(payload2)

        assert etag1 == etag2

    def test_etag_format_quoted(self) -> None:
        """ETag is wrapped in double quotes per HTTP spec."""
        payload = {"test": "data"}
        etag = build_etag(payload)

        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_etag_is_sha256_hex(self) -> None:
        """ETag contains SHA256 hex digest (64 chars)."""
        payload = {"test": "data"}
        etag = build_etag(payload)

        # Remove quotes and check length
        digest = etag.strip('"')
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_empty_payload(self) -> None:
        """Empty dict produces valid ETag."""
        payload: dict = {}
        etag = build_etag(payload)

        assert etag.startswith('"')
        assert etag.endswith('"')
        assert len(etag.strip('"')) == 64


class TestApplyCacheHeaders:
    """Tests for apply_cache_headers function."""

    def test_sets_etag_header(self) -> None:
        """Sets ETag header on response."""
        response = Response()
        etag = '"test-etag"'

        apply_cache_headers(response, etag, cache_ttl=3600)

        assert response.headers["ETag"] == etag

    def test_sets_cache_control_header(self) -> None:
        """Sets Cache-Control header with correct TTL."""
        response = Response()
        etag = '"test-etag"'

        apply_cache_headers(response, etag, cache_ttl=3600)

        cache_control = response.headers["Cache-Control"]
        assert "public" in cache_control
        assert "max-age=3600" in cache_control
        assert "s-maxage=3600" in cache_control
        assert "stale-while-revalidate=3600" in cache_control
        assert "stale-if-error=3600" in cache_control

    def test_different_ttl_values(self) -> None:
        """Cache-Control uses provided TTL value."""
        response = Response()
        etag = '"test-etag"'

        apply_cache_headers(response, etag, cache_ttl=86400)

        cache_control = response.headers["Cache-Control"]
        assert "max-age=86400" in cache_control


class TestCheckEtagMatch:
    """Tests for check_etag_match function."""

    def test_returns_true_when_match(self) -> None:
        """Returns True when if-none-match header matches ETag."""
        # Create a mock request with the header
        scope = {
            "type": "http",
            "headers": [(b"if-none-match", b'"matching-etag"')],
        }
        request = Request(scope)

        result = check_etag_match(request, '"matching-etag"')

        assert result is True

    def test_returns_false_when_no_match(self) -> None:
        """Returns False when if-none-match header doesn't match."""
        scope = {
            "type": "http",
            "headers": [(b"if-none-match", b'"different-etag"')],
        }
        request = Request(scope)

        result = check_etag_match(request, '"current-etag"')

        assert result is False

    def test_returns_false_when_no_header(self) -> None:
        """Returns False when no if-none-match header present."""
        scope = {
            "type": "http",
            "headers": [],
        }
        request = Request(scope)

        result = check_etag_match(request, '"any-etag"')

        assert result is False


class TestCreateNotModifiedResponse:
    """Tests for create_not_modified_response function."""

    def test_returns_304_status(self) -> None:
        """Returns response with 304 status code."""
        response = create_not_modified_response('"test-etag"', cache_ttl=3600)

        assert response.status_code == 304

    def test_includes_etag_header(self) -> None:
        """Response includes ETag header."""
        etag = '"test-etag"'
        response = create_not_modified_response(etag, cache_ttl=3600)

        assert response.headers["ETag"] == etag

    def test_includes_cache_control_header(self) -> None:
        """Response includes Cache-Control header."""
        response = create_not_modified_response('"test-etag"', cache_ttl=3600)

        assert "Cache-Control" in response.headers
        assert "max-age=3600" in response.headers["Cache-Control"]
