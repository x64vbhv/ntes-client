import json
import os
import time
import requests
from typing import Any, Optional

from .crypto import NTESCrypto
from .exceptions import NTESError


BASE_URL = "https://enquiry.indianrail.gov.in/crisns/AppServAnd"


class NTESClient:
    def __init__(self, timeout: int = 10, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self.crypto = NTESCrypto()

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "charset": "utf-8",
            "User-Agent": "Dalvik/2.1.0 (Linux; Android 11)",
        })

    def _decode(self, data: dict) -> Any:
        if "jsonIn" not in data:
            return data
        return self.crypto.decode(data["jsonIn"])

    def _extract_error(self, data: Any) -> Optional[str]:
        if isinstance(data, dict):
            return (
                data.get("AlertMsg")
                or data.get("alertMsg")
                or data.get("AlertMsgHindi")
                or data.get("alertMsgHindi")
            )
        return None

    def _request(self, payload: str) -> Any:
        last_error: Optional[Exception] = None

        for _ in range(self.retries + 1):
            try:
                r = self.session.post(
                    BASE_URL,
                    json={"jsonIn": self.crypto.build(payload)},
                    timeout=self.timeout
                )

                if not r.text.strip():
                    raise NTESError("empty response")

                try:
                    data = r.json()
                except ValueError:
                    raise NTESError("invalid json response")

                decoded = self._decode(data)

                error_msg = self._extract_error(decoded)
                if error_msg:
                    raise NTESError(error_msg)

                return decoded

            except (requests.RequestException, NTESError) as e:
                last_error = e

        raise NTESError(f"request failed: {last_error}")

    def search(self, query: str):
        return self._request(
            f"service=TrainRunningMob&subService=FindTrainJson&trainNo={query}"
        )

    def train_info(self, train_no: str):
        return self._request(
            f"service=TrainRunningMob&subService=GetTrainInstance&trainNo={train_no}"
        )

    def schedule(self, train_no: str, start_date: str = ""):
        return self._request(
            f"service=TrainRunningMob&subService=GetTrainSchedule&trainNo={train_no}&startDate={start_date}"
        )

    def station_live(self, station_code: str, hours: int = 2):
        return self._request(
            f"service=TrainRunningMob&subService=TrainsAtStationJson&jStation={station_code}&nHr={hours}&jToStation="
        )

    def live_status(self, train_no: str, start_date: str):
        return self._request(
            f"service=TrainRunningMob&subService=ShowFullRunJson&trainNo={train_no}&startDate={start_date}"
        )

    def exceptions(self, train_no: str):
        return self._request(
            f"service=TrainRunningMob&subService=TrainExcpInfo&trainNo={train_no}"
        )

    def pnr_status(self, pnr: str):
        from .pnr import _solve

        for _ in range(self.retries + 1):
            try:
                session = requests.Session()

                session.get(
                    "https://indianrail.gov.in/enquiry/CaptchaConfig",
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://indianrail.gov.in/enquiry/PNR/PnrEnquiry.html",
                        "Accept": "*/*"
                    }, 
                    timeout=self.timeout
                )

                ts = int(time.time() * 1000)
                img = session.get(
                    f"https://indianrail.gov.in/enquiry/captchaDraw.png?{ts}",
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        "Referer": "https://indianrail.gov.in/enquiry/PNR/PnrEnquiry.html"
                    }, 
                    timeout=self.timeout
                )

                if img.status_code != 200:
                    continue

                result = _solve(img.content)
                if not result or not result.get("success"):
                    continue

                captcha_val = str(result["answer"])

                resp = session.get(
                    "https://indianrail.gov.in/enquiry/CommonCaptcha",
                    params={
                        "inputCaptcha": captcha_val,
                        "inputPnrNo": pnr,
                        "inputPage": "PNR",
                        "language": "en"
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "*/*",
                        "Referer": "https://indianrail.gov.in/enquiry/PNR/PnrEnquiry.html"
                    }, 
                    timeout=self.timeout
                )

                if not resp.text.strip():
                    continue

                data = resp.json()

                if data.get("errorMessage") == "Captcha not matched":
                    continue

                return data

            except Exception as e:
                continue

        raise NTESError("pnr check failed after retries")
