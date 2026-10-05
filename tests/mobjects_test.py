import manim as m
import pytest

from manim_mjutils.mobjects import GroupDict


# ----------------------------------------------------------------------
# GroupDict
# ----------------------------------------------------------------------
def test_groupdict_creation_empty():
    """Test creating an empty GroupDict."""
    gd = GroupDict()
    assert len(gd) == 0
    assert list(gd.keys()) == []
    assert list(gd.values()) == []
    assert list(gd.items()) == []


def test_groupdict_creation_with_mapping():
    """Test creating GroupDict with a mapping."""
    mob1 = m.Circle()
    mob2 = m.Square()
    data = {"circle": mob1, "square": mob2}

    gd = GroupDict(data)

    assert len(gd) == 2
    assert gd["circle"] is mob1
    assert gd["square"] is mob2
    assert set(gd.keys()) == {"circle", "square"}


def test_groupdict_creation_with_iterable():
    """Test creating GroupDict with an iterable of tuples."""
    mob1 = m.Triangle()
    mob2 = m.Rectangle()
    data = [("triangle", mob1), ("rectangle", mob2)]

    gd = GroupDict(data)

    assert len(gd) == 2
    assert gd["triangle"] is mob1
    assert gd["rectangle"] is mob2


def test_groupdict_add_single_item():
    """Test adding a single item via __setitem__."""
    gd = GroupDict()
    mob = m.Circle()

    gd["circle"] = mob

    assert len(gd) == 1
    assert gd["circle"] is mob
    assert mob in gd.submobjects


def test_groupdict_add_multiple_items():
    """Test adding multiple items via add method."""
    gd = GroupDict()
    mob1 = m.Square()
    mob2 = m.Triangle()

    gd.add({"square": mob1, "triangle": mob2})

    assert len(gd) == 2
    assert gd["square"] is mob1
    assert gd["triangle"] is mob2


def test_groupdict_add_to_existing():
    """Test adding items to an existing GroupDict."""
    mob1 = m.Circle()
    gd = GroupDict({"circle": mob1})

    mob2 = m.Square()
    gd.add({"square": mob2})

    assert len(gd) == 2
    assert gd["circle"] is mob1
    assert gd["square"] is mob2


def test_groupdict_remove_item():
    """Test removing an item."""
    mob = m.Circle()
    gd = GroupDict({"circle": mob})

    result = gd.remove("circle")

    assert len(gd) == 0
    assert "circle" not in gd
    assert mob not in gd.submobjects
    assert result is gd  # Should return self for chaining


def test_groupdict_del_item():
    """Test deleting an item using del."""
    mob = m.Square()
    gd = GroupDict({"square": mob})

    del gd["square"]

    assert len(gd) == 0
    assert "square" not in gd
    assert mob not in gd.submobjects


def test_groupdict_update_existing_key():
    """Test updating an existing key replaces the mobject."""
    old_mob = m.Circle()
    new_mob = m.Square()
    gd = GroupDict({"shape": old_mob})

    gd["shape"] = new_mob

    assert len(gd) == 1
    assert gd["shape"] is new_mob
    assert old_mob not in gd.submobjects
    assert new_mob in gd.submobjects


def test_groupdict_getitem_missing_key():
    """Test getting a missing key raises KeyError."""
    gd = GroupDict()

    with pytest.raises(KeyError, match="not found in GroupDict"):
        _ = gd["nonexistent"]


def test_groupdict_delitem_missing_key():
    """Test deleting a missing key raises KeyError."""
    gd = GroupDict()

    with pytest.raises(KeyError, match="not found in GroupDict"):
        del gd["nonexistent"]


def test_groupdict_remove_missing_key():
    """Test removing a missing key raises KeyError."""
    gd = GroupDict()

    with pytest.raises(KeyError, match="not found in GroupDict"):
        gd.remove("nonexistent")


def test_groupdict_repr():
    """Test string representation."""
    mob = m.Circle()
    gd = GroupDict({"circle": mob})

    assert repr(gd) == "GroupDict({'circle': Circle})"


def test_groupdict_keys_view():
    """Test that keys() returns a view."""
    mob = m.Circle()
    gd = GroupDict({"circle": mob})

    keys = gd.keys()
    assert hasattr(keys, "__iter__")
    assert "circle" in keys


def test_groupdict_values_view():
    """Test that values() returns a view."""
    mob = m.Circle()
    gd = GroupDict({"circle": mob})

    values = gd.values()
    assert hasattr(values, "__iter__")
    assert mob in values


def test_groupdict_items_view():
    """Test that items() returns a view."""
    mob = m.Circle()
    gd = GroupDict({"circle": mob})

    items = gd.items()
    assert hasattr(items, "__iter__")
    assert ("circle", mob) in items


def test_groupdict_add_invalid_type():
    """Test that adding invalid types raises TypeError."""
    gd = GroupDict()

    with pytest.raises(TypeError, match="Only mappings or iterables"):
        gd.add("invalid")

    with pytest.raises(TypeError, match="Only mappings or iterables"):
        gd.add(123)


def test_groupdict_manim_integration():
    """Test that GroupDict integrates properly with Manim's Group."""
    mob1 = m.Circle()
    mob2 = m.Square()
    gd = GroupDict({"circle": mob1, "square": mob2})

    # Should be able to iterate like a Group
    count = sum(1 for _ in gd)
    assert count == 2

    # Should have all Group methods available
    assert hasattr(gd, "shift")
    assert hasattr(gd, "scale")
    assert hasattr(gd, "rotate")
