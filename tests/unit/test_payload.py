import pytest

from framework.payload import apply_overrides, coerce, parse_key

BASE = {"user_id": 1, "delivery": {"address": "12 Anna Salai", "pincode": "600002"}, "items": [{"sku": "A"}]}


@pytest.mark.unit
@pytest.mark.parametrize(
    "key, expected",
    [
        ("quantity", ["quantity"]),
        ("delivery[pincode]", ["delivery", "pincode"]),
        ("items[0][sku]", ["items", 0, "sku"]),
    ],
)
def test_parse_key(key, expected):
    assert parse_key(key) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    "cell, expected",
    [
        ("5", 5),
        ("2.5", 2.5),
        ("true", True),
        ("[1, 2]", [1, 2]),
        ('"5"', "5"),
        ("two", "two"),
        ("__null__", None),
        ("__empty__", ""),
        (7, 7),
    ],
)
def test_coerce(cell, expected):
    assert coerce(cell) == expected


@pytest.mark.unit
def test_overrides_do_not_mutate_the_default():
    apply_overrides(BASE, {"user_id": "9", "delivery[pincode]": "600001"})
    assert BASE["user_id"] == 1 and BASE["delivery"]["pincode"] == "600002"


@pytest.mark.unit
def test_nested_and_list_overrides():
    out = apply_overrides(BASE, {"delivery[pincode]": "600001", "items[0][sku]": "B", "items[1][sku]": "C"})
    assert out["delivery"]["pincode"] == 600001  # numeric text becomes a number unless quoted
    assert out["items"] == [{"sku": "B"}, {"sku": "C"}]


@pytest.mark.unit
def test_remove_and_create_missing_path():
    out = apply_overrides(BASE, {"delivery[address]": "__remove__", "meta[source]": "excel"})
    assert "address" not in out["delivery"]
    assert out["meta"] == {"source": "excel"}


@pytest.mark.unit
def test_list_index_on_dict_is_rejected():
    with pytest.raises(TypeError):
        apply_overrides(BASE, {"delivery[0]": "x"})
