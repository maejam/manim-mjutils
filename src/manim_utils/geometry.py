from typing import Literal, cast, overload

import manim as m
import numpy as np
from manim.typing import Point3D
from numpy.typing import NDArray


@overload
def get_bounds(
    *vmobjects: m.VMobject,
    as_len: Literal[False] = False,
    include_stroke: bool | None = None,
) -> tuple[Point3D, Point3D, Point3D]: ...


@overload
def get_bounds(
    *vmobjects: m.VMobject, as_len: Literal[True], include_stroke: bool | None = None
) -> tuple[float, float, float, Point3D]: ...


def get_bounds(
    *vmobjects: m.VMobject, as_len: bool = False, include_stroke: bool | None = None
) -> tuple[Point3D, Point3D, Point3D] | tuple[float, float, float, Point3D]:
    """Calculate the bounding box of a group of VMobjects.

    This function computes the bounding box for a (group of) vmobject(s).
    Depending on the `as_len` parameter value, it can return:
     - the extent of the bounding box in each dimension + the Point3D representing the
       center of the bounding box (`as_len=True`). Useful for instance to build a
       surrounding rectangle.
     - three Point3D numpy arrays representing respectively the lower left corner, the
       center and the upper right corner of the bounding box. Useful for instance to
       check whether another mobject lies inside the box boundaries.

    Parameters
    ----------
    *vmobjects
        One or more VMobjects.
    as_len
        If False (default), returns (min_point, center_point, max_point).
        If True, returns (width, height, depth, center_point).
    include_stroke
        Controls how stroke width affects the bounding box:
         - None (default): Returns the bounding box of the geometric path only.
           The bounding box lies in the middle of the stroke width.
         - True: Expands the bounding box to include the full stroke width.
         - False: Shrinks the bounding box to exclude the stroke width.
        The function tries to be smart about when to include/exclude stroke width or
        not:
         - a 2D shape bounding box will never gain depth.
         - a 0D (Dot) or 1D (Line) shape bounding box will have extent only in the
           dimensions it spans or if stroke is included. This might be a little buggy
           but seems to mostly work and is probably a edge case anyway.

    Returns
    -------
    If as_len is False:
        A tuple (down_left, center, up_right) where each element is a numpy array
        (Point3D).
    If as_len is True:
        A tuple (width, height, depth, center) where width/height/depth are floats
        and center is a Point3D.

    Examples
    --------
    >>> square = Square(side_length=2)
    >>> d = Dot().shift(LEFT * 2)
    >>> min_pt, center_pt, max_pt = get_bounds(square)
    >>> is_left_of_bbox = d.get_x() < min_pt[0]
    >>> width, height, depth, center = get_bounds(
    >>>     square, as_len=True, include_stroke=True
    >>> )
    >>> surrounding = Rectangle(width=width, height=height, color=RED).move_to(center)

    >>> self.add(square, d, surrounding)
    >>> print(is_left_of_bbox)
    True

    """
    if include_stroke is None:
        points = [p for obj in vmobjects for p in obj.get_all_points()]
        if len(points) == 0:
            zero = np.array([0.0, 0.0, 0.0])
            if not as_len:
                return (zero, zero.copy(), zero.copy())
            return (0.0, 0.0, 0.0, zero)
        v_min = np.min(points, axis=0)
        v_max = np.max(points, axis=0)
    else:
        multiplier = 1.0 if include_stroke else -1.0
        all_v_mins = []
        all_v_maxs = []

        for obj in vmobjects:
            pts = obj.get_all_points()
            if len(pts) == 0:
                continue

            sw = obj.get_stroke_width()
            adjustment = (sw / 200) * multiplier
            obj_min = np.min(pts, axis=0)
            obj_max = np.max(pts, axis=0)

            # NOTE: We want to bound only in the dimensions that the object spans.
            # For instance, for a horizontal 2D Line with include_stroke=False, we don't
            # want to include any height.
            # For a 2D object, we never want to include any depth to the bounding box.

            # Determine which axes have actual extent
            has_extent = (obj_max - obj_min) > 1e-9
            adjusted_min = obj_min.copy()
            adjusted_max = obj_max.copy()

            for dim in range(3):
                # X and Y: Adjust if (include_stroke) OR (has_extent).
                #   - ensures 1D lines get thickness and 2D shapes expand.
                # Z: Adjust ONLY if (has_extent).
                #   - prevents flat 2D shapes from gaining phantom Z-depth.
                #   - ensures 3D objects expand correctly in Z.

                if dim == 2:
                    if has_extent[dim]:
                        adjusted_min[dim] -= adjustment
                        adjusted_max[dim] += adjustment
                else:
                    if include_stroke or has_extent[dim]:
                        adjusted_min[dim] -= adjustment
                        adjusted_max[dim] += adjustment

            all_v_mins.append(adjusted_min)
            all_v_maxs.append(adjusted_max)

        if not all_v_mins:
            zero = np.array([0.0, 0.0, 0.0])
            if not as_len:
                return (zero, zero.copy(), zero.copy())
            return (0.0, 0.0, 0.0, zero)

        v_min = np.min(all_v_mins, axis=0)
        v_max = np.max(all_v_maxs, axis=0)

    center = m.midpoint(list(v_min), list(v_max))

    if not as_len:
        return cast(tuple[Point3D, Point3D, Point3D], (v_min, center, v_max))
    return cast(
        tuple[float, float, float, Point3D],
        (v_max[0] - v_min[0], v_max[1] - v_min[1], v_max[2] - v_min[2], center),
    )


def is_inside_bounds(
    mobject: m.Mobject,
    *vmobjects: m.VMobject,
    bounds: tuple[Point3D, Point3D, Point3D] | None = None,
    strict: bool = True,
    include_stroke: bool | None = None,
) -> bool:
    """Check if a mobject is inside the bounding box of a group of VMobjects.

    This function compares the Axis-Aligned Bounding Box (AABB) of the `mobject`
    against the AABB of the provided `vmobjects`.

    Parameters
    ----------
    mobject
        The mobject to check.
    *vmobjects
        One or more VMobjects defining the target bounding box.
    bounds
        Alternatively, a 3-tuple containing the result of `get_bounds` with
        `as_len=False` can be passed. If passed, these values will be used for the
        `vmobjects` bounds. Useful for performance when checking multiple mobjects
        against the same bounds.
    strict
        - If True (default): checks if the mobject is fully contained within the bounds.
        - If False: checks if the mobject overlaps with the bounds.
    include_stroke
        Passed to `get_bounds` to determine if stroke width should be included in the
        target bounding box calculation.

    Returns
    -------
    bool: True if the condition is met, False otherwise.

    """
    points = mobject.get_all_points()
    mob_min_pt = np.min(points, axis=0)
    mob_max_pt = np.max(points, axis=0)
    if bounds:
        min_pt, _, max_pt = bounds
    else:
        min_pt, _, max_pt = get_bounds(
            *vmobjects, as_len=False, include_stroke=include_stroke
        )

    # apply a tolerance to inequalities for floating point errors
    rtol: float = 1e-5
    atol: float = 1e-8

    def is_ge(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.bool_]:
        # Calculate the allowed negative deviation
        # This mimics the logic inside np.isclose: |a-b| <= atol + rtol*|b|
        # We want to accept if (a-b) is slightly negative but within tolerance
        tolerance = atol + rtol * np.abs(b)
        return (a - b) >= -tolerance

    def is_le(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.bool_]:
        tolerance = atol + rtol * np.abs(b)
        return (b - a) >= -tolerance

    if strict:
        mask1 = is_ge(mob_min_pt, min_pt)
        mask2 = is_le(mob_max_pt, max_pt)

    else:
        mask1 = is_ge(mob_max_pt, min_pt)
        mask2 = is_le(mob_min_pt, max_pt)

    return bool(np.all(mask1 & mask2))


def clip_vmobject(
    subject: m.VMobject,
    clipper: m.VMobject,
    strict: bool = False,
) -> m.VGroup:
    """Clip a subject VMobject by a clipper VMobject.

    This function computes the intersection between 2 VMobjects: the subject and the
    clipper. It is primarily meant to be used with Text-like Mobjects.

    It is superior to the built-in :class:`manim.Intersection` in 4 ways:
     - it accepts directly composite vmobjects such as VGroup or Text.
     - style preserving: the style of the subject is preserved.
     - it scales much better for complex vmobjects with many submobjects. It is
       a bit slower for simple shapes though.
     - submobjects that intersect the clipper can be discarded with strict=True.

    Parameters
    ----------
    subject
        The VMobject to clip.
    clipper
        The VMobject by which to clip the subject.
    strict
        If True, only keep the submobjects that are fully inside the clipper bounds.
        If False (default), keep the points of the submobjects intersecting the clipper
        that are inside it.

    Returns
    -------
    A VGroup containing all the subject's family members with points flattened.
    Those of the family members that intersect with the clipper are discarded if
    strict=True and are Intersection objects with strict=False.
    If the clipper does not have any points, a flattened VGroup containing all the
    family members with points is returned.

    Notes
    -----
     - Only the inside of the clipper stroke is considered: a vmobject touching
       the outer stroke of the clipper is considered to be outside of it.
     - Unlike Intersection, the order matters here:
       (clip_vmobject(square, circle) != clip_vmobject(circle, square)).

    """
    clipper_family = cast(list[m.VMobject], clipper.family_members_with_points())
    if not clipper_family:
        vmobs = cast(
            list[m.VMobject],
            [child.copy() for child in subject.family_members_with_points()],
        )
        return m.VGroup(vmobs)

    clipper_bounds = get_bounds(clipper, as_len=False, include_stroke=False)
    result_group = m.VGroup()

    for child in subject.family_members_with_points():
        child = cast(m.VMobject, child)
        # if child fully inside clipper: keep it
        if is_inside_bounds(
            child, bounds=clipper_bounds, strict=True, include_stroke=False
        ):
            result_group.add(child.copy())
            continue

        # if child fully outside: drop it
        if not is_inside_bounds(
            child, bounds=clipper_bounds, strict=False, include_stroke=False
        ):
            continue

        # if we are here, child is partially inside: drop it or crop it
        if strict:
            continue
        cropped_child = m.Intersection(child, *clipper_family).match_style(child)
        if len(cropped_child.points) > 0:
            result_group.add(cropped_child)

    return result_group
