import pytest
from manim import Group, Mobject, VDict, VGroup, VMobject

from manim_mjutils import GroupDict, V


# ----------------------------------------------------------------------
# V
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "mob",
    [GroupDict(), VDict(), Group(), VGroup(), Mobject(), VMobject(), 3, "string"],
)
def test_V_returns_mob_unchanged_if_raise_False(mob):
    result = V(mob, raise_=False)
    assert result is mob


@pytest.mark.parametrize(
    "mob",
    [GroupDict(), Group(), Mobject(), 3, "string"],
)
def test_V_raises_on_non_vectorized_with_raise_True(mob):
    """V() should raise when non-vectorized input with raise_=True."""
    with pytest.raises(AssertionError, match="is not a vectorized object"):
        V(mob, raise_=True)


@pytest.mark.parametrize(
    "mob",
    [VDict(), VGroup(), VMobject()],
)
def test_V_does_not_raise_on_vectorized_with_raise_True(mob):
    """V() should NOT raise when input is already vectorized."""
    result = V(mob, raise_=True)
    assert result is mob


def test_V_handles_nested_groups():
    """V() should work on VGroup containing other VGroups."""
    inner = VGroup()
    outer = VGroup(inner)
    result = V(outer, raise_=False)
    assert isinstance(result, VGroup)
    assert result == outer
