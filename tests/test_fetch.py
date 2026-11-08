import io
import json
import socket
import urllib.error
from pathlib import Path

import pytest

from ct_monitor import fetch
from ct_monitor.fetch import fetch_crtsh, parse_crtsh, summarize_crtsh

FIXTURE = Path(__file__).parent / "fixtures" / "crtsh_sample.json"


def test_parse_crtsh_splits_normalizes_and_drops_invalid():
    assert parse_crtsh(FIXTURE.read_text()) == {
        "login.examplebrand-secure.test": 1,
        "www.examplebrand-secure.test": 1,
        "examplebrand.test": 4,
        "shop.examplebrand.test": 3,
        "unrelated.test": 8,
    }


def test_parse_crtsh_drops_rows_with_non_integer_id():
    text = json.dumps([
        {"id": "9", "name_value": "a.test"},
        {"id": 1.5, "name_value": "b.test"},
        {"id": True, "name_value": "c.test"},
        {"id": None, "name_value": "d.test"},
        {"name_value": "e.test"},
        {"id": 10, "name_value": "f.test"},
    ])
    assert parse_crtsh(text) == {"f.test": 10}


def test_parse_crtsh_keeps_max_id_per_domain():
    text = json.dumps([
        {"id": 5, "name_value": "a.test"},
        {"id": 9, "name_value": "a.test"},
        {"id": 7, "name_value": "a.test"},
    ])
    assert parse_crtsh(text) == {"a.test": 9}


def test_parse_crtsh_empty_list_is_empty_set():
    assert parse_crtsh("[]") == {}


@pytest.mark.parametrize("text", ["", "not json", "<html>", '{"a": 1}', '"str"', "null"])
def test_parse_crtsh_raises_on_bad_response(text):
    with pytest.raises(ValueError):
        parse_crtsh(text)


def test_summarize_crtsh_counts_all_rows_and_max_valid_id():
    text = json.dumps([{"id": 3}, {"id": "99"}, {"id": 7}, "x"])
    assert summarize_crtsh(text) == (4, 7)
    assert summarize_crtsh("[]") == (0, None)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http_error(code):
    return urllib.error.HTTPError("http://x.test", code, "err", {}, None)


def _patch(monkeypatch, outcomes):
    """urlopen を差し替え、outcomes を順に返す/送出する。呼び出し回数を返す。"""
    calls = []

    def fake(url, timeout):
        calls.append(url)
        out = outcomes[len(calls) - 1]
        if isinstance(out, Exception):
            raise out
        return _Resp(out.encode())

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake)
    return calls


OK = json.dumps([{"id": 5, "name_value": "a.test"}, {"id": 2, "name_value": "b.test"}])


def test_fetch_success_reports_rows_and_max_id(monkeypatch):
    _patch(monkeypatch, [OK])
    sleeps = []
    r = fetch_crtsh("kw", sleep=sleeps.append)
    assert (r.domains, r.rows, r.max_id, r.retries) == ({"a.test": 5, "b.test": 2}, 2, 5, 0)
    assert sleeps == []


@pytest.mark.parametrize(
    "failure",
    [_http_error(502), _http_error(503), _http_error(504), socket.timeout(),
     TimeoutError(), urllib.error.URLError(socket.timeout())],
)
def test_fetch_retries_transient_errors_with_backoff(monkeypatch, failure):
    calls = _patch(monkeypatch, [failure, failure, OK])
    sleeps = []
    r = fetch_crtsh("kw", sleep=sleeps.append)
    assert r.retries == 2
    assert sleeps == [15, 30]
    assert len(calls) == 3


def test_fetch_gives_up_after_three_retries(monkeypatch):
    calls = _patch(monkeypatch, [_http_error(503)] * 4)
    sleeps = []
    with pytest.raises(urllib.error.HTTPError):
        fetch_crtsh("kw", sleep=sleeps.append)
    assert sleeps == [15, 30, 60]
    assert len(calls) == 4


@pytest.mark.parametrize("code", [400, 403, 404, 429, 500])
def test_fetch_does_not_retry_other_http_errors(monkeypatch, code):
    calls = _patch(monkeypatch, [_http_error(code), OK])
    sleeps = []
    with pytest.raises(urllib.error.HTTPError):
        fetch_crtsh("kw", sleep=sleeps.append)
    assert sleeps == [] and len(calls) == 1


def test_fetch_does_not_retry_non_timeout_url_error(monkeypatch):
    calls = _patch(monkeypatch, [urllib.error.URLError(ConnectionRefusedError()), OK])
    with pytest.raises(urllib.error.URLError):
        fetch_crtsh("kw", sleep=lambda s: None)
    assert len(calls) == 1
