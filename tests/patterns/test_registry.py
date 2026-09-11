"""Registry tests: conflicts, version resolution, P3 refusal, usage log."""
import pytest

from ruthless_pipeline.patterns import (
    DEFERRED_P3,
    GeneratorRegistrationError,
    GeneratorRegistry,
    HyperfaceLikeGenerator,
    StubPatternGenerator,
)
from ruthless_pipeline.patterns.utility import guard_p3_registration


class _DummyV19(StubPatternGenerator):
    name = "dummy"
    version = "1.9.0"
    category = "test"
    priority = "P2"


class _DummyV110(StubPatternGenerator):
    name = "dummy"
    version = "1.10.0"
    category = "test"
    priority = "P2"


class _DummyConflict(StubPatternGenerator):
    name = "dummy"
    version = "1.9.0"  # same key as _DummyV19, different class
    category = "test"
    priority = "P2"


def test_duplicate_same_class_idempotent():
    reg = GeneratorRegistry()
    reg.register(HyperfaceLikeGenerator)
    reg.register(HyperfaceLikeGenerator)  # no raise
    assert len(reg.generators) == 1


def test_duplicate_different_class_raises():
    reg = GeneratorRegistry()
    reg.register(_DummyV19)
    with pytest.raises(GeneratorRegistrationError):
        reg.register(_DummyConflict)


def test_latest_version_resolution_semantic():
    reg = GeneratorRegistry()
    reg.register(_DummyV19)
    reg.register(_DummyV110)
    assert reg.get("dummy").version == "1.10.0"  # semantic, not lexicographic
    assert reg.get("dummy", "1.9.0").version == "1.9.0"
    with pytest.raises(GeneratorRegistrationError):
        reg.get("nonexistent")


def test_list_by_priority():
    reg = GeneratorRegistry()
    reg.register(HyperfaceLikeGenerator)
    reg.register(_DummyV19)
    p0 = reg.list_by_priority("P0")
    assert [g.name for g in p0] == ["hyperface_like"]


class _BadWords(StubPatternGenerator):
    name = "bad_words"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P3"


class _WebAttackStrings(StubPatternGenerator):
    name = "web_attack_strings"
    version = "1.0.0"
    category = "texture_symbolic"
    priority = "P3"


def test_p3_refused():
    assert set(DEFERRED_P3) == {"bad_words", "web_attack_strings"}
    reg = GeneratorRegistry()
    for cls in (_BadWords, _WebAttackStrings):
        with pytest.raises(GeneratorRegistrationError):
            reg.register(cls)
        with pytest.raises(GeneratorRegistrationError):
            guard_p3_registration(cls)


def test_usage_log_canonical_and_deterministic():
    reg = GeneratorRegistry()
    reg.record_usage("hyperface_like", "D3-0001")
    reg.record_usage("hyperface_like", "D3-0002")
    reg.record_usage("landmark_noise", "D3-0001")
    expected = (b'{"hyperface_like":["D3-0001","D3-0002"],'
                b'"landmark_noise":["D3-0001"]}')
    assert reg.export_usage_log() == expected
    assert reg.export_usage_log() == expected  # stable across calls


def test_stub_registered_but_unimplemented():
    from ruthless_pipeline.patterns import (
        GeneratorParams,
        PatternNotImplementedError,
    )
    reg = GeneratorRegistry()
    reg.register(_DummyV19)
    inst = reg.get("dummy", "1.9.0")
    with pytest.raises(PatternNotImplementedError):
        inst.generate(GeneratorParams(seed=1, mask_geometry={}, output_size=(8, 8)))
