from pathlib import Path

from ct_monitor.detect import detect
from ct_monitor.fetch import parse_crtsh

FIXTURE = Path(__file__).parent / "fixtures" / "crtsh_sample.json"


def test_detect_excludes_allowlist_and_subdomains():
    domains = parse_crtsh(FIXTURE.read_text())
    assert detect(domains, ["examplebrand"], ["examplebrand.test"]) == {
        "login.examplebrand-secure.test",
        "www.examplebrand-secure.test",
    }


def test_allowlist_does_not_match_suffix_lookalike():
    assert detect({"evilexamplebrand.test"}, ["examplebrand"], ["examplebrand.test"]) == {
        "evilexamplebrand.test"
    }


def test_detect_is_case_insensitive_for_keywords():
    assert detect({"examplebrand.test"}, ["ExampleBrand"], []) == {"examplebrand.test"}


def test_detect_no_keyword_match():
    assert detect({"unrelated.test"}, ["examplebrand"], []) == set()
