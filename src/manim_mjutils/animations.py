from collections.abc import Callable, Iterable
from typing import Any

import manim as m


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
