import pytest
from starter import validate_tree


def test_tree_contracts():
    assert validate_tree([("base", "arm"), ("arm", "tool")]) == "base"
    with pytest.raises(ValueError):
        validate_tree([("a", "b"), ("c", "b")])
    with pytest.raises(ValueError):
        validate_tree([("a", "b"), ("b", "a")])
    with pytest.raises(ValueError):
        validate_tree([("", "arm")])
    with pytest.raises(ValueError):
        validate_tree([("base",)])
