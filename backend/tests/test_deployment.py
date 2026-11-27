"""Deployment-specific configuration and model download checks."""
import hashlib
import io

import pytest

from app.core.config import Settings
from scripts import fetch_deployment_artifacts as fetch


@pytest.mark.parametrize("url", ["postgres://u:p@host/db", "postgresql://u:p@host/db"])
def test_render_database_urls_use_psycopg3(url):
    assert Settings(database_url=url).database_url == "postgresql+psycopg://u:p@host/db"


def test_artifact_download_is_verified_before_installing(tmp_path, monkeypatch):
    payload = b"trusted artifact"
    target = tmp_path / "artifacts/model.pt"
    expected = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(fetch, "ROOT", tmp_path)
    monkeypatch.setattr(fetch, "ARTIFACTS", (("TEST_ARTIFACT_URL", "artifacts/model.pt", expected),))
    monkeypatch.setenv("TEST_ARTIFACT_URL", "https://example.org/model.pt")

    class Response(io.BytesIO):
        def geturl(self):
            return "https://example.org/model.pt"

    monkeypatch.setattr(fetch, "urlopen", lambda *args, **kwargs: Response(payload))
    fetch.main()
    assert target.read_bytes() == payload

    target.unlink()
    monkeypatch.setattr(fetch, "urlopen", lambda *args, **kwargs: Response(b"wrong"))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        fetch.main()
    assert not target.exists()
