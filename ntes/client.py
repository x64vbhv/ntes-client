import json
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
