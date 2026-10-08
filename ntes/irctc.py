"""IRCTC reservation chart lookups (irctc.co.in/online-charts).

Reverse engineered from the official "Reservation Charts" web app
(browser network capture + bundle inspection). Three JSON endpoints, all
POST, no auth/captcha/cookies required:

    /online-charts/api/trainComposition   {trainNo, jDate, boardingStation}
        -> coach list (cdd), chart dates, charting/remote station,
           chart status. `boardingStation` is REQUIRED - the API returns
           "Chart not prepared" without it.

    /online-charts/api/vacantBerth        trainComposition fields + {cls, chartType}
        -> vacant berths for one class (chartType 1 = first chart,
           2 = later/second chart).

    /online-charts/api/coachComposition   trainComposition fields + {coach, cls}
        -> berth-level layout: berth no/type, from/to segments, occupancy.

Charts are only published a few hours before departure, so future dates
fail with "Chart not prepared" - that is expected, not a client bug.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from .exceptions import IRCTCError


# Base URL for the online-charts single-page app.
IRCTC_BASE = "https://www.irctc.co.in"

# The site rejects unknown user agents / cross-origin callers; mirror the
# browser so the API behaves the same as the public web page.
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
)


def _new_irctc_session() -> requests.Session:
    """Session with browser-like headers the chart API expects.

    Returns:
        A `requests.Session` preloaded with UA/Accept/Origin/Referer so a
        bare POST behaves exactly like the online-charts page.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": _BROWSER_UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en-IN;q=0.9,en-US;q=0.8,en;q=0.7",
        # Origin/Referer matter: the API is same-origin only from the SPA.
        "Origin": IRCTC_BASE,
        "Referer": f"{IRCTC_BASE}/online-charts/",
        "Content-Type": "application/json",
    })
    return session


def _norm_date(d: Optional[str]) -> str:
    """Normalize a user-supplied date to the API's YYYY-MM-DD format.

    Accepted inputs:
        - None            -> today
        - "YYYY-MM-DD"    -> returned as-is
        - "DD-MM-YYYY"    -> reordered
        - "DD/MM/YYYY"    -> reordered
        - "DD-MMM-YYYY"   -> e.g. "02-May-2026" (NTES-style date)

    Unknown formats are passed through unchanged so the API error message
    (rather than a client-side parse error) reaches the caller.
    """
    if not d:
        return datetime.now().strftime("%Y-%m-%d")
    s = d.strip()
    # ISO: YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    # DD-MM-YYYY
    m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # DD/MM/YYYY
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # DD-MMM-YYYY (e.g. 02-May-2026), NTES style
    for fmt in ("%d-%b-%Y", "%d/%b/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def irctc_reservation_chart(
    train_no: str,
    boarding_station: str,
    journey_date: Optional[str] = None,
    timeout: int = 30,
    include_vacant_berths: bool = False,
    include_coach_layout: bool = False,
    class_filter: Optional[List[str]] = None,
    chart_type: int = 2,
) -> Dict[str, Any]:
    """
    Fetch IRCTC online-charts reservation chart data.

    Args:
        train_no: Train number (e.g. "12931", "12426")
        boarding_station: Boarding station code (e.g. "ADI", "NDLS") - required by the API
        journey_date: Date in YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, or DD-MMM-YYYY (defaults to today)
        timeout: HTTP timeout
        include_vacant_berths: If True, fetch vacant berth summary per class via vacantBerth
        include_coach_layout: If True, fetch full berth layout for each coach (heavy)
        class_filter: List of class codes to restrict when fetching details
        chart_type: Chart version for vacantBerth lookups (1 = first chart, 2 = later/second chart)

    Returns:
        Dict with chart metadata (chart dates, charting/remote station), coach
        composition, and optional vacant berths / coach layouts.

    Raises:
        IRCTCError: on transport failure, bad response, or "Chart not prepared"
            (chart not yet prepared for that train/date/boarding station).
    """
    s = _new_irctc_session()
    jdate = _norm_date(journey_date)

    # 1) Chart metadata + coach list (the "composition" call). Everything
    #    else (vacantBerth / coachComposition) needs fields from this reply.
    comp_body = {"trainNo": str(train_no), "jDate": jdate, "boardingStation": boarding_station.upper()}
    try:
        r = s.post(f"{IRCTC_BASE}/online-charts/api/trainComposition", json=comp_body, timeout=timeout)
    except Exception as e:
        raise IRCTCError(f"trainComposition request failed: {e}") from e
    if r.status_code != 200:
        raise IRCTCError(f"trainComposition failed: HTTP {r.status_code} {r.text[:200]}")
    try:
        comp = r.json()
    except Exception as e:
        raise IRCTCError(f"trainComposition invalid JSON: {e} {r.text[:200]}") from e
    if comp.get("error"):
        raise IRCTCError(f"chart unavailable for {train_no} on {jdate} boarding {boarding_station.upper()}: {comp.get('error')}")

    # Normalize the response into a flatter, documented shape.
    result: Dict[str, Any] = {
        "train_no": comp.get("trainNo") or train_no,
        "train_name": comp.get("trainName"),
        "from": comp.get("from"),
        "to": comp.get("to"),
        "journey_date": jdate,
        "train_start_date": comp.get("trainStartDate"),
        "remote": comp.get("remote"),
        "next_remote": comp.get("nextRemote"),
        "avl_remote_for_booking": comp.get("avlRemoteForBooking"),
        "destination_station": comp.get("destinationStation"),
        "chart_one_date": comp.get("chartOneDate"),
        "chart_two_date": comp.get("chartTwoDate"),
        "chart_status": comp.get("chartStatusResponseDto"),
        "composition": comp.get("cdd", []),
        "boarding_station": boarding_station.upper(),
    }

    # 2) Optional: vacant berths per class. One call per distinct class
    #    (deduped); private failures are skipped so a single class outage
    #    never loses the whole result. Chart fields must match what the
    #    composition reply reported (remote station, source, train date).
    if include_vacant_berths and result["boarding_station"] and result["remote"] and result["from"]:
        vb = []
        seen_classes = set()
        for c in comp.get("cdd", []):
            cls = c.get("classCode")
            if class_filter and cls not in class_filter:
                continue
            if cls in seen_classes:
                continue
            seen_classes.add(cls)
            vb_body = {
                "trainNo": str(train_no),
                "boardingStation": result["boarding_station"],
                "remoteStation": comp.get("remote"),
                "trainSourceStation": comp.get("from"),
                # Follow-up calls key off the train's actual start date,
                # which can be one day earlier for overnight trains.
                "jDate": comp.get("trainStartDate") or jdate,
                "cls": cls,
                "chartType": chart_type,
            }
            try:
                vr = s.post(f"{IRCTC_BASE}/online-charts/api/vacantBerth", json=vb_body, timeout=timeout)
                if vr.status_code == 200:
                    vb.append({"cls": cls, "data": vr.json()})
            except Exception:
                continue  # best-effort: keep whatever classes succeeded
        result["vacant_berths"] = vb

    # 3) Optional: berth-level layout per coach (heavy: one call per coach,
    #    so use class_filter to limit it). Same request fields as vacantBerth
    #    plus the coach name. Best-effort like above.
    if include_coach_layout and result["boarding_station"] and result["remote"] and result["from"]:
        layouts = []
        for c in comp.get("cdd", []):
            cls = c.get("classCode")
            coach = c.get("coachName")
            if class_filter and cls not in class_filter:
                continue
            cl_body = {
                "trainNo": str(train_no),
                "boardingStation": result["boarding_station"],
                "remoteStation": comp.get("remote"),
                "trainSourceStation": comp.get("from"),
                "jDate": comp.get("trainStartDate") or jdate,
                "coach": coach,
                "cls": cls,
            }
            try:
                cr = s.post(f"{IRCTC_BASE}/online-charts/api/coachComposition", json=cl_body, timeout=timeout)
                if cr.status_code == 200:
                    layouts.append({"coach": coach, "cls": cls, "data": cr.json()})
            except Exception:
                continue  # best-effort: keep whatever coaches succeeded
        result["coach_layouts"] = layouts

    return result


# Convenience alias so callers can use either name.
reservation_chart = irctc_reservation_chart
