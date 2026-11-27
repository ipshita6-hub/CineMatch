"""Write memory-mappable sidecars for the seen index.

The inference process loads ``artifacts/mappings/seen_all.npz``. Its ``indices``
array is ~76 MB of int32 — the single largest allocation the API makes. Read out
of the .npz it becomes anonymous memory, which counts fully against a container's
memory limit and cannot be reclaimed by the kernel. On a 512 MB instance that is
the difference between running and being OOM-killed.

This writes ``seen_all_indices.npy`` and ``seen_all_indptr.npy`` beside the .npz
so ``SeenIndex.load`` can mmap the large one: file-backed, read-only pages the OS
can evict under pressure.

Run once per deploy, after the artifacts are fetched. Idempotent — it skips files
that already match the source.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts" / "mappings" / "seen_all.npz"


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"missing {SOURCE.relative_to(ROOT)}; fetch the artifacts first")

    targets = {
        "indices": SOURCE.with_name(SOURCE.stem + "_indices.npy"),
        "indptr": SOURCE.with_name(SOURCE.stem + "_indptr.npy"),
    }

    with np.load(SOURCE) as z:
        for key, target in targets.items():
            source_array = z[key]
            if target.is_file():
                existing = np.load(target, mmap_mode="r")
                if existing.shape == source_array.shape and existing.dtype == source_array.dtype:
                    print(f"Verified {target.name}", flush=True)
                    continue
                print(f"Rewriting {target.name} (shape or dtype changed)", flush=True)
            # Write via a temporary file so an interrupted run cannot leave a
            # truncated .npy that would later be mmapped as if it were complete.
            # Must still end in .npy: np.save appends the suffix otherwise.
            temporary = target.with_name(target.stem + ".tmp.npy")
            try:
                np.save(temporary, source_array)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            size_mb = target.stat().st_size / 1048576
            print(f"Wrote {target.name} ({size_mb:.1f} MB, {source_array.dtype})", flush=True)


if __name__ == "__main__":
    sys.exit(main())
