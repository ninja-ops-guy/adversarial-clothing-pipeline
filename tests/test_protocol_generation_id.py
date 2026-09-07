"""Regression tests for the D2-0004 step-18 loader failure (CI run 34147902820).

Root cause: ``load_protocol()`` raised
``TypeError: CertificationProtocol.__init__() got an unexpected keyword
argument 'generation_id'`` on ``protocols/RAC-PERSON-DETECT-1.2.json`` —
the first protocol carrying the preregistered ``generation_id`` key.
These tests pin the fix: the dataclass must accept and carry the field,
and legacy protocols without it must keep loading unchanged.
"""

from ruthless_pipeline.certification import load_protocol


def test_protocol_12_loads_and_carries_generation_id():
    protocol = load_protocol("protocols/RAC-PERSON-DETECT-1.2.json")
    assert protocol.protocol_id == "RAC-PERSON-DETECT"
    assert protocol.version == "1.2"
    assert protocol.generation_id == "RAC-PER-D2-0004"


def test_legacy_protocols_default_generation_id_empty():
    for version in ("1.0", "1.1"):
        protocol = load_protocol(f"protocols/RAC-PERSON-DETECT-{version}.json")
        assert protocol.generation_id == ""
