"""
Unit tests for Content-Addressed PipelineStageCache.
"""

import shutil
from pathlib import Path
import pytest
from pydantic import BaseModel

from app.caching.pipeline_cache import PipelineStageCache


class SampleItem(BaseModel):
    name: str
    count: int


@pytest.fixture
def temp_cache(tmp_path: Path):
    cache = PipelineStageCache(cache_dir=tmp_path / "cache", enabled=True)
    yield cache
    if (tmp_path / "cache").exists():
        shutil.rmtree(tmp_path / "cache")


@pytest.mark.fast
@pytest.mark.unit
def test_cache_compute_key_deterministic(temp_cache: PipelineStageCache):
    k1 = temp_cache.compute_key("parser", "v1.0", b"test pdf bytes")
    k2 = temp_cache.compute_key("parser", "v1.0", b"test pdf bytes")
    k3 = temp_cache.compute_key("parser", "v1.1", b"test pdf bytes")
    assert k1 == k2
    assert k1 != k3


@pytest.mark.fast
@pytest.mark.unit
def test_cache_set_and_get(temp_cache: PipelineStageCache):
    key = temp_cache.compute_key("extraction", "v1", {"input": "foo"})
    assert temp_cache.get("extraction", key) is None
    assert temp_cache.has("extraction", key) is False

    temp_cache.set("extraction", key, {"result": "bar"}, metadata={"doc": "DOC-001"})
    assert temp_cache.has("extraction", key) is True

    cached = temp_cache.get("extraction", key)
    assert cached is not None
    assert cached["result"] == "bar"
    assert cached["_cache_metadata"]["doc"] == "DOC-001"


@pytest.mark.fast
@pytest.mark.unit
def test_cache_pydantic_model_roundtrip(temp_cache: PipelineStageCache):
    key = temp_cache.compute_key("models", "v1", "sample_input")
    model = SampleItem(name="widget", count=42)

    temp_cache.set("models", key, model)
    restored = temp_cache.get_model("models", key, SampleItem)
    assert restored is not None
    assert restored.name == "widget"
    assert restored.count == 42


@pytest.mark.fast
@pytest.mark.unit
def test_cache_disabled_behavior(tmp_path: Path):
    disabled_cache = PipelineStageCache(cache_dir=tmp_path / "cache", enabled=False)
    key = disabled_cache.compute_key("stage", "v1", "data")
    disabled_cache.set("stage", key, {"value": 123})
    assert disabled_cache.get("stage", key) is None
    assert disabled_cache.has("stage", key) is False


@pytest.mark.fast
@pytest.mark.unit
def test_cache_clear_and_stats(temp_cache: PipelineStageCache):
    k1 = temp_cache.compute_key("s1", "v1", "item1")
    k2 = temp_cache.compute_key("s2", "v1", "item2")
    temp_cache.set("s1", k1, {"val": 1})
    temp_cache.set("s2", k2, {"val": 2})

    temp_cache.get("s1", k1)  # hit
    temp_cache.get("s1", "missing")  # miss

    stats = temp_cache.stats
    assert stats["hits"] == 1
    assert stats["misses"] == 1

    deleted = temp_cache.clear("s1")
    assert deleted == 1
    assert temp_cache.get("s1", k1) is None
    assert temp_cache.get("s2", k2) is not None