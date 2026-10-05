from types import MethodType
from unittest.mock import MagicMock

import numpy as np
import pytest

from manim_mjutils import CartesianCameraMixin


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
@pytest.fixture
def scene():
    """Create a minimal mock ThreeDScene with camera support."""
    scene = MagicMock()
    camera = MagicMock()
    scene.camera = camera
    scene.set_camera_orientation = MagicMock()
    scene.move_camera = MagicMock()
    scene.set_camera_position = MethodType(
        CartesianCameraMixin.set_camera_position, scene
    )
    scene.get_camera_position_cartesian = MethodType(
        CartesianCameraMixin.get_camera_position_cartesian, scene
    )
    return scene


def configure_camera(scene, r, phi, theta):
    """Helper to configure camera mocks consistently."""
    scene.camera.get_focal_distance.return_value = float(r)
    scene.camera.get_phi.return_value = float(phi)
    scene.camera.get_theta.return_value = float(theta)


# ----------------------------------------------------------------------
# get_camera_position_cartesian
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("r", "phi", "theta", "expected"),
    [
        (0.0, 0.0, 0.0, (0.0, 0.0, 0.0)),  # on ORIGIN
        (5.0, np.pi / 2, 0.0, (5.0, 0.0, 0.0)),  # on +x-axis
        (5.0, np.pi / 2, np.pi / 2, (0.0, 5.0, 0.0)),  # on +y-axis
        (5.0, 0.0, 0.0, (0.0, 0.0, 5.0)),  # on +z-axis
        (5.0, np.pi, 0.0, (0.0, 0.0, -5.0)),  # on -z-axis
    ],
)
def test_get_camera_position_cartesian(scene, r, phi, theta, expected):
    """Test positions on positive coordinate axes."""
    configure_camera(scene, r, phi, theta)
    position = scene.get_camera_position_cartesian()

    np.testing.assert_allclose(position, expected, atol=1e-10)


def test_get_camera_position_cartesian_general_position(scene):
    """Test a general 3D position."""
    # Position: (3, 4, 5)
    expected_pos = np.array([3.0, 4.0, 5.0])
    r = np.linalg.norm(expected_pos)
    phi = np.arccos(np.clip(expected_pos[2] / r, -1, 1))
    theta = np.arctan2(expected_pos[1], expected_pos[0])

    configure_camera(scene, r, phi, theta)
    position = CartesianCameraMixin.get_camera_position_cartesian(scene)

    np.testing.assert_allclose(position, expected_pos, rtol=1e-10, atol=1e-10)


# ----------------------------------------------------------------------
# set_camera_position
# ----------------------------------------------------------------------
def test_set_camera_position_2d_default(scene):
    """Test the '2D' default mode."""
    scene.set_camera_position(position="2D", run_time=0)

    # Verify expected 2D orientation was passed
    args = scene.set_camera_orientation.call_args.kwargs
    phi = args["phi"]
    theta = args["theta"]
    zoom = args["zoom"]
    assert phi == 0
    assert theta == -np.pi / 2
    assert zoom == 1.0

    # check camera position
    configure_camera(scene, 20, phi, theta)
    np.testing.assert_allclose(
        scene.get_camera_position_cartesian(), np.array([0.0, 0.0, 20.0])
    )


@pytest.mark.parametrize(
    ("position", "expected", "atol"),
    [
        ([0, 0, 0], [0, 0, 0], 0),  # Origin should not raise
        (
            [1e-16, 1e-17, 1e-16],
            [0, 0, 0],
            1e-14,
        ),  # Close to origin should not raise nor cause infinities
        ([5, 3, 4], [5, 3, 4], 0),
        ([-6, -4, -2], [-6, -4, -2], 0),  # negative values
        ([1, 0, 0], [1, 0, 0], 1e-14),  # +x-axis
        ([-1, 0, 0], [-1, 0, 0], 1e-14),  # -x-axis
        ([0, 1, 0], [0, 1, 0], 1e-14),  # +y-axis
        ([0, -1, 0], [0, -1, 0], 1e-14),  # -y-axis
        ([0, 0, 1], [0, 0, 1], 1e-14),  # +z-axis
        ([0, 0, -1], [0, 0, -1], 1e-14),  # -z-axis
    ],
)
def test_set_camera_position(scene, position, expected, atol):
    scene.set_camera_position(position=position, run_time=0)

    call_kwargs = scene.set_camera_orientation.call_args.kwargs
    phi = call_kwargs["phi"]
    theta = call_kwargs["theta"]
    r = call_kwargs["focal_distance"]
    assert not np.isnan(phi)
    assert not np.isnan(theta)
    assert not np.isnan(r)

    # Check position
    configure_camera(scene, r, phi, theta)
    np.testing.assert_allclose(
        scene.get_camera_position_cartesian(), expected, atol=atol
    )


def test_set_camera_position_with_zoom(scene):
    """Test that zoom parameter is passed correctly."""
    position = [5, 3, 4]
    zoom = 2.5
    scene.set_camera_position(position=position, zoom=zoom, run_time=0)
    call_kwargs = scene.set_camera_orientation.call_args.kwargs
    assert call_kwargs["zoom"] == zoom


def test_set_camera_position_with_roll(scene):
    """Test that roll parameter maps to gamma."""
    position = [5, 3, 4]
    roll = np.pi / 4
    scene.set_camera_position(position=position, roll=roll, run_time=0)
    call_kwargs = scene.set_camera_orientation.call_args.kwargs
    assert call_kwargs["gamma"] == roll


def test_set_camera_position_move_camera_called_when_run_time_nonzero(scene):
    """Test that move_camera is used instead of set_camera_orientation."""
    position = [5, 3, 4]
    scene.set_camera_position(position=position, run_time=1.0)
    # Verify move_camera was called, not set_camera_orientation
    scene.move_camera.assert_called_once()
    scene.set_camera_orientation.assert_not_called()


def test_set_camera_position_with_mobject_frame_center(scene):
    """Test that Mobjects as frame_center are passed through (not converted)."""
    from manim import Mobject

    position = [5, 3, 4]
    frame_center = Mobject()

    scene.set_camera_position(position=position, frame_center=frame_center, run_time=0)

    call_kwargs = scene.set_camera_orientation.call_args.kwargs
    assert call_kwargs["frame_center"] is frame_center
