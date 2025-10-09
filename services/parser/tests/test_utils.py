from pathlib import Path
import sys

import pytest
from minio.error import S3Error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import _read_object, _split  # noqa: E402


class DummyResponse:
    def __init__(self, payload: bytes):
        self._payload = payload
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


def test_split_with_overlap():
    text = "abcdef"
    parts = _split(text, size=3, overlap=1)
    assert parts == ["abc", "cde", "ef"]


def test_read_object_success(monkeypatch):
    captured = {}

    def fake_get_object(bucket: str, object_name: str):
        captured["args"] = (bucket, object_name)
        return DummyResponse(b"payload")

    monkeypatch.setattr("app.main.minio.get_object", fake_get_object)
    data = _read_object("object.txt")
    assert data == b"payload"
    assert captured["args"][1] == "object.txt"


def test_read_object_error(monkeypatch):
    err = S3Error("code", "message", "resource", "request_id", "host_id", 500)

    def fake_get_object(bucket: str, object_name: str):  # pragma: no cover - network
        raise err

    monkeypatch.setattr("app.main.minio.get_object", fake_get_object)
    with pytest.raises(RuntimeError) as exc:
        _read_object("missing.txt")
    assert "missing.txt" in str(exc.value)
