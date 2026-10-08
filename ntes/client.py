"""Main NTES client: encrypted train enquiry API + PNR/captcha enquiry.

Two distinct backends are used:

1. NTES API (`BASE_URL`, enquiry.indianrail.gov.in) - POST of an encrypted
   payload, used by search/train_info/schedule/station_live/trains_between/
   live_status/exceptions. Traffic goes through `NTESClient._request`.
2. PNR enquiry (indianrail.gov.in/enquiry/*) - a browser-like flow that
   fetches a math captcha image, solves it locally (`ntes.pnr`), and submits
   the answer; used only by `pnr_status`.

All https sessions are built by `_new_session()`, which widens the TLS cipher
list because indianrail.gov.in only accepts legacy static-RSA TLS 1.2 suites
that OpenSSL's defaults no longer offer.
"""

import json
import os
import ssl
import time
import requests
from requests.adapters import HTTPAdapter
from typing import Any, Optional

from .crypto import NTESCrypto
from .exceptions import NTESError


# Encrypted NTES enquiry API used by all train methods (search, schedule, ...).
BASE_URL = "https://enquiry.indianrail.gov.in/crisns/AppServAnd"

# Browser-like identity for the indianrail.gov.in PNR endpoints; the site
# behaves differently (or refuses) for non-browser user agents.
_CHART_UA = "Mozilla/5.0"


def _new_session() -> requests.Session:
    """Create a session compatible with indianrail.gov.in's TLS config.

    indianrail.gov.in only accepts legacy static-RSA TLS 1.2 cipher suites
    (e.g. AES128-GCM-SHA256). OpenSSL's default cipher list excludes them,
    so the handshake fails with SSLV3_ALERT_HANDSHAKE_FAILURE unless the
    cipher list is widened. Verified fix; harmless if the server later
    re-enables modern suites - we only widen what the client offers.

    Returns:
        A `requests.Session` with the widened SSL context mounted for all
        https:// connections.
    """
    context = ssl.create_default_context()
    context.set_ciphers("DEFAULT@SECLEVEL=1")

    # HTTPAdapter.init_poolmanager forwards kwargs (ssl_context) to urllib3's
    # PoolManager, which uses it for every connection in the pool.
    adapter = HTTPAdapter()
    adapter.init_poolmanager(10, 10, ssl_context=context)

    session = requests.Session()
    session.mount("https://", adapter)
    return session


class NTESClient:
    """Client for the NTES enquiry API and the PNR captcha endpoint.

    Args:
        timeout: Per-request timeout in seconds.
        retries: Extra attempts after the first for retryable failures
            (so total attempts = retries + 1).

    Example:
        >>> client = NTESClient()
        >>> client.search("12951")
        >>> client.pnr_status("6410603220")
    """

    def __init__(self, timeout: int = 10, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self.crypto = NTESCrypto()

        # Shared session for the NTES API; widened TLS (see _new_session).
        self.session = _new_session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "charset": "utf-8",
            # The API expects the Android app's user agent.
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 11)",
        })

    def _decode(self, data: dict) -> Any:
        """Decrypt the "jsonIn" field of an NTES response (pass-through if absent)."""
        if "jsonIn" not in data:
            return data
        return self.crypto.decode(data["jsonIn"])

    def _extract_error(self, data: Any) -> Optional[str]:
        """Pull a server-side alert message out of a response, if any.

        NTES signals business errors ("invalid train", ...) via AlertMsg
        fields instead of HTTP status codes; both casing variants occur.
        """
        if isinstance(data, dict):
            return (
                data.get("AlertMsg")
                or data.get("alertMsg")
                or data.get("AlertMsgHindi")
                or data.get("alertMsgHindi")
            )
        return None

    def _request(self, payload: str) -> Any:
        """POST an encrypted payload to the NTES API with retries.

        Each attempt encrypts the payload fresh (cheap), so retries are
        safe. Failures are collected and the last one is reported so the
        caller sees the real cause (timeout, TLS, server alert, ...).

        Raises:
            NTESError: after all attempts fail; message includes the last error.
        """
        last_error: Optional[Exception] = None

        for _ in range(self.retries + 1):
            try:
                r = self.session.post(
                    BASE_URL,
                    json={"jsonIn": self.crypto.build(payload)},
                    timeout=self.timeout
                )

                # Some failure modes return an empty body with HTTP 200.
                if not r.text.strip():
                    raise NTESError("empty response")

                try:
                    data = r.json()
                except ValueError:
                    raise NTESError("invalid json response")

                decoded = self._decode(data)

                # Server-reported business error -> surface it as NTESError.
                error_msg = self._extract_error(decoded)
                if error_msg:
                    raise NTESError(error_msg)

                return decoded

            except (requests.RequestException, NTESError) as e:
                last_error = e

        raise NTESError(f"request failed: {last_error}")

    def search(self, query: str):
        """Find trains by number, name, or keyword (e.g. "12951", "rajdhani")."""
        return self._request(
            f"service=TrainRunningMob&subService=FindTrainJson&trainNo={query}"
        )

    def train_info(self, train_no: str):
        """Get train details and recent/upcoming running instances."""
        return self._request(
            f"service=TrainRunningMob&subService=GetTrainInstance&trainNo={train_no}"
        )

    def schedule(self, train_no: str, start_date: str = ""):
        """Get the full route/schedule (all stops with STA/STD).

        Args:
            train_no: 5-digit train number.
            start_date: Optional journey date (NTES format, e.g. "02-May-2026").
        """
        return self._request(
            f"service=TrainRunningMob&subService=GetTrainSchedule&trainNo={train_no}&startDate={start_date}"
        )

    def station_live(self, station_code: str, hours: int = 2):
        """Live arrivals/departures board for a station over the next `hours`."""
        return self._request(
            f"service=TrainRunningMob&subService=TrainsAtStationJson&jStation={station_code}&nHr={hours}&jToStation="
        )

    def trains_between(self, from_station: str, to_station: str, train_type: str = "XXX"):
        """List trains between two stations.

        Args:
            from_station: Source station code (e.g. "LKO").
            to_station: Destination station code (e.g. "GZB").
            train_type: Optional type filter ("XXX" = all, "SUF", "RAJ", ...).
        """
        return self._request(
           f"service=TrainRunningMob&subService=TrainBtwStnJson&stnFrom={from_station}&stnTo={to_station}&trainType={train_type}"
        )

    def live_status(self, train_no: str, start_date: str):
        """Real-time position/status of a train for a given start date."""
        return self._request(
            f"service=TrainRunningMob&subService=ShowFullRunJson&trainNo={train_no}&startDate={start_date}"
        )

    def exceptions(self, train_no: str):
        """Cancellation/diversion/rescheduling alerts for a train."""
        return self._request(
            f"service=TrainRunningMob&subService=TrainExcpInfo&trainNo={train_no}"
        )

    def pnr_status(self, pnr: str):
        """Check PNR status by solving the site's math captcha automatically.

        Flow per attempt:
            1. GET CaptchaConfig (warms the session/cookies).
            2. GET captchaDraw.png?<timestamp> and solve it (`pnr._solve`).
            3. GET CommonCaptcha with inputCaptcha/inputPnrNo and parse JSON.

        Captcha mismatches and transient failures retry up to `retries + 1`
        times; every failure path records `last_error` so the final exception
        reports the actual cause rather than a generic message.

        Args:
            pnr: 10-digit PNR number.

        Returns:
            PNR details dict (train, passengers, chart status, ...).

        Raises:
            NTESError: after all attempts fail; message includes the last error.
        """
        from .pnr import _solve

        last_error: Optional[Exception] = None

        for _ in range(self.retries + 1):
            try:
                # Fresh session per attempt: avoids stale cookies/expired
                # captcha state bleeding across retries.
                session = _new_session()

                # Step 1: initial GET sets the server-side captcha session.
                session.get(
                    "https://indianrail.gov.in/enquiry/CaptchaConfig",
                    headers={
                        "User-Agent": _CHART_UA,
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://indianrail.gov.in/enquiry/PNR/PnrEnquiry.html",
                        "Accept": "*/*"
                    },
                    timeout=self.timeout
                )

                # Step 2: fetch a fresh captcha (cache-busted with epoch ms).
                ts = int(time.time() * 1000)
                img = session.get(
                    f"https://indianrail.gov.in/enquiry/captchaDraw.png?{ts}",
                    headers={
                        "User-Agent": _CHART_UA,
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        "Referer": "https://indianrail.gov.in/enquiry/PNR/PnrEnquiry.html"
                    },
                    timeout=self.timeout
                )

                if img.status_code != 200:
                    last_error = NTESError(f"captcha image request failed: HTTP {img.status_code}")
                    continue

                # Solve locally; a failed solve just means a fresh captcha next loop.
                result = _solve(img.content)
                if not result or not result.get("success"):
                    last_error = NTESError("captcha solve failed")
                    continue

                captcha_val = str(result["answer"])

                # Step 3: submit captcha + PNR and read the JSON result.
                resp = session.get(
                    "https://indianrail.gov.in/enquiry/CommonCaptcha",
                    params={
                        "inputCaptcha": captcha_val,
                        "inputPnrNo": pnr,
                        "inputPage": "PNR",
                        "language": "en"
                    },
                    headers={
                        "User-Agent": _CHART_UA,
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "*/*",
                        "Referer": "https://indianrail.gov.in/enquiry/PNR/PnrEnquiry.html"
                    },
                    timeout=self.timeout
                )

                if not resp.text.strip():
                    last_error = NTESError("empty response from PNR endpoint")
                    continue

                data = resp.json()

                # Wrong captcha answer -> retry with a new image.
                if data.get("errorMessage") == "Captcha not matched":
                    last_error = NTESError("captcha not matched")
                    continue

                return data

            except Exception as e:
                # Broad catch is intentional: any transient failure (TLS,
                # timeout, bad JSON, solver bug) should trigger a retry,
                # with the cause preserved for the final error message.
                last_error = e

        raise NTESError(f"pnr check failed after retries: {last_error}")
