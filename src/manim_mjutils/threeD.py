from collections.abc import Iterable, Sequence
from typing import Any, Protocol

import manim as m
import numpy as np
from manim.typing import Point3DLike


class _Has3DCamera(Protocol):
    camera: m.ThreeDCamera

    def set_camera_orientation(
        self,
        phi: float | None = None,
        theta: float | None = None,
        gamma: float | None = None,
        zoom: float | None = None,
        focal_distance: float | None = None,
        frame_center: m.Mobject | Sequence[float] | None = None,
        **kwargs: Any,
    ) -> None: ...

    def move_camera(
        self,
        phi: float | None = None,
        theta: float | None = None,
        gamma: float | None = None,
        zoom: float | None = None,
        focal_distance: float | None = None,
        frame_center: m.Mobject | Sequence[float] | None = None,
        added_anims: Iterable[m.Animation] = [],
        **kwargs: Any,
    ) -> None: ...


class CartesianCameraMixin:
    """Mixin for ThreeDScene that provide cartesian camera positioning.

    Examples
    --------
    >>> class MyScene(CartesianCameraMixin, ThreeDScene):
    ...     def construct(self):
    ...         self.set_camera_position([5, 3, 4], frame_center=[1, 2, 3])

    """

    def set_camera_position(
        self: _Has3DCamera,
        position: Point3DLike | Sequence[float] | str = "2D",
        frame_center: m.Mobject | Point3DLike | None = None,
        roll: float = 0,
        zoom: float = 1.0,
        added_anims: Iterable[m.Animation] = (),
        run_time: float = 0,
        **kwargs: Any,
    ) -> None:
        """Set the camera position using (x, y, z) cartesian coordinates.

        Parameters
        ----------
        position
            Camera position in (x, y, z) world coordinates. The default (`"2D"`) will
            reproduce the usual 2D camera position.
        frame_center
            The new center of the camera frame in cartesian coordinates.
            Defaults to `None`, meaning the frame center is unchanged after the camera
            is repositioned.
        roll
            The rotation of the camera about the vector from the ORIGIN to the Camera.
            Equivalent to `gamma` in `ThreeDScene.move_camera` and
            `ThreeDScene.set_camera_orientation`.
        zoom
            The zoom factor of the camera.
        added_anims
            Any other animations to be played at the same time.
            Only useful if `run_time` is not 0.
        run_time
            Animation duration in seconds. `0` means instant change.
        **kwargs
            Keyword arguments forwarded to the play call.
            Only useful if `run_time` is not 0.
        """
        look_at = (
            tuple(frame_center)
            if isinstance(frame_center, np.ndarray)
            else frame_center
        )

        if isinstance(position, str):
            # Default 2D view
            phi, theta, gamma = 0.0, -m.PI / 2, 0.0
            focal_dist = 20.0

        else:
            position = np.array(position, dtype=float)
            r = float(np.linalg.norm(position))
            if r > 0:
                z_over_r = np.clip(position[2] / r, -1, 1)  # Force into valid domain
                phi = np.arccos(z_over_r)
                theta = np.arctan2(position[1], position[0])
            else:
                phi = 0.0
                theta = 0.0

            gamma = roll
            focal_dist = r

        frame_center = np.array(frame_center, dtype=float)
        if run_time == 0:
            self.set_camera_orientation(
                phi=phi,
                theta=theta,
                gamma=gamma,
                zoom=zoom,
                focal_distance=focal_dist,
                frame_center=look_at,
            )
        else:
            added_anims = list(added_anims)
            self.move_camera(
                phi=phi,
                theta=theta,
                gamma=gamma,
                zoom=zoom,
                focal_distance=focal_dist,
                frame_center=look_at,
                added_anims=added_anims,
                run_time=run_time,
            )

    def get_camera_position_cartesian(self: _Has3DCamera) -> np.ndarray:
        """Reconstruct cartesian camera position from spherical coordinates."""
        r = self.camera.get_focal_distance()
        phi = self.camera.get_phi()
        theta = self.camera.get_theta()

        x = r * np.sin(phi) * np.cos(theta)
        y = r * np.sin(phi) * np.sin(theta)
        z = r * np.cos(phi)

        return np.array([x, y, z])
