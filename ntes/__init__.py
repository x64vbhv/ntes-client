"""NTES Client - unofficial Python interface for India's National Train Enquiry System.

Provides encrypted API access to train search/schedule/live status plus
PNR enquiry (with captcha solving) and IRCTC reservation chart lookups.

Public surface:
    NTESClient           - main client (NTES API, PNR enquiry)
    irctc_reservation_chart - reservation chart data from IRCTC online charts
    reservation_chart    - alias of irctc_reservation_chart
    NTESError            - generic NTES/network failure
    NTESCryptoError      - encrypt/decrypt failure
    IRCTCError           - IRCTC chart endpoint failure
"""

from .client import NTESClient
from .exceptions import NTESError, NTESCryptoError, IRCTCError
from .irctc import irctc_reservation_chart, reservation_chart

__all__ = ["NTESClient", "NTESError", "NTESCryptoError", "IRCTCError", "irctc_reservation_chart", "reservation_chart"]
