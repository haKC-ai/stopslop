"""URL fetching with an SSRF guard that re-checks every redirect hop.

The v1 guard resolved the hostname once and then let `requests` follow
redirects unchecked. Here redirects are followed manually and every hop's
hostname is resolved and re-validated before the request is made.

Known limit: DNS rebinding between the check and the request is still
possible; this guard blocks straightforward SSRF, not a rebinding attacker.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from core import USER_AGENT

_MAX_REDIRECTS = 5


def _is_public_host(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    if not infos:
        return False
    for _family, _type, _proto, _canon, sockaddr in infos:
        ip = str(sockaddr[0])
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            return False
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
        ):
            return False
    return True


def _check_url(url: str, block_private_ips: bool) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("only http and https are allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no hostname")
    if block_private_ips and not _is_public_host(host):
        raise ValueError(f"blocked non-public host {host!r} to avoid SSRF")
    return url


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _extract(html: str) -> str:
    try:
        import trafilatura

        extracted = trafilatura.extract(html, include_formatting=True)
        if extracted and len(extracted) >= 200:
            return str(extracted)
    except Exception:  # noqa: BLE001 - extraction fallback is intentional
        pass
    return _html_to_text(html)


def fetch_url(
    url: str,
    timeout_sec: int = 30,
    block_private_ips: bool = True,
) -> tuple[str, dict[str, Any]]:
    current = _check_url(url, block_private_ips)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    hops: list[str] = []
    response: requests.Response | None = None
    for _ in range(_MAX_REDIRECTS + 1):
        response = session.get(current, timeout=timeout_sec, allow_redirects=False)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            if not location:
                break
            nxt = urljoin(current, location)
            # Re-check the redirect target before following it. This is the
            # redirect-chain re-check the v1 guard was missing.
            current = _check_url(nxt, block_private_ips)
            hops.append(current)
            continue
        break
    else:
        raise ValueError(f"too many redirects (> {_MAX_REDIRECTS})")
    assert response is not None
    response.raise_for_status()
    html = response.text
    text = _extract(html)
    meta: dict[str, Any] = {
        "source": url,
        "final_url": current,
        "redirect_hops": hops,
        "fetched_at": int(time.time()),
        "bytes": len(html),
    }
    return text, meta
