from unittest.mock import patch

import manim as m
import pytest

from manim_mjutils.ui import Cursor


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
@pytest.fixture
def mock_svg_files(tmp_path):
    """
    Creates a temporary directory structure with dummy SVG files
    to satisfy the Cursor's file scanning requirements.
    """
    cursor_dir = tmp_path / "assets" / "cursors"
    cursor_dir.mkdir(parents=True)

    # Create dummy SVG files
    (cursor_dir / "mock1.svg").write_text("<svg>dummy</svg>")
    (cursor_dir / "mock2.svg").write_text("<svg>dummy</svg>")
    (cursor_dir / "mock3.svg").write_text("<svg>dummy</svg>")

    return cursor_dir


@pytest.fixture
def cursor_instance(mock_svg_files):
    """
    Initializes a Cursor instance with the mocked SVG files.
    """
    c = Cursor(svg_paths=[mock_svg_files], idle_duration=2.0, fade_duration=0.5)
    return c


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
def test_cursor_initialization_loads_cursors(cursor_instance, mock_svg_files):
    """Test that the cursor loads all available SVGs and maps them correctly."""
    assert "MOCK1" in cursor_instance.cursors
    assert "MOCK2" in cursor_instance.cursors
    assert "MOCK3" in cursor_instance.cursors

    assert cursor_instance.cursors["MOCK1"] == mock_svg_files / "mock1.svg"


def test_cursor_initialization_missing_required_file(mock_svg_files, tmp_path):
    """Test that initialization fails if LEFT_PTR is missing."""
    # Create a directory without left_ptr.svg
    bad_dir = tmp_path / "bad_cursors"
    bad_dir.mkdir()
    (bad_dir / "mock2.svg").write_text("<svg>dummy</svg>")

    with (
        pytest.raises(KeyError, match="LEFT_PTR"),
        patch.object(Cursor, "DEFAULT_PATH", bad_dir),
    ):
        Cursor(svg_paths=[], idle_duration=-1)


def test_set_shape_valid(cursor_instance):
    """Test switching to a valid cursor."""
    initial_scale = cursor_instance._scale_factor

    cursor_instance.fill_opacity = 0.5
    cursor_instance._idle_timer = 1
    result = cursor_instance.set_shape("MOCK2")

    assert result is cursor_instance  # Should return self for chaining
    assert cursor_instance._idle_timer == 0
    assert cursor_instance.fill_opacity == 1
    assert cursor_instance._scale_factor == initial_scale


def test_set_shape_invalid(cursor_instance):
    """Test switching to a non-existent cursor raises ValueError."""
    with pytest.raises(ValueError, match="Unknown cursor: INVALID_CURSOR"):
        cursor_instance.set_shape("INVALID_CURSOR")


def test_set_shape_no_timer_reset(cursor_instance):
    initial_scale = cursor_instance._scale_factor

    cursor_instance.fill_opacity = 0.5
    cursor_instance._idle_timer = 1
    result = cursor_instance.set_shape("MOCK2", reset_timer=False)

    assert result is cursor_instance  # Should return self for chaining
    assert cursor_instance._idle_timer == 1
    assert cursor_instance.fill_opacity == 0.5
    assert cursor_instance._scale_factor == initial_scale


def test_scale_accumulation(cursor_instance):
    """Test that scale factors accumulate correctly."""
    # base factor = 0.1
    cursor_instance.scale(2.0)
    assert cursor_instance._scale_factor == 0.2

    cursor_instance.scale(0.5)
    assert cursor_instance._scale_factor == 0.1


def test_scale_returns_self(cursor_instance):
    """Test that scale returns the instance for chaining."""
    result = cursor_instance.scale(1.5)
    assert result is cursor_instance


def test_idle_fade_logic_does_not_reset_with_animate(cursor_instance):
    """Test that moving the cursor resets the idle timer."""
    cursor_instance._idle_timer = 5.0
    cursor_instance.animate.shift(m.RIGHT)
    assert cursor_instance._idle_timer == 5.0


def test_idle_fade_logic_fades_when_stationary(cursor_instance):
    """Test that opacity decreases when stationary past idle_duration."""
    assert cursor_instance._idle_fade in cursor_instance.updaters
    cursor_instance.animate.shift(m.LEFT)
    assert cursor_instance._idle_fade in cursor_instance.updaters
    cursor_instance.idle_duration = 1.0
    cursor_instance.fade_duration = 1.0

    # Set idle time to exactly the threshold
    cursor_instance._idle_timer = 1.0

    # Advance time by 0.5 seconds (past threshold)
    cursor_instance._idle_fade(cursor_instance, 0.5)

    # Opacity should be 0.5 (1 - (1.5 - 1.0)/1.0)
    assert cursor_instance._idle_timer == 1.5
    assert cursor_instance.fill_opacity == 0.5
    assert cursor_instance.stroke_opacity == 0.5
