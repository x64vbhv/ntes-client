# PNR Status Failure: TLS Cipher Fix

## Symptom

```python
from ntes import NTESClient
NTESClient().pnr_status("6410603220")
# ntes.exceptions.NTESError: pnr check failed after retries
```

All other methods (`search`, `live_status`, `schedule`, ...) worked fine.

## Root Cause

Two stacked problems in `ntes/client.py`:

1. **TLS handshake failure (the real bug).** `indianrail.gov.in` (the
   captcha/PNR host, distinct from `enquiry.indianrail.gov.in` used by the
   other methods) only accepts **static-RSA TLS 1.2 cipher suites**
   (`AES128-GCM-SHA256`, `AES256-GCM-SHA384`). Python/OpenSSL's default
   cipher list only offers forward-secrecy suites (ECDHE/DHE) plus TLS 1.3,
   so every request to that host failed with:

   ```
   ssl.SSLError: [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure
   ```

   This affected `CaptchaConfig`, `captchaDraw.png` and `CommonCaptcha`
   equally — the captcha solver never even got an image to solve.

2. **Error swallowing (why the message was useless).** `pnr_status` wrapped
   every attempt in `except Exception: continue`, discarding the `SSLError`,
   then raised a generic `NTESError("pnr check failed after retries")`.

Diagnosis details:

- `set_ciphers("DEFAULT@SECLEVEL=1")` / `"DEFAULT"` / `"DEFAULT@SECLEVEL=2"`
  all handshaked successfully (server negotiated
  `TLSv1.2 AES128-GCM-SHA256`); ECDHE-only, DHE-only, CBC and TLS1.3-only
  offers were rejected with `handshake_failure` (alert 40).
- Plain `requests.get("https://indianrail.gov.in/enquiry/CaptchaConfig")`
  reproduced the failure; TLS to other hosts (e.g. google.com) worked, so it
  was host-specific, not a broken Python install.
- Monkeypatching urllib3's SSL context to widen the cipher list made the
  **unmodified** `pnr_status("6410603220")` return full data — proving the
  captcha solver and request logic were fine.
- Nothing in the repo had changed (git history was clean); the site-side TLS
  configuration had changed.

## Fix

`ntes/client.py`:

1. Added `_new_session()`, which builds a `requests.Session` whose pool
   manager uses an `ssl.SSLContext` with `set_ciphers("DEFAULT@SECLEVEL=1")`,
   and mounts it for all `https://` traffic. Used for both the main API
   session (`__init__`) and the per-call session inside `pnr_status`.

   ```python
   context = ssl.create_default_context()
   context.set_ciphers("DEFAULT@SECLEVEL=1")
   adapter = HTTPAdapter()
   adapter.init_poolmanager(10, 10, ssl_context=context)
   ```

2. `pnr_status` now records `last_error` on every failed/skipped attempt
   (HTTP error, captcha solve failure, empty response, captcha mismatch,
   exceptions) and includes it in the final raise:

   ```python
   raise NTESError(f"pnr check failed after retries: {last_error}")
   ```

   So future failures surface the underlying cause (e.g. the `SSLError`)
   instead of a bare message.

## Verification

```bash
pytest -q                      # 2 passed
python -c "from ntes import NTESClient; print(NTESClient().search('12951'))"   # ok
python -c "from ntes import NTESClient; print(NTESClient().pnr_status('6410603220'))"
# -> full PNR JSON: 14015 SADBHAVANA EXP, MFP -> GZB, 3A, CNF/B1/23, Chart Prepared
```

Forcing the old plain-session behavior now produces the real error:

```
NTESError: pnr check failed after retries: ... (Caused by SSLError(... [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ...))
```

## Notes / Trade-offs

- `DEFAULT@SECLEVEL=1` lowers OpenSSL's security level (allows legacy
  static-RSA key exchange, 80-bit security, SHA-1 signatures) for **all**
  requests made by this client. That is required by the target host's
  current TLS config; the PNR data itself is public information. If
  `indianrail.gov.in` re-enables modern ciphers, the explicit cipher list
  can be removed.
- If the server ever starts accepting ECDHE/TLS 1.3 again, this change is
  harmless — it only widens what the client offers, never narrows it.
