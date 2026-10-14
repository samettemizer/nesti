#!/usr/bin/env python3
"""Prepare a pinned, non-secret CPU model artifact during a controlled build."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reranker import MODEL_REVISIONS, validate_artifact, validate_profile

logger = logging.getLogger(__name__)
_LICENSE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"
_DEFAULT_MODEL = "cross-encoder/ettin-reranker-150m-v1"


def prepare(output: Path, model_id: str, profile_path: Path | None = None) -> dict:
    """Download only fixed-revision model files; never overwrite an existing artifact."""
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists; use a new artifact directory")
    profile = None
    if profile_path is not None:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if not isinstance(profile, dict):
            raise ValueError("profile must be a JSON object")
        model_id = profile.get("model_id")
    if not isinstance(model_id, str) or model_id not in MODEL_REVISIONS:
        raise ValueError("model_id must be one of the pinned experiment models")
    revision = MODEL_REVISIONS[model_id]
    if profile is not None and profile.get("revision") != revision:
        raise ValueError("profile revision differs from the pinned artifact")
    from huggingface_hub import HfApi, snapshot_download

    info = HfApi().model_info(model_id, revision=revision)
    if info.sha != revision or not info.card_data or info.card_data.get("license") != "apache-2.0":
        raise ValueError("upstream revision/license does not match the pinned artifact source")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".nesti-reranker-", dir=output.parent) as name:
        directory = Path(name) / "artifact"
        snapshot_download(
            repo_id=model_id, revision=revision, local_dir=directory,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "README.md", "LICENSE*"],
            ignore_patterns=["onnx/*", "openvino/*", "trainer_state.json", "training_args.*"],
            max_workers=2,
        )
        shutil.rmtree(directory / ".cache", ignore_errors=True)
        if any(path.is_symlink() for path in directory.rglob("*")):
            raise ValueError("prepared artifact must contain regular local files, not symlinks")
        if (directory / "reranker-profile.json").exists():
            raise ValueError("deployment profile must come from the operator, not the model repository")
        with urlopen(_LICENSE_URL, timeout=30) as response:
            license_text = response.read().decode("utf-8")
        if "Apache License" not in license_text or "Version 2.0" not in license_text:
            raise ValueError("Apache license source returned unexpected content")
        (directory / "LICENSE").write_text(license_text, encoding="utf-8")
        checksums = {}
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                with path.open("rb") as handle:
                    checksums[str(path.relative_to(directory))] = hashlib.file_digest(handle, "sha256").hexdigest()
        manifest = {
            "model_id": model_id, "revision": revision, "license": "apache-2.0",
            "license_url": _LICENSE_URL, "prepared_at": datetime.now(timezone.utc).isoformat(),
            "files_sha256": checksums,
        }
        (directory / "reranker-artifact.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        validate_artifact(directory, model_id, revision)
        if profile is not None:
            (directory / "reranker-profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
            validate_profile(directory / "reranker-profile.json")
        os.rename(directory, output)
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Prepare one artifact and print its immutable identity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-id", choices=tuple(MODEL_REVISIONS), default=_DEFAULT_MODEL)
    parser.add_argument("--profile", default="", help="operator-approved profile; its pinned model identity takes precedence")
    args = parser.parse_args(argv)
    try:
        manifest = prepare(args.output, args.model_id, Path(args.profile) if args.profile else None)
    except Exception as exc:
        logger.error("Model preparation failed (%s): %s", type(exc).__name__, exc)
        return 1
    print(f"Prepared {manifest['model_id']}@{manifest['revision']} in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
