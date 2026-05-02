import base64
import binascii
import hashlib
from typing import Union, Any

from .exceptions import NTESCryptoError
from .utils import safe_json_loads

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad

class NTESCrypto:
    def __init__(self):
        self.key = b"8EA4DB2CC1EB3DC5"
        self.iv = b"7DC5EB3BB4DB6EA8"
        self.sckey = "645fbc1e56e23365f2f3c204ae0899f6"

    def _encrypt(self, data: str) -> str:
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded = pad(data.encode("utf-8"), 16)
        encrypted = cipher.encrypt(padded)
        return binascii.hexlify(base64.b64encode(encrypted)).decode().upper()

    def _decode_layers(self, enc: str) -> bytes:
        try:
            raw = binascii.unhexlify(enc)
            b64 = raw.decode()
            return base64.b64decode(b64)
        except Exception as e:
            raise NTESCryptoError(f"encoding error: {e}")

    def decode(self, enc: str) -> Union[dict, list, str]:
        if not enc:
            raise NTESCryptoError("empty input")

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
        return hashlib.md5((data + self.sckey).encode()).hexdigest().upper()

    def build(self, data: str) -> str:
        if not data:
            raise NTESCryptoError("empty payload")
        return f"{self._hash(data)}#{self._encrypt(data)}"