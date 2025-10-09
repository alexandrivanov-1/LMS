from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from minio.error import S3Error

from services.parser.app import _read_object, _split


class DummyS3Error(S3Error):
    """Упрощённое исключение для удобного создания в тестах."""

    def __init__(self, message: str):
        super().__init__(
            code="500",
            message=message,
            resource="/bucket/object",
            request_id="req",
            host_id="host",
            response=SimpleNamespace(),
        )


def test_split_returns_chunks_with_overlap():
    text = "abcdefghij"
    chunks = _split(text, size=4, overlap=2)
    assert chunks == ["abcd", "cdef", "efgh", "ghij", "ij"]


def test_split_handles_empty_text():
    assert _split("", size=3, overlap=1) == []


def test_read_object_returns_bytes_and_closes_response():
    response = MagicMock()
    response.read.return_value = b"payload"

    client = MagicMock()
    client.get_object.return_value = response

    data = _read_object(client, "bucket", "object")

    assert data == b"payload"
    client.get_object.assert_called_once_with("bucket", "object")
    response.read.assert_called_once()
    response.close.assert_called_once()
    response.release_conn.assert_called_once()


def test_read_object_wraps_get_errors():
    client = MagicMock()
    client.get_object.side_effect = DummyS3Error("boom")

    with pytest.raises(RuntimeError) as exc:
        _read_object(client, "bucket", "object")

    assert "Не удалось получить объект" in str(exc.value)


def test_read_object_wraps_read_errors():
    response = MagicMock()
    response.read.side_effect = DummyS3Error("broken")

    client = MagicMock()
    client.get_object.return_value = response

    with pytest.raises(RuntimeError) as exc:
        _read_object(client, "bucket", "object")

    assert "Ошибка чтения объекта" in str(exc.value)
    response.close.assert_called_once()
    response.release_conn.assert_called_once()
