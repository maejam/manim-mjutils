from collections.abc import Callable
from typing import Any

import manim as m
from manim.utils.unit import Pixels


class Stencil(m.VMobject):
    """A VMobject that represents the Boolean combination of a shape and a clip.

    Parameters
    ----------
    shape
        The base shape; defaults to a ``Rectangle``.
    clip
        The clipping shape; defaults to an empty ``VMobject``.
    bool_op
        Function that combines ``shape`` and ``clip`` (e.g. ``manim.Difference``).
    wrapped
        An optional VMobject the stencil will cover. If given, the size and position of
        the stencil will adapt to the wrapped Mobject through a manim updater.
        If ``None`` (default), the stencil shape will remain unchanged. It is also
        possible to set this parameter to ``None`` and attach a custom updater to the
        stencil. For permormance reasons, it is advised to set ``wrapped`` to
        ``None`` if the geometry and position of the covered mobject remain fixed.
    **kwargs
        Additional arguments passed to ``m.VMobject.__init__``. If not specified, the
        ``fill_color`` will default to the scene background color, and the
        ``fill_opacity`` to ``1``.
    """

    def __init__(
        self,
        shape: m.VMobject | None = None,
        clip: m.VMobject | None = None,
        bool_op: Callable[[m.VMobject, m.VMobject], m.VMobject] = m.Difference,
        wrapped: m.VMobject | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("fill_color", m.config.background_color)
        kwargs.setdefault("fill_opacity", 1)
        super().__init__(**kwargs)

        self._shape = shape or m.Rectangle()
        self._clip = clip or m.VMobject()
        self._bool_op = bool_op
        self._wrapped = wrapped
        self._static_clip = False
        self.add(self._clip)

        self._make_stencil()
        if self._wrapped:
            self.add_updater(self._adapt_stencil, call_updater=True)

    def _make_stencil(self) -> None:
        """Recompute the stencil geometry."""
        stencil = self._bool_op(
            self._shape,
            self._clip,
        )
        self.match_points(stencil)

    def _adapt_stencil(self, mob: m.Mobject) -> None:
        """Keep the stencil aligned with the wrapped Mobject."""
        if self._wrapped is None:
            return
        w, h, _, center = get_bounds(self._wrapped, as_len=True, include_stroke=True)
        r = m.Rectangle(width=w + 2 * Pixels, height=h + 2 * Pixels).move_to(center)
        self._shape.match_points(r)
        self._make_stencil()

    @property
    def shape(self) -> m.VMobject:
        """The base shape used in the Boolean operation."""
        return self._shape

    @shape.setter
    def shape(self, mob: m.VMobject) -> None:
        self._shape = mob
        self._make_stencil()

    @property
    def clip(self) -> m.VMobject:
        """The clipping shape."""
        return self._clip

    @clip.setter
    def clip(self, mob: m.VMobject) -> None:
        self._clip = mob
        self._make_stencil()

    @property
    def bool_op(self) -> Callable[[m.VMobject, m.VMobject], m.VMobject]:
        """The Boolean operation applied to ``shape`` and ``clip``."""
        return self._bool_op

    @bool_op.setter
    def bool_op(self, bool_op: Callable[[m.VMobject, m.VMobject], m.VMobject]) -> None:
        self._bool_op = bool_op
        self._make_stencil()

    @property
    def wrapped(self) -> m.VMobject | None:
        """Optional VMobject the stencil covers."""
        return self._wrapped

    @wrapped.setter
    def wrapped(self, mob: m.VMobject | None) -> None:
        self._wrapped = mob
        if mob is None:
            self.remove_updater(self._adapt_stencil)
        else:
            self.add_updater(self._adapt_stencil)
        self._make_stencil()

    @property
    def is_clip_static(self) -> bool:
        """Whether the clip should move with the stencil or not."""
        return self._static_clip

    @is_clip_static.setter
    def is_clip_static(self, is_static: bool) -> None:
        self._static_clip = is_static
        self.remove(self._clip) if is_static else self.add(self._clip)
