from __future__ import annotations

import contextlib
import random
from collections.abc import Callable, Iterable
from typing import Any, cast

import manim as m
import numpy as np


class LazyAnimation(m.Animation):
    """An Animation that is built at play time.

    This is useful when the set of Mobjects to animate or the animation parameters
    change dynamically between the moment the Animation is declared and the moment
    it is played.

    Parameters
    ----------
    mobject_factory
        A callable that returns the Mobject (or Group) to be animated.
    animation_factory
        A callable that takes the Mobject and any additional parameter,
        returning an Animation instance.
    **kwargs
        Standard Animation keyword arguments (passed to parent Animation class).

    Examples
    --------
    >>> from manim import *
    >>> from manim_utils import LazyAnimation


    >>> class LazyAnimationScene(Scene):
    >>>     def construct(self) -> None:
    >>>         grp = VGroup(Circle(color=RED), Dot(color=GREEN), Rectangle(color=BLUE))
    >>>         self.add(grp.arrange(RIGHT))

    >>>         def mob_factory():
    >>>             return VGroup([mob for mob in grp if mob.color == RED])

    >>>         def animation_factory(mob):
    >>>             # args can be made dynamic too
    >>>             vec = RIGHT * len([mob for mob in grp if mob.color == GREEN])
    >>>             return ApplyMethod(mob.shift, vec)

    >>>         anim = LazyAnimation(
    >>>             mobject_factory=mob_factory,
    >>>             animation_factory=animation_factory,
    >>>         )

    >>>         # even mobjects that are changed after the animation is built will be
    >>>         # included
    >>>         grp[2].set_color(RED)
    >>>         grp.add(Dot(color=GREEN) for _ in range(4))
    >>>         self.play(anim, run_time=2)

    """

    def __init__(
        self,
        mobject_factory: Callable[..., m.Mobject],
        animation_factory: Callable[..., m.Animation],
        **kwargs: Any,
    ) -> None:
        self._mobject_factory = mobject_factory
        self._animation_factory = animation_factory
        super().__init__(None, **kwargs)

    def begin(self) -> None:
        """Construct the mobject and the inner animation just before playing."""
        self._mobject = self._mobject_factory()
        # Set the mobject for the parent class
        self.mobject = self._mobject  # type: ignore[assignment]

        self._animation = self._animation_factory(self._mobject)
        self._animation.begin()

    def finish(self) -> None:
        """Delegate finish to the inner animation."""
        self._animation.finish()

    def interpolate(self, alpha: float) -> None:
        """Delegate interpolation to the inner animation."""
        self._animation.interpolate(alpha)

    def update_mobjects(self, dt: float) -> None:
        """Delegate updater calls."""
        self._animation.update_mobjects(dt)

    def get_all_families_zipped(self) -> Iterable[tuple[m.Mobject, ...]]:
        """Ensure families are zipped based on the deferred mobject."""
        return self._animation.get_all_families_zipped()


class TrackedAnimationMixin:
    """A Mixin that adds tracking abilities to animations.

    Make sure the Mixin is first in the inheritance chain.

    Examples
    --------
    >>> from manim import *
    >>> from manim_utils import TrackedAnimationMixin

    >>> class TrackedAnimationScene(Scene):
    >>>     def construct(self) -> None:
    >>>         c = Circle()

    >>>         # Animation classes can be used directly
    >>>         class TrackedTransform(TrackedAnimationMixin, Transform): ...

    >>>         tracker = ValueTracker()
    >>>         anim = TrackedTransform(
    >>>             c,
    >>>             Rectangle(),
    >>>             alpha_tracker=tracker,
    >>>             run_time=2,
    >>>         )

    >>>         status_text = always_redraw(
    >>>             lambda: Text(f"status: {anim.status}").to_edge(DOWN)
    >>>         )
    >>>         alpha_text = always_redraw(
    >>>             lambda: Text(f"tracker: {tracker.get_value():.2f}")
    >>>                 .next_to(status_text, UP)
    >>>         )
    >>>         self.add(status_text, alpha_text)
    >>>         self.wait()
    >>>         self.play(anim)

    >>>         # .animate methods can be wrapped in ApplyMethod
    >>>         class TrackedApplyMethod(TrackedAnimationMixin, ApplyMethod): ...

    >>>         # the tracker is optional
    >>>         anim2 = TrackedApplyMethod(c.shift, RIGHT * 3)
    >>>         print(anim2.status)
    'not played'

    >>>         self.play(anim2)
    >>>         print(anim2.status)
    'played'

    """

    def __init__(
        self,
        *args: Any,
        alpha_tracker: m.ValueTracker | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.status = "not played"
        self.alpha_tracker = alpha_tracker

    def begin(self) -> None:
        super().begin()  # type: ignore[misc]
        self.status = "playing"
        if self.alpha_tracker is not None:
            self.alpha_tracker.set_value(0.0)

    def finish(self) -> None:
        super().finish()  # type: ignore[misc]
        if self.alpha_tracker is not None:
            self.alpha_tracker.set_value(1.0)
        self.status = "played"

    def interpolate(self, alpha: float) -> None:
        super().interpolate(alpha)  # type: ignore[misc]
        if self.alpha_tracker is not None:
            self.alpha_tracker.set_value(alpha)


class CallbackAnimation(m.Animation):
    """A wrapper allowing a function call to be performed during an animation.

    Unlike :class:`~.ApplyMethod`, this accepts all functions, not only mobject methods
    (and mobject methods should be used with great care).

    Heavily inspired (actually completely stolen) from @nikolaj on manim discord server.

    Parameters
    ----------
    callback
        The function that will be called during the animation.
    args
        Any positional arguments to be passed when applying the method.
    delay
        Defines the delay after which the function is called. This time is relative to
        the total duration of the animation (independently of any rate functions).
            0.0 = immediately when this animation starts.
            1.0 = at the very end.
    kwargs
        Any keyword arguments passed to :class:`~.Animation`.

    """

    def __init__(
        self,
        callback: Callable[..., Any],
        *args: Any,
        delay: float = 0.0,
        **kwargs: Any,
    ) -> None:
        self._callback = callback
        self._args = args
        self._delay = delay
        self._called = False
        super().__init__(None, **kwargs)

    def begin(self) -> None:
        self._called = False
        super().begin()

    def interpolate(self, alpha: float) -> None:
        if not self._called and alpha >= self._delay:
            self._callback(*self._args)
            self._called = True


class VariableParametersAnimationMixin:
    """A Mixin that turns animation parameters into functions of progress.

    Any keyword parameter of the parent animation that is normally stored as a constant
    may instead be passed as a callable of one argument. At each frame, the callable
    receives the animation progress (``alpha``) and the resulting value is used in place
    of the constant.

    Limitation: the parent animation must read the parameter from ``self`` at
    interpolation time for the variation to have an effect. Parameters baked into the
    constructor remain frozen regardless of the callable passed.

    Note
    ----
    :class:`~.UpdateFromAlphaFunc` offers a similar mechanism at a lower level: it
    receives alpha in a callback and hands you full responsibility for the mobject's
    state each frame, discarding the parent animation's own interpolation. This mixin
    instead keeps the parent animation's machinery and only varies the parameter values
    that machinery reads. Use :class:`~.UpdateFromAlphaFunc` when the motion is bespoke;
    use this mixin when the motion already exists in an animation class and only its
    parameters need to change over time.

    Examples
    --------
    class VariableParameterDemo(Scene):
        def construct(self):
            square = Square()

            class VariableWiggle(VariableParametersAnimationMixin, Wiggle):
                pass

            self.play(
                VariableWiggle(
                    square,
                    scale_value=lambda alpha: 1 + 3 * alpha,
                    rotation_angle=lambda alpha: 0.5 * alpha,
                    n_wiggles=16,
                    run_time=5,
                )
            )
    """

    # kwargs that belong to Animation's machinery, not to the concrete animation's
    # parameters. rate_func is callable and must NOT be captured as a
    # "variable parameter".
    CONTROL_KEYS = {
        "run_time",
        "rate_func",
        "name",
        "remover",
        "introducer",
        "suspend_mobject_updating",
        "lag_ratio",
        "reverse",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._var_funcs = {}
        const = {}
        for key, value in kwargs.items():
            if callable(value) and key not in self.CONTROL_KEYS:
                self._var_funcs[key] = value
            else:
                const[key] = value
        self._alpha = 0.0
        super().__init__(*args, **const)

    def __getattribute__(self, key: str) -> Any:
        var_funcs = object.__getattribute__(self, "_var_funcs")

        if key in var_funcs:
            return var_funcs[key](object.__getattribute__(self, "_alpha"))
        return object.__getattribute__(self, key)

    def interpolate(self, alpha: float) -> None:
        self._alpha = alpha
        super().interpolate(alpha)  # type: ignore[misc]


class Shatter(m.Animation):
    """Explode a mobject into its constituent family members.

    Every visible family member becomes an independent fragment that flies radially
    outward from the mobject's center, spins, and fades.

    Parameters
    ----------
    mobject
        The mobject to shatter. Every family member carrying geometry (i.e. every
        element of ``family_members_with_points()``) becomes an independent fragment.
    dispersion_factor
        Multiplier for the maximum fragment travel distance, relative to the distance
        between the explosion center and the farthest fragment's initial position.
        Higher values throw pieces farther. Defaults to ``6.0``.
    rotation_amplitude
        Maximum rotation (in radians) any single fragment accumulates over the
        animation. Each fragment receives a random angle. Defaults to ``PI / 3``.
    fade
        Whether fragments fade to zero opacity over the course of the animation.
        If ``False``, fragments end fully visible and are removed from the scene only
        per ``remover``. Defaults to ``True``.
    seed
        Seed for the random dispersal (direction jitter and per-fragment rotation).
        ``None`` produces different randomness on every run; pass a fixed integer for
        reproducible renders. Defaults to ``None``.
    remover
        Passed to the parent :class:`~.Animation`. With the default ``True``, the
        mobject and all its family memebers are removed from the scene on cleanup.
    **kwargs
        Forwarded to the parent :class:`~.Animation` constructor (``run_time``,
        ``rate_func``, ...).

    Examples
    --------
    self.play(Shatter(mob, seed=42), rate_func=rush_from)

    """

    def __init__(
        self,
        mobject: m.Mobject,
        dispersion_factor: float = 6.0,
        rotation_amplitude: float = m.PI / 3,
        fade: bool = True,
        seed: int | None = None,
        remover: bool = True,
        **kwargs: Any,
    ) -> None:
        self.dispersion_factor = dispersion_factor
        self.rotation_amplitude = rotation_amplitude
        self.fade = fade
        self.seed = seed
        super().__init__(mobject, remover=remover, **kwargs)

    def begin(self) -> None:
        rng = random.Random(self.seed)
        center = self.mobject.get_center()

        self._pieces = cast(list[m.VMobject], self.mobject.family_members_with_points())
        if not self._pieces:
            raise ValueError("Nothing to shatter: no family member with points.")

        self._starts = [p.get_center() for p in self._pieces]
        self._directions = []
        self._angles = []
        self._opacities = []

        for piece, start in zip(self._pieces, self._starts, strict=True):
            radial = start - center
            if np.linalg.norm(radial) < 1e-6:  # piece sits at the center
                radial = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1), 0.0])
            direction = radial / np.linalg.norm(radial)
            # slight angular jitter so perfect symmetry doesn't look fake
            jitter = rng.uniform(-0.25, 0.25)
            cos, sin = np.cos(jitter), np.sin(jitter)
            direction = np.array(
                [
                    direction[0] * cos - direction[1] * sin,
                    direction[0] * sin + direction[1] * cos,
                    0.0,
                ],
            )
            self._directions.append(direction)
            self._angles.append(
                rng.uniform(-self.rotation_amplitude, self.rotation_amplitude)
            )
            self._opacities.append(
                (piece.get_fill_opacity(), piece.get_stroke_opacity())
            )

        # Total travel distance, scaled to the mobject's size
        self._travel = self.dispersion_factor * max(
            np.linalg.norm(start - center) for start in self._starts
        )

        self._prev_alpha = 0.0
        super().begin()

    def interpolate(self, alpha: float) -> None:
        super().interpolate(alpha)
        d_alpha = alpha - self._prev_alpha
        self._prev_alpha = alpha

        for piece, direction, angle, (fill_opacity, stroke_opacity) in zip(
            self._pieces,
            self._directions,
            self._angles,
            self._opacities,
            strict=True,
        ):
            piece.shift(direction * self._travel * d_alpha)
            if d_alpha != 0:
                piece.rotate(angle * d_alpha, about_point=piece.get_center())
            if self.fade:
                with contextlib.suppress(TypeError):
                    piece.set_fill(opacity=fill_opacity * (1 - alpha))
                    piece.set_stroke(opacity=stroke_opacity * (1 - alpha))
