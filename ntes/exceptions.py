"""Exception types raised by the ntes package."""


class NTESError(Exception):
    """Generic failure talking to NTES/PNR endpoints.

    Raised for transport errors (timeouts, TLS, HTTP failures), malformed
    responses, server-side alert messages, and exhausted retries. The
    message always carries the underlying cause when one is known.
    """


class NTESCryptoError(Exception):
    """Raised when encrypting/decrypting an NTES payload fails.

    Usually means the response format changed, the payload was truncated,
    or the shared secret/keys no longer match.
    """


class IRCTCError(Exception):
    """Raised when an IRCTC online-charts lookup fails.

    Covers request failures, non-200/invalid JSON responses, and the
    common "Chart not prepared" case (chart does not exist yet for that
    train/date/boarding station).
    """
