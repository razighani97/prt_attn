from protest_attention.collect.wikipedia import summed
from protest_attention.http import _key


def test_summed_adds_redirects_by_day():
    record = {
        "series": {
            "Canonical": [{"date": "2021-01-01", "views": 10}, {"date": "2021-01-02", "views": 5}],
            "Old name": [{"date": "2021-01-01", "views": 3}],
        }
    }
    assert summed(record) == {"2021-01-01": 13, "2021-01-02": 5}


def test_cache_key_ignores_param_order():
    assert _key("u", {"a": 1, "b": 2}) == _key("u", {"b": 2, "a": 1})
    assert _key("u", {"a": 1}) != _key("u", {"a": 2})
