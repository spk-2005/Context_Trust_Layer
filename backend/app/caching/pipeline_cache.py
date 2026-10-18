"""
Content-Addressed Pipeline Stage Cache.

Provides cryptographic (SHA-256) caching for expensive pipeline operations:
1. Document Parsing & Structure Extraction (OCR, PDF AST)
2. Layer 5 Candidate Claim Discovery & Extraction
3. Layer 6 Validation Gate Invariant Evaluations

Eliminates redundant processing when source documents, schemas, and code version hashes
have not changed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_CACHE_DIR = Path("B:/Context_Layer_Ai/.pipeline_cache")


class PipelineStageCache:
    """Persistent, content-addressed disk cache for pipeline stages."""

    def __init__(self, cache_dir: Optional[Path] = None, enabled: Optional[bool] = None):
        if cache_dir is None:
            env_dir = os.environ.get("CONTEXT_LAYER_CACHE_DIR")
            self.cache_dir = Path(env_dir) if env_dir else DEFAULT_CACHE_DIR
        else:
            self.cache_dir = cache_dir

        if enabled is None:
            self.enabled = os.environ.get("CONTEXT_LAYER_NO_CACHE", "0") != "1"
        else:
            self.enabled = enabled

        self._hits = 0
        self._misses = 0

    def compute_key(
        self,
        stage_name: str,
        code_version: str,
        input_data: bytes | str | Dict[str, Any] | list,
    ) -> str:
        """Computes deterministic SHA-256 cache key from stage, code version, and input."""
        hasher = hashlib.sha256()
        hasher.update(stage_name.encode("utf-8"))
        hasher.update(code_version.encode("utf-8"))

        if isinstance(input_data, bytes):
            hasher.update(input_data)
        elif isinstance(input_data, str):
            hasher.update(input_data.encode("utf-8"))
        else:
            serialized = json.dumps(input_data, sort_keys=True, separators=(",", ":"), default=str)
            hasher.update(serialized.encode("utf-8"))

        return hasher.hexdigest()

    def compute_pipeline_key(
        self,
        stage_name: str,
        source_sha256: str,
        parser_version: str,
        parser_config_hash: str,
        normalizer_version: str,
    ) -> str:
        """Computes deterministic 4-factor cryptographic cache key for document processing.

        Incorporates:
        1. Source file SHA-256
        2. Parser implementation version
        3. Parser configuration hash (OCR, table, layout flags)
        4. Normalizer semantic rules version
        """
        hasher = hashlib.sha256()
        hasher.update(stage_name.encode("utf-8"))
        hasher.update(source_sha256.encode("utf-8"))
        hasher.update(parser_version.encode("utf-8"))
        hasher.update(parser_config_hash.encode("utf-8"))
        hasher.update(normalizer_version.encode("utf-8"))
        return hasher.hexdigest()

    def _get_stage_dir(self, stage_name: str) -> Path:
        stage_dir = self.cache_dir / stage_name
        stage_dir.mkdir(parents=True, exist_ok=True)
        return stage_dir

    def get(self, stage_name: str, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached JSON payload if present and cache is enabled. Gracefully evicts corrupted files."""
        if not self.enabled:
            return None

        target_file = self._get_stage_dir(stage_name) / f"{cache_key}.json"
        if not target_file.exists():
            self._misses += 1
            return None

        try:
            content = target_file.read_text(encoding="utf-8")
            data = json.loads(content)
            self._hits += 1
            logger.debug("Pipeline cache HIT for %s:%s", stage_name, cache_key[:12])
            return data
        except Exception as e:
            logger.warning("Corrupted cache entry evicted for %s:%s: %s", stage_name, cache_key[:12], e)
            try:
                target_file.unlink(missing_ok=True)
            except Exception:
                pass
            self._misses += 1
            return None

    def get_model(self, stage_name: str, cache_key: str, model_cls: Type[T]) -> Optional[T]:
        """Retrieves and deserializes cached Pydantic model with safe fallback on corruption."""
        data = self.get(stage_name, cache_key)
        if data is None:
            return None
        try:
            return model_cls.model_validate(data)
        except Exception as e:
            logger.warning("Cached data incompatible with model %s (%s); evicting corrupted cache.", model_cls.__name__, e)
            try:
                (self._get_stage_dir(stage_name) / f"{cache_key}.json").unlink(missing_ok=True)
            except Exception:
                pass
            self._misses += 1
            return None

    def set(
        self,
        stage_name: str,
        cache_key: str,
        value: Dict[str, Any] | BaseModel | str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Stores entry in cache."""
        if not self.enabled:
            return

        target_file = self._get_stage_dir(stage_name) / f"{cache_key}.json"
        try:
            if isinstance(value, BaseModel):
                payload = value.model_dump(mode="json")
            elif isinstance(value, (dict, list)):
                payload = value
            elif isinstance(value, str):
                payload = {"_raw_string": value}
            else:
                payload = {"data": str(value)}

            if metadata:
                payload["_cache_metadata"] = metadata

            target_file.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            logger.debug("Pipeline cache STORED for %s:%s", stage_name, cache_key[:12])
        except Exception as e:
            logger.warning("Failed to write cache for %s:%s: %s", stage_name, cache_key[:12], e)

    def has(self, stage_name: str, cache_key: str) -> bool:
        if not self.enabled:
            return False
        return (self._get_stage_dir(stage_name) / f"{cache_key}.json").exists()

    def clear(self, stage_name: Optional[str] = None) -> int:
        """Clears cached items. Returns number of items deleted."""
        deleted = 0
        if stage_name:
            stage_dir = self.cache_dir / stage_name
            if stage_dir.exists():
                for f in stage_dir.glob("*.json"):
                    try:
                        f.unlink()
                        deleted += 1
                    except Exception:
                        pass
        else:
            if self.cache_dir.exists():
                for f in self.cache_dir.rglob("*.json"):
                    try:
                        f.unlink()
                        deleted += 1
                    except Exception:
                        pass
        return deleted

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total,
            "hit_ratio": (self._hits / total) if total > 0 else 0.0,
        }


# Global default instance
default_pipeline_cache = PipelineStageCache()