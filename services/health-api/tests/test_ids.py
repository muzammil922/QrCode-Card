from app.services.ids import generate_qr_token, generate_uhid, hash_qr_token


def test_uhid_format_and_uniqueness():
    a = generate_uhid()
    b = generate_uhid()
    assert a.startswith("UHQ-")
    assert a != b
    assert len(a) > 8


def test_qr_token_opaque_and_hashed():
    raw = generate_qr_token()
    assert len(raw) >= 32
    # Must not look like embedded PHI fields
    assert "CNIC" not in raw
    assert "diagnosis" not in raw.lower()
    digest = hash_qr_token(raw)
    assert len(digest) == 64
    assert digest == hash_qr_token(raw)
    assert digest != hash_qr_token(raw + "x")
