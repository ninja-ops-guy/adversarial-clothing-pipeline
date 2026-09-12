from rac_prc.canonical import RACCanonicalSerializer


def test_canonical_vectors():
    assert RACCanonicalSerializer.compute_sha256({"b": 2.0, "a": [True, None, -0.0]}) == "bcc05b0b2b9d8add02ae2096a65eb28a2c49057e1d9fef891c925ab93974f2e7"
    assert RACCanonicalSerializer.compute_sha256({"escapes": 'Quote: " Slash: \\'}) == "f0782bae74024630b61325493e7ca5c7e8c3377178e27be53bb7b8a6f7ae338a"


def test_nonfinite_refused():
    import pytest
    with pytest.raises(ValueError):
        RACCanonicalSerializer.serialize({"x": float("nan")})
