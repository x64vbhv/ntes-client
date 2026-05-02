from ntes.crypto import NTESCrypto

def test_encrypt_decrypt():
    crypto = NTESCrypto()
    data = "service=test"
    enc = crypto.build(data)
    dec = crypto.decode(enc)
    assert dec == data