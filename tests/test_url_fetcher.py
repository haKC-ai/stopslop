"""SSRF guard: kept from v1 (the one thing that was right), plus the
redirect-chain re-check v1 was missing."""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

from core import USER_AGENT
from core.extractors.url_fetcher import _check_url, _is_public_host, fetch_url


def _addrinfo(ip: str) -> list[Any]:
    return [(2, 1, 6, "", (ip, 443))]


class TestHostGuard:
    @pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "0.0.0.0"])
    def test_non_public_ips_blocked(self, ip: str) -> None:
        with mock.patch("socket.getaddrinfo", return_value=_addrinfo(ip)):
            assert _is_public_host("evil.example") is False

    def test_public_ip_allowed(self) -> None:
        with mock.patch("socket.getaddrinfo", return_value=_addrinfo("93.184.216.34")):
            assert _is_public_host("example.com") is True

    def test_unresolvable_blocked(self) -> None:
        with mock.patch("socket.getaddrinfo", side_effect=OSError):
            assert _is_public_host("nope.invalid") is False

    def test_non_http_scheme_rejected(self) -> None:
        with pytest.raises(ValueError, match="http"):
            _check_url("file:///etc/passwd", block_private_ips=True)
        with pytest.raises(ValueError, match="http"):
            _check_url("gopher://example.com/", block_private_ips=True)


class _FakeResponse:
    def __init__(self, status: int, location: str | None = None, text: str = "") -> None:
        self.status_code = status
        self.headers = {"Location": location} if location else {}
        self.text = text
        self.is_redirect = status in (301, 302, 303, 307, 308) and location is not None
        self.is_permanent_redirect = status in (301, 308) and location is not None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class TestRedirectRecheck:
    """v1 resolved the hostname once, then requests followed redirects
    unchecked. v2 re-validates every hop."""

    def test_redirect_to_private_host_blocked(self) -> None:
        responses = [_FakeResponse(302, location="http://169.254.169.254/latest/meta-data/")]

        def public_only(host: str) -> bool:
            return host == "start.example"

        with (
            mock.patch("core.extractors.url_fetcher._is_public_host", side_effect=public_only),
            mock.patch("requests.Session.get", side_effect=responses),pytest.raises(ValueError, match="SSRF")
        ):
            fetch_url("https://start.example/page")

    def test_clean_redirect_followed(self) -> None:
        responses = [
            _FakeResponse(302, location="https://final.example/doc"),
            _FakeResponse(200, text="<html><body><p>" + "content word " * 60 + "</p></body></html>"),
        ]
        with (
            mock.patch("core.extractors.url_fetcher._is_public_host", return_value=True),
            mock.patch("requests.Session.get", side_effect=responses),
        ):
            text, meta = fetch_url("https://start.example/page")
        assert "content word" in text
        assert meta["final_url"] == "https://final.example/doc"
        assert meta["redirect_hops"] == ["https://final.example/doc"]

    def test_redirect_loop_bounded(self) -> None:
        looping = [_FakeResponse(302, location="https://start.example/page") for _ in range(10)]
        with (
            mock.patch("core.extractors.url_fetcher._is_public_host", return_value=True),
            mock.patch("requests.Session.get", side_effect=looping),
            pytest.raises(ValueError, match="redirects"),
        ):
            fetch_url("https://start.example/page")


def test_user_agent_is_stopslop() -> None:
    assert USER_AGENT.split("/")[0] == "stopslop"
