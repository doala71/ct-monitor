import json

import pytest

from ct_monitor.run import run
from ct_monitor.state import load_state, save_state


def test_load_state_missing_is_empty(tmp_path):
    assert load_state(tmp_path / "state.json") == {}


def test_save_then_load(tmp_path):
    p = tmp_path / "sub" / "state.json"
    save_state({"alpha": 42, "beta": 7}, p)
    assert load_state(p) == {"alpha": 42, "beta": 7}
    assert not list(p.parent.glob("*.tmp"))


@pytest.mark.parametrize(
    "text",
    ["", "not json", "[]", "{}", "null", '{"max_id": 5}', '{"max_ids": []}',
     '{"max_ids": {"a": "1"}}', '{"max_ids": {"a": true}}', '{"max_ids": {"a": -1}}'],
)
def test_load_state_raises_on_corrupted(tmp_path, text):
    p = tmp_path / "state.json"
    p.write_text(text)
    with pytest.raises(ValueError):
        load_state(p)


def _paths(tmp_path):
    return tmp_path / "state.json", tmp_path / "detected.json"


def test_first_run_saves_max_id_per_keyword_without_detection(tmp_path):
    state, out = _paths(tmp_path)
    fetched = {
        "alpha": {"x.alpha.test": 3, "y.alpha.test": 7},
        "beta": {"x.beta.test": 2},
    }
    assert run(fetched, [], state, out) is None
    assert load_state(state) == {"alpha": 7, "beta": 2}
    assert not out.exists()


def test_later_run_detects_only_ids_above_saved(tmp_path):
    state, out = _paths(tmp_path)
    save_state({"alpha": 5}, state)
    fetched = {"alpha": {"old.alpha.test": 5, "new.alpha.test": 6, "other.test": 9}}
    assert run(fetched, [], state, out) == ["new.alpha.test"]
    assert json.loads(out.read_text()) == ["new.alpha.test"]
    assert load_state(state) == {"alpha": 9}


def test_keyword_with_lower_max_id_does_not_miss_new_certs(tmp_path):
    # alpha の最大 id (50) が beta (100) より小さくても、alpha の 60 は検知される
    state, out = _paths(tmp_path)
    save_state({"alpha": 50, "beta": 100}, state)
    fetched = {
        "alpha": {"old.alpha.test": 50, "new.alpha.test": 60},
        "beta": {"old.beta.test": 100},
    }
    assert run(fetched, [], state, out) == ["new.alpha.test"]
    assert load_state(state) == {"alpha": 60, "beta": 100}


def test_new_keyword_is_first_run_only_for_itself(tmp_path):
    state, out = _paths(tmp_path)
    save_state({"alpha": 5}, state)
    fetched = {
        "alpha": {"new.alpha.test": 6},
        "gamma": {"old.gamma.test": 80, "older.gamma.test": 70},
    }
    assert run(fetched, [], state, out) == ["new.alpha.test"]
    assert load_state(state) == {"alpha": 6, "gamma": 80}


def test_allowlist_applies(tmp_path):
    state, out = _paths(tmp_path)
    save_state({"alpha": 1}, state)
    fetched = {"alpha": {"a.alpha.test": 2, "b.alpha.test": 3}}
    assert run(fetched, ["a.alpha.test"], state, out) == ["b.alpha.test"]


def test_state_does_not_decrease(tmp_path):
    state, out = _paths(tmp_path)
    save_state({"alpha": 10}, state)
    assert run({"alpha": {"a.alpha.test": 3}}, [], state, out) == []
    assert load_state(state) == {"alpha": 10}


def test_empty_fetch_saves_zero_for_first_run_keyword_and_keeps_known(tmp_path):
    state, out = _paths(tmp_path)
    save_state({"alpha": 10}, state)
    assert run({"alpha": {}, "gamma": {}}, [], state, out) == []
    assert load_state(state) == {"alpha": 10, "gamma": 0}


def test_all_keywords_empty_on_first_run_saves_zero(tmp_path):
    state, out = _paths(tmp_path)
    assert run({"alpha": {}}, [], state, out) is None
    assert load_state(state) == {"alpha": 0}
    assert not out.exists()


def test_cert_first_seen_after_empty_first_run_is_detected(tmp_path):
    state, out = _paths(tmp_path)
    assert run({"alpha": {}}, [], state, out) is None
    assert load_state(state) == {"alpha": 0}
    # 次回、初めて証明書が現れた。id が小さくても新規として検知される
    assert run({"alpha": {"first.alpha.test": 1}}, [], state, out) == ["first.alpha.test"]
    assert load_state(state) == {"alpha": 1}


def test_corrupted_state_raises_and_writes_nothing(tmp_path):
    state, out = _paths(tmp_path)
    state.write_text("garbage")
    with pytest.raises(ValueError):
        run({"alpha": {"a.alpha.test": 3}}, [], state, out)
    assert state.read_text() == "garbage"
    assert not out.exists()
