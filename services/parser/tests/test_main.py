import pytest
from minio.error import S3Error
from ..app.main import _read_object, _split


class DummyResponse:
    def __init__(self, payload=b"data", *, fail_on_read=False):
        self.payload = payload
        self.fail_on_read = fail_on_read
        self.closed = False
        self.released = False

    def read(self):
        if self.fail_on_read:
            raise S3Error(500, "InternalError", "boom", "resource", "request", "host")
        return self.payload

    def close(self):
        self.closed = True

    def release_conn(self):
        self.released = True


class DummyClient:
    def __init__(self, response=None, *, fail_on_get=False):
        self.response = response or DummyResponse()
        self.fail_on_get = fail_on_get

    def get_object(self, bucket, key):
        if self.fail_on_get:
            raise S3Error(404, "NoSuchKey", "missing", bucket, "request", "host")
        return self.response


def test_split_respects_overlap():
    chunks = _split("abcdefghij", size=4, overlap=1)
    assert chunks == ["abcd", "defg", "ghij", "j"]


def test_read_object_returns_payload_and_closes():
    response = DummyResponse(payload=b"payload")
    client = DummyClient(response=response)

    data = _read_object(client, "bucket", "key")

    assert data == b"payload"
    assert response.closed
    assert response.released


def test_read_object_translates_get_errors():
    client = DummyClient(fail_on_get=True)

    with pytest.raises(RuntimeError) as exc:
        _read_object(client, "bucket", "key")

    assert "Не удалось получить объект bucket/key" in str(exc.value)


def test_read_object_translates_read_errors_and_closes():
    response = DummyResponse(fail_on_read=True)
    client = DummyClient(response=response)

    with pytest.raises(RuntimeError) as exc:
        _read_object(client, "bucket", "key")

    assert "Не удалось дочитать объект bucket/key" in str(exc.value)
    assert response.closed
    assert response.released
