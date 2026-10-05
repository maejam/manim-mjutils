from unittest.mock import MagicMock

import manim as m
import numpy as np
import pytest

from manim_mjutils import CallbackAnimation, LazyAnimation, TrackedAnimationMixin


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
def circle_factory():
    return m.Circle()


def applymeth_factory(mob):
    return m.ApplyMethod(mob.shift, m.RIGHT)


@pytest.fixture
def tracked_transform():
    class TrackedTransform(TrackedAnimationMixin, m.Transform): ...

    return TrackedTransform(m.Circle(), m.Rectangle())


@pytest.fixture
def tracked_apply_meth():
    class TrackedAppplyMeth(TrackedAnimationMixin, m.ApplyMethod): ...

    return TrackedAppplyMeth(m.Circle().shift, m.RIGHT)


@pytest.fixture
def mock_callback():
    """Creates a mock function to act as the callback."""
    return MagicMock(name="user_callback")


@pytest.fixture
def callback_animation(mock_callback):
    """
    Creates a CallbackAnimation instance with a mock callback.
    Uses a short run_time for faster testing.
    """
    return CallbackAnimation(mock_callback, "arg1", 42, delay=0.5, run_time=1.0)


@pytest.fixture
def immediate_callback_animation(mock_callback):
    """
    Creates a CallbackAnimation that triggers immediately (at alpha=0).
    """
    return CallbackAnimation(mock_callback, run_time=1.0, delay=0.0)


# ----------------------------------------------------------------------
# LazyAnimation
# ----------------------------------------------------------------------
def test_lazy_animation_instantiation():
    anim = LazyAnimation(
        mobject_factory=circle_factory,
        animation_factory=applymeth_factory,
    )

    assert anim is not None
    assert anim._mobject_factory is circle_factory
    assert anim._animation_factory is applymeth_factory


def test_mobject_assigned_after_begin():
    anim = LazyAnimation(
        mobject_factory=circle_factory,
        animation_factory=applymeth_factory,
    )

    assert isinstance(anim.mobject, m.Mobject)
    assert not isinstance(anim.mobject, m.Circle)
    anim.begin()
    assert isinstance(anim.mobject, m.Circle)


def test_delegation_to_inner_animation():
    anim = LazyAnimation(
        mobject_factory=circle_factory,
        animation_factory=applymeth_factory,
    )

    anim.begin()

    # These should not raise AttributeError
    anim.interpolate(0.5)
    anim.update_mobjects(0.016)
    families = anim.get_all_families_zipped()
    assert isinstance(families, zip)


def test_finish_delegates_to_inner_animation():
    anim = LazyAnimation(
        mobject_factory=circle_factory,
        animation_factory=applymeth_factory,
    )

    anim.begin()
    # Should not raise
    anim.finish()


def test_dynamic_mobject_changes_are_captured():
    """Test that mobject changes before play are captured."""
    c = m.Circle(color=m.RED)
    d = m.Dot(color=m.GREEN)
    grp = m.VGroup(c, d)

    def mob_factory():
        return m.VGroup([mob for mob in grp if mob.color == m.RED])

    anim = LazyAnimation(
        mobject_factory=mob_factory,
        animation_factory=applymeth_factory,
    )

    grp[1].set_color(m.RED)

    s = m.Scene()
    pos_c = c.get_center()
    pos_d = d.get_center()
    s.play(anim)

    assert len(anim.mobject) == 2
    assert not np.allclose(pos_c, c.get_center())
    assert not np.allclose(pos_d, d.get_center())


# ----------------------------------------------------------------------
# TrackedAnimationMixin
# ----------------------------------------------------------------------
def test_tracked_mixin_initialstatus(tracked_transform, tracked_apply_meth):
    assert tracked_transform.status == "not played"
    assert tracked_apply_meth.status == "not played"


def test_tracked_mixinstatus_after_begin(tracked_transform, tracked_apply_meth):
    tracked_transform.begin()
    assert tracked_transform.status == "playing"
    tracked_apply_meth.begin()
    assert tracked_apply_meth.status == "playing"


def test_tracked_mixinstatus_after_finish(tracked_transform, tracked_apply_meth):
    tracked_transform.begin()
    tracked_transform.finish()
    assert tracked_transform.status == "played"
    tracked_apply_meth.begin()
    tracked_apply_meth.finish()
    assert tracked_apply_meth.status == "played"


def test_tracked_mixin_multiple_begin_finish_cycles(
    tracked_transform, tracked_apply_meth
):
    # First cycle
    assert tracked_transform.status == "not played"
    tracked_transform.begin()
    assert tracked_transform.status == "playing"
    tracked_transform.finish()
    assert tracked_transform.status == "played"

    # Second cycle
    tracked_transform.begin()
    assert tracked_transform.status == "playing"
    tracked_transform.finish()
    assert tracked_transform.status == "played"

    # First cycle
    assert tracked_apply_meth.status == "not played"
    tracked_apply_meth.begin()
    assert tracked_apply_meth.status == "playing"
    tracked_apply_meth.finish()
    assert tracked_apply_meth.status == "played"

    # Second cycle
    tracked_apply_meth.begin()
    assert tracked_apply_meth.status == "playing"
    tracked_apply_meth.finish()
    assert tracked_apply_meth.status == "played"


def test_tracked_mixin_tracker(tracked_transform, tracked_apply_meth):
    t1 = m.ValueTracker()
    t2 = m.ValueTracker()
    tracked_transform.alpha_tracker = t1
    tracked_apply_meth.alpha_tracker = t2

    # First cycle
    assert t1.get_value() == 0.0
    tracked_transform.begin()
    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
        tracked_transform.interpolate(alpha)
        assert t1.get_value() == alpha
    assert t1.get_value() == 1.0

    # Second cycle
    tracked_transform.begin()
    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
        tracked_transform.interpolate(alpha)
        assert t1.get_value() == alpha
    assert t1.get_value() == 1.0

    # First cycle
    assert t2.get_value() == 0.0
    tracked_apply_meth.begin()
    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
        tracked_apply_meth.interpolate(alpha)
        assert t2.get_value() == alpha
    assert t2.get_value() == 1.0

    # Second cycle
    tracked_apply_meth.begin()
    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
        tracked_apply_meth.interpolate(alpha)
        assert t2.get_value() == alpha
    assert t2.get_value() == 1.0


# ----------------------------------------------------------------------
# CallbackAnimation
# ----------------------------------------------------------------------
def test_callback_not_called_before_delay(callback_animation, mock_callback):
    """Test that the callback is NOT called if alpha is below the delay threshold."""
    # Simulate animation progress at alpha = 0.4 (below 0.5 delay)
    callback_animation.interpolate(0.4)
    mock_callback.assert_not_called()


def test_callback_called_at_delay(callback_animation, mock_callback):
    """Test that the callback IS called when alpha reaches the delay threshold."""
    # Simulate animation progress at alpha = 0.5 (exactly at delay)
    callback_animation.interpolate(0.5)
    mock_callback.assert_called_once()


def test_callback_called_after_delay(callback_animation, mock_callback):
    """Test that the callback is called if alpha exceeds the delay threshold."""
    # Simulate animation progress at alpha = 0.9 (above 0.5 delay)
    callback_animation.interpolate(0.9)
    mock_callback.assert_called_once()


def test_callback_arguments_passed_correctly(callback_animation, mock_callback):
    """Test that arguments passed to the animation are forwarded to the callback."""
    callback_animation.interpolate(0.5)

    # Verify the callback received the specific arguments passed in __init__
    mock_callback.assert_called_once_with("arg1", 42)


def test_callback_called_only_once(callback_animation, mock_callback):
    """Test that the callback is not called multiple times as alpha increases."""
    # delay at 0.5
    callback_animation.interpolate(0.5)
    callback_animation.interpolate(0.6)
    callback_animation.interpolate(0.9)
    callback_animation.interpolate(1.0)

    # Should still be called exactly once
    mock_callback.assert_called_once()


def test_immediate_delay(immediate_callback_animation, mock_callback):
    """Test that a delay=0.0 calls the callback immediately on first call."""
    # Even at alpha=0.0, it should delay
    immediate_callback_animation.interpolate(0.0)

    mock_callback.assert_called_once()


def test_callback_with_no_args(mock_callback):
    """Test creating and running an animation with no extra arguments."""
    anim = CallbackAnimation(mock_callback, run_time=1.0, delay=0.5)
    anim.interpolate(0.5)

    mock_callback.assert_called_once_with()


def test_begin_resets_state(callback_animation, mock_callback):
    """Test that calling begin() resets the _called flag, allowing re-use."""
    # First run
    callback_animation.interpolate(0.5)
    assert mock_callback.call_count == 1

    # Reset the animation state (simulating a restart)
    callback_animation.begin()

    # Second run
    callback_animation.interpolate(0.5)

    # Should be called again
    assert mock_callback.call_count == 2


def test_inherits_from_animation(callback_animation):
    """Verify that CallbackAnimation is a proper subclass of Animation."""
    from manim import Animation

    assert isinstance(callback_animation, Animation)
