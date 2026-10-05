import manim as m
import numpy as np
import pytest

from manim_mjutils.ui.buttons import (
    Button,
    ButtonDict,
    ButtonGroup,
    HighlightButton,
    PushButton,
)


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
class TstButton(Button):
    """A minimal concrete button for testing the base Button class."""

    STATE_A = {"color": m.RED}
    STATE_B = {"color": m.BLUE}

    def _build_state(self, state_name: str) -> tuple[m.VGroup, m.VDict]:
        color = self.states[state_name]["color"]
        body = self._get_template().set_fill(color=color)
        contents = self._get_contents_template().set_fill(color=color)
        return m.VGroup(body), contents


@pytest.fixture
def btn():
    shape = m.Circle()
    return TstButton(shape=shape)


@pytest.fixture
def btn_with_cb():
    """Create a button with a custom callback."""
    shape = m.Circle()
    calls = []

    def callback(button, from_state, to_state):
        calls.append((button, from_state, to_state))

    btn = TstButton(shape=shape, callback=callback)
    btn._calls = calls  # type: ignore[reportAttributeAccessIssue]
    return btn


@pytest.fixture
def btns():
    """Create multiple test buttons."""
    return [TstButton(shape=m.Circle()) for _ in range(3)]


@pytest.fixture
def btn_group(btns):
    """Create a ButtonGroup with test buttons."""
    return ButtonGroup(*btns)


@pytest.fixture
def btn_dict(btns):
    """Create a ButtonDict with test buttons."""
    return ButtonDict(dict(zip(["b1", "b2", "b3"], btns, strict=True)))


@pytest.fixture
def btn_dict_with_cb(btns):
    """Create a ButtonDict with test buttons and a callback."""
    calls = []
    bd = ButtonDict(
        dict(zip(["b1", "b2", "b3"], btns, strict=True)),
        callback=lambda g, b, f, t: calls.append((g, b, f, t)),
    )
    bd._calls = calls  # type: ignore[reportAttributeAccessIssue]
    return bd


# ----------------------------------------------------------------------
# Button
# ----------------------------------------------------------------------
def test_button_initialization(btn):
    """Test that a button initializes with the first state."""
    assert btn.state == "STATE_A"
    assert len(btn._state_keys) == 2
    assert btn._state_keys == ["STATE_A", "STATE_B"]
    assert btn._state_index == 0
    assert btn.states == {
        "STATE_A": {"color": m.RED},
        "STATE_B": {"color": m.BLUE},
    }


def test_button_transition_next_state(btn):
    """Test transitioning to the next state automatically."""
    assert btn.state == "STATE_A"
    assert btn._state_index == 0
    btn.transition()
    assert btn.state == "STATE_B"
    assert btn._state_index == 1


def test_button_transition_wraps_around(btn):
    """Test that transitioning cycles back to the first state."""
    btn.transition()
    assert btn.state == "STATE_B"
    assert btn._state_index == 1

    btn.transition()
    assert btn.state == "STATE_A"
    assert btn._state_index == 0


def test_button_transition_explicit_state(btn):
    """Test transitioning to a specific named state."""
    btn.transition("STATE_B")
    assert btn.state == "STATE_B"

    btn.transition("STATE_A")
    assert btn.state == "STATE_A"


def test_button_transition_explicit_same_state(btn):
    """Test transitioning to the same named state."""
    btn.transition("STATE_B")
    assert btn.state == "STATE_B"
    assert btn._state_index == 1

    btn.transition("STATE_B")
    assert btn.state == "STATE_B"
    assert btn._state_index == 1


def test_button_transition_invalid_state(btn):
    """Test that transitioning to an invalid state raises ValueError."""
    with pytest.raises(
        ValueError,
        match=r"State 'INVALID_STATE' is not valid for TstButton. "
        r"Avalaible states: \['STATE_A', 'STATE_B'\]",
    ):
        btn.transition("INVALID_STATE")


def test_button_callback_execution(btn_with_cb):
    """Test that the callback is called during transition."""
    btn_with_cb.transition()  # STATE_A -> STATE_B
    btn_with_cb.transition()  # STATE_B -> STATE_A
    btn_with_cb.transition("STATE_A")  # STATE_A -> STATE_A

    assert len(btn_with_cb._calls) == 3
    assert btn_with_cb._calls[0] == (btn_with_cb, "STATE_A", "STATE_B")
    assert btn_with_cb._calls[1] == (btn_with_cb, "STATE_B", "STATE_A")
    assert btn_with_cb._calls[2] == (btn_with_cb, "STATE_A", "STATE_A")


def test_button_return_self(btn):
    """Test that transition returns the button instance for chaining."""
    result = btn.transition()
    assert result is btn


def test_swap_content_updates_displayed_content():
    shape = m.Circle()
    btn = TstButton(
        shape=shape,
        contents={"STATE_A": m.Text("A"), "STATE_B": m.Text("B")},
    )
    assert btn.content.text == "A"

    btn.swap_content("STATE_B")
    assert btn.content.text == "B"

    btn.transition()
    btn.swap_content("STATE_A")
    assert btn.content.text == "A"


def test_swap_content_defaults_to_current_state():
    shape = m.Circle()
    btn = TstButton(
        shape=shape,
        contents={"STATE_A": m.Text("A"), "STATE_B": m.Text("B")},
    )
    btn.transition("STATE_B")
    btn.swap_content()
    assert btn.content.text == "B"


def test_swap_content_empty_state():
    """Test swapping content when a state has an empty Mobject."""
    shape = m.Circle()
    contents = {
        "STATE_A": m.Text("A"),
        "STATE_B": m.VMobject(),  # Empty state
    }

    btn = TstButton(shape=shape, contents=contents)

    btn.transition("STATE_B")
    btn.swap_content()
    assert isinstance(btn.content, m.VMobject)
    assert len(btn.content.submobjects) == 0


def test_button_contents_initialized_with_None(btn):
    assert isinstance(btn._contents, m.VDict)
    assert list(btn._contents.submob_dict.keys()) == ["STATE_A", "STATE_B"]
    assert isinstance(btn._contents["STATE_A"], m.VMobject)
    assert isinstance(btn._contents["STATE_B"], m.VMobject)


def test_button_contents_initialized_with_dict():
    shape = m.Circle()
    d = m.Dot()
    r = m.Rectangle()
    btn = TstButton(shape=shape, contents={"STATE_A": d, "STATE_B": r})
    assert isinstance(btn._contents, m.VDict)
    assert list(btn._contents.submob_dict.keys()) == ["STATE_A", "STATE_B"]
    assert isinstance(btn._contents["STATE_A"], m.Dot)
    assert isinstance(btn._contents["STATE_B"], m.Rectangle)


def test_button_contents_initialized_with_single_vmob():
    shape = m.Circle()
    d = m.Dot()
    btn = TstButton(shape=shape, contents=d)
    assert isinstance(btn._contents, m.VDict)
    assert list(btn._contents.submob_dict.keys()) == ["STATE_A", "STATE_B"]
    assert isinstance(btn._contents["STATE_A"], m.Dot)
    assert isinstance(btn._contents["STATE_B"], m.Dot)
    assert btn._contents["STATE_A"] is btn._contents["STATE_B"]


def test_button_requires_all_states_in_contents():
    shape = m.Circle()
    # Missing STATE_B in contents should raise ValueError
    contents = {"STATE_A": m.VMobject()}

    with pytest.raises(ValueError, match="exactly one content VMobject for each state"):
        TstButton(shape=shape, contents=contents)


def test_button_contents_keys_must_match_states():
    shape = m.Circle()
    # Extra key not in states
    contents = {
        "STATE_A": m.VMobject(),
        "STATE_C": m.VMobject(),
    }

    with pytest.raises(KeyError, match="keys in the content dictionary should match"):
        TstButton(shape=shape, contents=contents)


def test_button_adds_all_components_in_init(btn):
    # Check that the button group contains the expected submobjects
    # Based on __init__: template, contents_template, deco_group, content
    assert len(btn.submobjects) == 4


# ----------------------------------------------------------------------
# ButtonGroup
# ----------------------------------------------------------------------
def test_btn_group_initializes_with_buttons(btn_group, btns):
    """ButtonGroup should contain all buttons passed to constructor."""
    assert len(btn_group.submobjects) == len(btns)
    for btn in btns:
        assert btn in btn_group.submobjects


def test_btn_group_empty_without_buttons():
    """ButtonGroup can be created without buttons."""
    bg = ButtonGroup()
    assert len(bg.submobjects) == 0


def test_btn_group_forwards_kwargs():
    """ButtonGroup should forward kwargs to VGroup."""
    bg = ButtonGroup(fill_opacity=0.5)
    assert bg.fill_opacity == 0.5


def test_original_callback_preserved(btn_with_cb):
    """Original button callback should still be callable."""
    assert callable(btn_with_cb._callback)


def test_group_callback_wraps_button_callback(btn_with_cb):
    """ButtonGroup should wrap the button's callback."""
    calls = []

    def group_callback(group, button, from_state, to_state):
        calls.append((group, button, from_state, to_state))

    bg = ButtonGroup(btn_with_cb, callback=group_callback)

    # Trigger a transition
    btn_with_cb.transition("STATE_B")

    # Both callbacks should have been called
    assert len(btn_with_cb._calls) == 1
    assert len(calls) == 1
    assert btn_with_cb._calls[0] == (btn_with_cb, "STATE_A", "STATE_B")
    assert calls[0] == (bg, btn_with_cb, "STATE_A", "STATE_B")


def test_multiple_buttons_each_get_wrapped(btns):
    """Each button in the group should have its callback wrapped."""
    calls_per_button = []

    def make_callback(idx):
        def callback(button, from_state, to_state):
            calls_per_button.append((idx, from_state, to_state))

        return callback

    # Assign unique callbacks to each button
    for i, btn in enumerate(btns):
        btn._callback = make_callback(i)

    bg = ButtonGroup(*btns)

    # Transition each button
    for btn in bg.submobjects:
        btn.transition("STATE_B")

    # Each button's callback should have been called once
    assert len(calls_per_button) == 3
    for i in range(3):
        assert (i, "STATE_A", "STATE_B") in calls_per_button


def test_default_callback_is_noop():
    """Default callback should be a no-op."""
    btn = TstButton(shape=m.Circle())
    bg = ButtonGroup(btn)  # No callback provided

    # Should not raise
    btn.transition("STATE_B")


def test_add_button_to_existing_group(btn_group, btn):
    """Should be able to add a button to an existing group."""
    initial_count = len(btn_group.submobjects)
    btn_group.add(btn)
    assert len(btn_group.submobjects) == initial_count + 1
    assert btn in btn_group.submobjects


def test_add_wraps_new_button_callback(btn_group, btn):
    """Adding a button should wrap its callback with group logic."""
    calls = []

    def group_callback(group, button, from_state, to_state):
        calls.append((group, button, from_state, to_state))

    # Recreate group with callback
    bg = ButtonGroup(callback=group_callback)
    bg.add(btn)

    btn.transition("STATE_B")

    assert len(calls) == 1
    assert calls[0] == (bg, btn, "STATE_A", "STATE_B")


def test_add_multiple_buttons_at_once(btn_group):
    """Should be able to add multiple buttons at once."""
    new_buttons = [TstButton(shape=m.Circle()) for _ in range(2)]
    initial_count = len(btn_group.submobjects)

    btn_group.add(*new_buttons)

    assert len(btn_group.submobjects) == initial_count + 2
    for btn in new_buttons:
        assert btn in btn_group.submobjects


def test_add_button_twice_wraps_only_once(btn_group, btn):
    """Adding the same button twice should not double-wrap the callback."""
    calls = []

    def group_callback(group, button, from_state, to_state):
        calls.append((from_state, to_state))

    bg = ButtonGroup(callback=group_callback)
    bg.add(btn)
    bg.add(btn)  # Add again

    btn.transition("STATE_B")

    assert len(calls) == 1
    assert len(bg.submobjects) == 1


def test_button_state_after_transition_in_group(btn_group):
    """Button state should update correctly when in a group."""
    btn = btn_group[0]
    btn.transition("STATE_B")
    assert btn.state == "STATE_B"


def test_button_transitions_still_work_in_group(btn_group):
    """Buttons should still be able to transition normally in a group."""
    btn = btn_group[0]

    assert btn.state == "STATE_A"
    btn.transition()  # Cycle to next state
    assert btn.state == "STATE_B"
    btn.transition()  # Cycle again
    assert btn.state == "STATE_A"


def test_add_empty_arguments(btn_group):
    """Adding no buttons should not change the group."""
    initial_count = len(btn_group.submobjects)
    btn_group.add()
    assert len(btn_group.submobjects) == initial_count


def test_callback_with_lambda():
    """Lambda callbacks should work correctly."""
    calls = []
    callback = lambda g, b, f, t: calls.append((g, b, f, t))  # noqa: E731

    btn = TstButton(shape=m.Circle())
    bg = ButtonGroup(btn, callback=callback)

    btn.transition("STATE_B")

    assert len(calls) == 1
    assert calls[0] == (bg, btn, "STATE_A", "STATE_B")


def test_button_removed_from_group_still_has_wrapped_callback(btn_group):
    """Removing a button doesn't unwrap its callback (current behavior)."""
    # Note: This is a limitation of the current implementation
    # The callback remains wrapped even after removal
    assert len(btn_group.submobjects) == 3
    btn = btn_group.submobjects[0]
    original_callback = btn._callback

    btn_group.remove(btn)

    # Callback is still wrapped (this is expected with current design)
    assert btn._callback is original_callback
    # VGroup is updated
    assert len(btn_group.submobjects) == 2


def test_button_added_to_multiple_groups_calls_all_callbacks(btn_group, btn_with_cb):
    calls = []

    def cb(g, b, f, t):
        calls.append(g)

    bg = ButtonGroup(callback=cb)
    btn_group._callback = cb
    assert len(calls) == 0
    btn_group.add(btn_with_cb)
    bg.add(btn_with_cb)
    btn_with_cb.transition()
    assert len(calls) == 2
    assert calls[0] is btn_group
    assert calls[1] is bg
    btn_with_cb.transition()
    assert len(calls) == 4
    btn_group.remove(btn)
    btn_with_cb.transition()
    assert len(calls) == 6
    # the button callback is called only once per transition
    assert len(btn_with_cb._calls) == 3


def test_add_returns_self(btn_group, btn):
    """add() should return self for method chaining."""
    result = btn_group.add(btn)
    assert result is btn_group


def test_direction_instantiating_with_single_button(btn):
    g = ButtonGroup(btn, direction=m.RIGHT, buff=0.4)
    assert np.array_equal(g.get_center(), m.ORIGIN)
    assert np.array_equal(btn.get_center(), m.ORIGIN)


def test_direction_instantiating_with_multiple_buttons(btns):
    g = ButtonGroup(*btns, direction=m.RIGHT, buff=0.4)
    g.move_to(m.ORIGIN, aligned_edge=m.LEFT)
    assert np.array_equal(g.get_edge_center(m.LEFT), m.ORIGIN)
    assert np.array_equal(btns[0].get_edge_center(m.LEFT), m.ORIGIN)
    assert btns[1].get_x() == pytest.approx(btns[0].get_x() + btns[0].width + 0.4)
    assert btns[2].get_x() == pytest.approx(
        btns[0].get_x() + 2 * (btns[0].width + 0.4)
    )  # buttons have same width


def test_direction_adding_one_button_at_a_time(btns):
    g = ButtonGroup(btns[0], direction=m.RIGHT, buff=0.4)
    assert np.array_equal(btns[0].get_center(), m.ORIGIN)
    g.add(btns[1])
    assert np.array_equal(btns[0].get_center(), m.ORIGIN)
    assert btns[1].get_x() == btns[0].get_x() + btns[0].width + 0.4
    g.add(btns[2])
    assert np.array_equal(btns[0].get_center(), m.ORIGIN)
    assert btns[1].get_x() == btns[0].get_x() + btns[0].width + 0.4
    assert btns[2].get_x() == pytest.approx(btns[0].get_x() + 2 * (btns[0].width + 0.4))


def test_direction_adding_all_button_at_once(btns):
    g = ButtonGroup(btns[0], direction=m.RIGHT, buff=0.4)
    assert np.array_equal(btns[0].get_center(), m.ORIGIN)
    g.add(btns[1], btns[2])
    assert np.array_equal(btns[0].get_center(), m.ORIGIN)
    assert btns[1].get_x() == btns[0].get_x() + btns[0].width + 0.4
    assert btns[2].get_x() == pytest.approx(btns[0].get_x() + 2 * (btns[0].width + 0.4))


def test_direction_removing_buttons(btns, btn):
    g = ButtonGroup(*btns, btn, direction=m.RIGHT, buff=0.4)
    assert [b.get_x() for b in g] == pytest.approx([0, 2.4, 4.8, 7.2])
    # remove last one
    g.remove(btn)
    assert [b.get_x() for b in g] == pytest.approx([0, 2.4, 4.8])
    # remove middle one
    g.remove(btns[1])
    assert [b.get_x() for b in g] == pytest.approx([0, 2.4])
    # remove first one: does not fill the gap
    g.remove(btns[0])
    assert [b.get_x() for b in g] == pytest.approx([2.4])
    assert len(g) == 1
    assert btns[2] in g
    # add: positioned relative the new first button
    g.add(btn)
    assert [b.get_x() for b in g] == pytest.approx([2.4, 4.8])


# ----------------------------------------------------------------------
# ButtonDict
# ----------------------------------------------------------------------
def test_initialization_with_buttons(btn_dict_with_cb, btns):
    """Test that ButtonDict initializes with buttons and wraps callbacks."""
    assert len(btn_dict_with_cb) == 3
    assert list(btn_dict_with_cb.keys()) == ["b1", "b2", "b3"]

    # Verify all buttons are in the VGroup
    assert len(btn_dict_with_cb.submobjects) == 3

    # Verify internal data mapping
    assert btn_dict_with_cb["b1"] is btns[0]
    assert btn_dict_with_cb["b2"] is btns[1]
    assert btn_dict_with_cb["b3"] is btns[2]

    btns[0].transition("STATE_B")
    assert len(btn_dict_with_cb._calls) == 1
    assert btn_dict_with_cb._calls[0] == (
        btn_dict_with_cb.group,
        btns[0],
        "STATE_A",
        "STATE_B",
    )


def test_initialization_empty():
    """Test creating an empty ButtonDict."""
    bd = ButtonDict()
    assert len(bd) == 0
    assert len(bd.submobjects) == 0
    assert isinstance(bd.group, m.VGroup)
    assert len(bd.group) == 0
    assert len(bd.data) == 0


def test_initialization_iterable(btn):
    btn2 = btn.copy()
    bd = ButtonDict([("btn", btn), ("btn2", btn2)])
    assert len(bd) == 2
    assert list(bd.keys()) == ["btn", "btn2"]

    # Verify all buttons are in the VGroup
    assert len(bd.submobjects) == 2

    # Verify internal data mapping
    assert bd["btn"] is btn
    assert bd["btn2"] is btn2


def test_buttondict_add_remove(btn_dict, btn):
    assert btn not in btn_dict.submobjects
    btn_dict.add({"btn": btn})
    assert btn in btn_dict.submobjects
    assert btn in btn_dict._group
    assert btn_dict["btn"] is btn
    btn_dict.remove("btn")
    assert btn not in btn_dict.submobjects
    assert btn not in btn_dict._group
    with pytest.raises(KeyError):
        assert btn_dict["btn"] is btn
    # iterable syntax
    btn_dict.add([("btn", btn)])
    assert btn in btn_dict.submobjects
    assert btn in btn_dict._group
    assert btn_dict["btn"] is btn


def test_setitem_adds_to_group_and_dict(btn_dict_with_cb, btn):
    """Test that adding a button updates both the dict and the VGroup."""
    btn_dict_with_cb["new"] = btn

    assert len(btn_dict_with_cb) == 4
    assert btn_dict_with_cb["new"] is btn
    assert btn in btn_dict_with_cb.submobjects
    assert btn in btn_dict_with_cb.group.submobjects


def test_setitem_type_error(btn_dict_with_cb):
    """Test that non-Button instances raise TypeError."""
    with pytest.raises(TypeError, match="expects Button instances"):
        btn_dict_with_cb["invalid"] = "not a button"


def test_delitem_removes_from_all_sources(btn_dict_with_cb, btns):
    """Test that deleting a key removes it from dict, VGroup, and Group."""
    assert len(btn_dict_with_cb) == 3
    assert len(btn_dict_with_cb.submobjects) == 3

    del btn_dict_with_cb["b1"]

    assert len(btn_dict_with_cb) == 2
    assert len(btn_dict_with_cb.submobjects) == 2
    assert "b1" not in btn_dict_with_cb
    assert btns[0] not in btn_dict_with_cb.submobjects
    assert btns[0] not in btn_dict_with_cb.group.submobjects


def test_contains_operator(btn_dict_with_cb):
    """Test the 'in' operator."""
    assert "b1" in btn_dict_with_cb
    assert "nonexistent" not in btn_dict_with_cb


def test_iter_and_len(btn_dict_with_cb):
    """Test iteration and length."""
    assert len(btn_dict_with_cb) == 3
    keys = list(btn_dict_with_cb)
    assert set(keys) == {"b1", "b2", "b3"}


def test_keys_values_items(btn_dict_with_cb):
    """Test dict view methods."""
    assert set(btn_dict_with_cb.keys()) == {"b1", "b2", "b3"}
    assert list(btn_dict_with_cb.values()) == [
        btn_dict_with_cb["b1"],
        btn_dict_with_cb["b2"],
        btn_dict_with_cb["b3"],
    ]

    items = list(btn_dict_with_cb.items())
    assert len(items) == 3
    assert ("b1", btn_dict_with_cb["b1"]) in items


def test_manim_methods(btn_dict_with_cb):
    """Test that VGroup methods like arrange work."""
    # should not raise an error
    btn_dict_with_cb.arrange(m.DOWN)
    btn_dict_with_cb.shift(m.RIGHT)

    assert (
        btn_dict_with_cb.submobjects[0].get_center()[1]
        != btn_dict_with_cb.submobjects[1].get_center()[1]
    )


def test_callback_wrapping(btn_dict_with_cb, btn_with_cb):
    """Test that the group callback is invoked when a button state changes."""

    btn_dict_with_cb["new"] = btn_with_cb
    btn_dict_with_cb["new"].transition("STATE_B")
    assert len(btn_dict_with_cb._calls) == 1
    assert btn_dict_with_cb._calls[0] == (
        btn_dict_with_cb.group,
        btn_with_cb,
        "STATE_A",
        "STATE_B",
    )
    assert len(btn_with_cb._calls) == 1
    assert btn_with_cb._calls[0] == (
        btn_with_cb,
        "STATE_A",
        "STATE_B",
    )


def test_data_property_access(btns, btn_dict_with_cb):
    """Test accessing the internal data dict."""
    assert btn_dict_with_cb.data is btn_dict_with_cb._data
    assert "b1" in btn_dict_with_cb.data
    assert btn_dict_with_cb.data["b1"] is btns[0]


def test_group_property_access(btns, btn_dict_with_cb):
    """Test accessing the internal ButtonGroup."""
    assert isinstance(btn_dict_with_cb.group, ButtonGroup)
    assert len(btn_dict_with_cb.group.submobjects) == 3


# ----------------------------------------------------------------------
# PushButton
# ----------------------------------------------------------------------
def test_pushbutton_default_state():
    """Test that PushButton initializes to UNPUSHED."""
    shape = m.RoundedRectangle(corner_radius=0.3, width=3.0, height=1.2)
    contents = {"UNPUSHED": m.Text("Unpushed"), "PUSHED": m.Text("Pushed")}
    btn = PushButton(shape=shape, contents=contents)
    assert btn.state == "UNPUSHED"
    assert btn.content.text == "Unpushed"


def test_pushbutton_transition_changes_internal_properties():
    shape = m.Rectangle()
    pb = PushButton(shape=shape)

    assert pb.state == "UNPUSHED"
    pb.transition("PUSHED")
    assert pb.state == "PUSHED"

    pb.transition()
    assert pb.state == "UNPUSHED"


def test_pushbutton_build_state_returns_expected_structure():
    shape = m.Rectangle()
    pb = PushButton(shape=shape)

    deco_group, contents = pb._build_state("UNPUSHED")

    assert isinstance(deco_group, m.VGroup)
    assert isinstance(contents, m.VDict)

    # Check that deco_group has expected components (shadow, body, etc.)
    assert len(deco_group.submobjects) == 5


def test_pushbutton_callback_on_push():
    """Test callback execution specifically for PushButton transitions."""
    shape = m.RoundedRectangle(corner_radius=0.3, width=3.0, height=1.2)
    contents = {"UNPUSHED": m.Text("Unpushed"), "PUSHED": m.Text("Pushed")}
    transitions = []

    def track_transitions(btn, from_s, to_s):
        transitions.append((btn, from_s, to_s))

    btn = PushButton(shape=shape, contents=contents, callback=track_transitions)

    btn.transition()  # UNPUSHED -> PUSHED
    btn.transition()  # PUSHED -> UNPUSHED

    assert len(transitions) == 2
    assert transitions[0] == (btn, "UNPUSHED", "PUSHED")
    assert transitions[1] == (btn, "PUSHED", "UNPUSHED")


def test_pushbutton_content_opacity_after_transition():
    pushed = m.Text("Pushed")
    unpushed = m.Text("Unpushed").set_fill(opacity=0.5)
    shape = m.Rectangle()
    pb = PushButton(
        shape=shape,
        contents={
            "PUSHED": pushed,
            "UNPUSHED": unpushed,
        },
    )
    assert pb.state == "UNPUSHED"
    assert pb.content is unpushed
    assert pb.content.fill_opacity == 0.5
    pb.transition()
    pb.swap_content()
    assert pb.state == "PUSHED"
    assert pb.content.text == pushed.text  # content is now a copy
    assert pb.content.fill_opacity == 1
    pb.transition().swap_content()
    assert pb.state == "UNPUSHED"
    assert pb.content.text == unpushed.text
    assert pb.content.fill_opacity == 0.5


# ----------------------------------------------------------------------
# HighlightButton
# ----------------------------------------------------------------------
def test_highlightbutton_content_opacity_after_transition():
    active = m.Text("Active")
    inactive = m.Text("Inactive").set_fill(opacity=0.5)
    shape = m.Rectangle()
    hb = HighlightButton(
        shape=shape,
        contents={
            "ACTIVE": active,
            "INACTIVE": inactive,
        },
    )
    assert hb.state == "INACTIVE"
    assert hb.content is inactive
    assert hb.content.fill_opacity == 0.5
    hb.transition()
    hb.swap_content()
    assert hb.state == "ACTIVE"
    assert hb.content.text == active.text  # content is now a copy
    assert hb.content.fill_opacity == 1
    hb.transition().swap_content()
    assert hb.state == "INACTIVE"
    assert hb.content.text == inactive.text
    assert hb.content.fill_opacity == 0.5
