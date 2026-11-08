from pathlib import Path

import pytest

from ct_monitor.fetch import parse_crtsh

FIXTURE = Path(__file__).parent / "fixtures" / "crtsh_sample.json"


def test_parse_crtsh_splits_normalizes_and_drops_invalid():
    assert parse_crtsh(FIXTURE.read_text()) == {
        "login.examplebrand-secure.test",
        "www.examplebrand-secure.test",
        "examplebrand.test",
        "shop.examplebrand.test",
        "unrelated.test",
    }


def test_parse_crtsh_empty_list_is_empty_set():
    assert parse_crtsh("[]") == set()


@pytest.mark.parametrize("text", ["", "not json", "<html>", '{"a": 1}', '"str"', "null"])
def test_parse_crtsh_raises_on_bad_response(text):
    with pytest.raises(ValueError):
        parse_crtsh(text)
