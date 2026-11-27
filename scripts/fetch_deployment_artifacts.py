"""Fetch the exact locally trained inference artifacts for a Render build.

The URLs must be direct HTTPS downloads, not HTML sharing pages. SHA-256 checks
are pinned in source because PyTorch checkpoints must only be loaded from a
trusted source. Change the hashes deliberately when publishing a new model.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (
    ("NEUMF_ARTIFACT_URL", "artifacts/checkpoints/neumf.pt", "b9fb96cbaeb1f46d1bf36f8d64e4ea783e10d29c019f031d06b3d9fe9194ee26"),
    ("MF_ARTIFACT_URL", "artifacts/checkpoints/matrix_factorization.pt", "38c0684f6f4622784b1eba1cf95fe36d4e096d720a04176fc27786b5b1925c4c"),
    ("RATING_ARTIFACT_URL", "artifacts/checkpoints/rating_predictor.pt", "a90061d384f9a9e7dc90ceb904cf65aaf5cc25cea853c62ef191ec12763ff0db"),
    ("SEEN_ARTIFACT_URL", "artifacts/mappings/seen_all.npz", "ce088be087830c0c9829a56a492318623d6f018516c5f79959714c8c567aff35"),
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    for env_name, relative_path, expected_hash in ARTIFACTS:
        target = ROOT / relative_path
        if target.is_file() and digest(target) == expected_hash:
            print(f"Verified {relative_path}", flush=True)
            continue
        url = os.environ.get(env_name, "")
        if urlparse(url).scheme != "https":
            raise SystemExit(f"{env_name} must be set to a direct HTTPS download URL")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".download")
        try:
            try:
                with urlopen(url, timeout=120) as response, temporary.open("wb") as output:
                    if urlparse(response.geturl()).scheme != "https":
                        raise ValueError("Artifact download redirected away from HTTPS")
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > 512 * 1024 * 1024:
                            raise ValueError("Artifact exceeds the 512 MiB download limit")
                        output.write(chunk)
            except (OSError, ValueError):
                # Do not print the URL, which might contain signed credentials.
                raise SystemExit(f"Failed to download {relative_path}; check {env_name}") from None
            if digest(temporary) != expected_hash:
                raise ValueError(f"SHA-256 mismatch for {relative_path}; check the file and URL")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"Downloaded and verified {relative_path}", flush=True)


if __name__ == "__main__":
    main()
