"""Encryption layer for the NTES mobile API.

The official app wraps every request/response in a custom scheme
(reverse engineered with Frida + Burp Suite):

    Request payload:  MD5(data + secret) # HEX(BASE64(AES-CBC(data)))
    Response payload: "jsonIn" field holding HEX(BASE64(AES-CBC(json)))

- Cipher: AES-128 in CBC mode with a static key/IV (extracted from the app)
- Encoding layers on the wire: raw bytes -> base64 -> uppercase hex
- Integrity/signature: MD5 of plaintext + shared secret, hex-uppercase

Both `Cryptodome` (pycryptodome) and legacy `Crypto` packages are supported.
"""

import base64
import binascii
import hashlib
from typing import Union, Any

from .exceptions import NTESCryptoError
from .utils import safe_json_loads

# Support both the modern (Cryptodome) and legacy (Crypto) pycryptodome layouts.
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad


class NTESCrypto:
    """Encrypts outgoing NTES payloads and decrypts incoming ones.

    Key/IV/secret are constants recovered from the official Android app;
    they are shared by every client, not per-user credentials.
    """

    def __init__(self):
        # AES-128 key and IV (16 bytes each), as extracted from the app binary.
        self.key = b"8EA4DB2CC1EB3DC5"
        self.iv = b"7DC5EB3BB4DB6EA8"
        # Shared secret mixed into the MD5 request signature.
        self.sckey = "645fbc1e56e23365f2f3c204ae0899f6"

    def _encrypt(self, data: str) -> str:
        """AES-CBC encrypt, then encode base64 -> uppercase hex (wire format)."""
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded = pad(data.encode("utf-8"), 16)  # PKCS#7 padding to block size
        encrypted = cipher.encrypt(padded)
        return binascii.hexlify(base64.b64encode(encrypted)).decode().upper()

    def _decode_layers(self, enc: str) -> bytes:
        """Reverse the wire encoding: hex -> base64 -> raw ciphertext bytes."""
        try:
            raw = binascii.unhexlify(enc)
            b64 = raw.decode()
            return base64.b64decode(b64)
        except Exception as e:
            raise NTESCryptoError(f"encoding error: {e}")

    def decode(self, enc: str) -> Union[dict, list, str]:
        """Decrypt a response payload and parse the contained JSON/text.

        Responses are prefixed with "<md5-signature>#"; the signature part
        is stripped before decryption. Result is parsed as JSON when
        possible, otherwise returned as plain text.

        Raises:
            NTESCryptoError: empty input, bad encoding, or decryption failure
                (typically a changed server format or truncated payload).
        """
        if not enc:
            raise NTESCryptoError("empty input")

        # Strip the leading "<signature>#" if present; only the ciphertext matters.
        if "#" in enc:
            enc = enc.split("#", 1)[1]

        try:
            cipher_bytes = self._decode_layers(enc)
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            decrypted = unpad(cipher.decrypt(cipher_bytes), 16)
            text = decrypted.decode("utf-8")
        except Exception as e:
            raise NTESCryptoError(f"decryption failed: {e}")

        return safe_json_loads(text)

    def _hash(self, data: str) -> str:
        """Request signature: uppercase MD5 of plaintext + shared secret."""
        return hashlib.md5((data + self.sckey).encode()).hexdigest().upper()

    def build(self, data: str) -> str:
        """Wrap a plaintext payload into the wire format expected by NTES.

        Returns "MD5(data + secret)#HEX(BASE64(AES(data)))".

        Raises:
            NTESCryptoError: if the payload is empty.
        """
        if not data:
            raise NTESCryptoError("empty payload")
        return f"{self._hash(data)}#{self._encrypt(data)}"
