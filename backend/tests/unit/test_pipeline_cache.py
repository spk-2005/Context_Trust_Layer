"""
Unit tests for Content-Addressed PipelineStageCache.

Validates:
1. 4-factor cryptographic cache key determinism.
2. Cache hit on identical source bytes and versions.
3. Cache miss on changed source bytes.
4. Cache miss on changed parser version.
5. Cache miss on changed normalizer version.
6. Cache miss on changed parser configuration.
7. Graceful recovery and eviction on corrupted cache files.
8. Graceful eviction on incompatible model schemas.
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
def test_cache_compute_pipeline_key_dimensions(temp_cache: PipelineStageCache):
    base_key = temp_cache.compute_pipeline_key("stage", "src_sha_1", "v1.0", "cfg_1", "norm_1")

    # Identical inputs -> identical key
    same_key = temp_cache.compute_pipeline_key("stage", "src_sha_1", "v1.0", "cfg_1", "norm_1")
    assert base_key == same_key

    # Changed source SHA -> different key
    assert base_key != temp_cache.compute_pipeline_key("stage", "src_sha_2", "v1.0", "cfg_1", "norm_1")

    # Changed parser version -> different key
    assert base_key != temp_cache.compute_pipeline_key("stage", "src_sha_1", "v2.0", "cfg_1", "norm_1")

    # Changed config hash -> different key
    assert base_key != temp_cache.compute_pipeline_key("stage", "src_sha_1", "v1.0", "cfg_2", "norm_1")

    # Changed normalizer version -> different key
    assert base_key != temp_cache.compute_pipeline_key("stage", "src_sha_1", "v1.0", "cfg_1", "norm_2")


@pytest.mark.fast
@pytest.mark.unit
def test_cache_hit_on_identical_inputs(temp_cache: PipelineStageCache):
    key = temp_cache.compute_pipeline_key("universal_parser", "hash_abc", "v3.1", "cfg_def", "v1.2")
    temp_cache.set("universal_parser", key, {"text": "Extracted contract"})

    # Hit
    cached = temp_cache.get("universal_parser", key)
    assert cached is not None
    assert cached["text"] == "Extracted contract"
    assert temp_cache.stats["hits"] == 1
    assert temp_cache.stats["misses"] == 0


@pytest.mark.fast
@pytest.mark.unit
def test_cache_miss_on_changed_source_bytes(temp_cache: PipelineStageCache):
    k_v1 = temp_cache.compute_pipeline_key("universal_parser", "pdf_bytes_v1", "v3.1", "cfg_std", "v1.2")
    k_v2 = temp_cache.compute_pipeline_key("universal_parser", "pdf_bytes_v2", "v3.1", "cfg_std", "v1.2")

    temp_cache.set("universal_parser", k_v1, {"pages": 5})

    assert temp_cache.get("universal_parser", k_v1) is not None
    assert temp_cache.get("universal_parser", k_v2) is None  # Miss
    assert temp_cache.stats["misses"] == 1


@pytest.mark.fast
@pytest.mark.unit
def test_cache_miss_on_changed_parser_version(temp_cache: PipelineStageCache):
    k_old = temp_cache.compute_pipeline_key("universal_parser", "pdf_sha", "v3.0", "cfg_std", "v1.2")
    k_new = temp_cache.compute_pipeline_key("universal_parser", "pdf_sha", "v3.1", "cfg_std", "v1.2")

    temp_cache.set("universal_parser", k_old, {"pages": 1})

    assert temp_cache.get("universal_parser", k_new) is None  # Miss triggers fresh parse


@pytest.mark.fast
@pytest.mark.unit
def test_cache_miss_on_changed_normalizer_version(temp_cache: PipelineStageCache):
    k_old = temp_cache.compute_pipeline_key("universal_parser", "pdf_sha", "v3.1", "cfg_std", "v1.0")
    k_new = temp_cache.compute_pipeline_key("universal_parser", "pdf_sha", "v3.1", "cfg_std", "v1.2")

    temp_cache.set("universal_parser", k_old, {"pages": 1})

    assert temp_cache.get("universal_parser", k_new) is None


@pytest.mark.fast
@pytest.mark.unit
def test_cache_miss_on_changed_config_hash(temp_cache: PipelineStageCache):
    k_ocr_off = temp_cache.compute_pipeline_key("universal_parser", "pdf_sha", "v3.1", "ocr=false", "v1.2")
    k_ocr_on = temp_cache.compute_pipeline_key("universal_parser", "pdf_sha", "v3.1", "ocr=true", "v1.2")

    temp_cache.set("universal_parser", k_ocr_off, {"ocr": False})

    assert temp_cache.get("universal_parser", k_ocr_on) is None


@pytest.mark.fast
@pytest.mark.unit
def test_cache_corrupted_payload_safe_recompute(temp_cache: PipelineStageCache):
    key = temp_cache.compute_pipeline_key("universal_parser", "sha", "v1", "c", "n")
    stage_dir = temp_cache._get_stage_dir("universal_parser")
    corrupt_file = stage_dir / f"{key}.json"

    # Write truncated / invalid JSON
    corrupt_file.write_text("{\"unterminated_json: true, ...", encoding="utf-8")

    # Attempt to read corrupt cache: must return None without raising, and evict the file
    res = temp_cache.get("universal_parser", key)
    assert res is None
    assert not corrupt_file.exists(), "Corrupted file should be evicted"
    assert temp_cache.stats["misses"] == 1


@pytest.mark.fast
@pytest.mark.unit
def test_cache_incompatible_model_schema_eviction(temp_cache: PipelineStageCache):
    key = temp_cache.compute_key("models", "v1", "sample_input")
    # Write payload missing required 'count' field for SampleItem
    temp_cache.set("models", key, {"name": "widget_only"})

    model = temp_cache.get_model("models", key, SampleItem)
    assert model is None
    assert not (temp_cache._get_stage_dir("models") / f"{key}.json").exists(), "Incompatible model entry should be evicted"