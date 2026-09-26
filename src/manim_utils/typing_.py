from typing import Any, cast, overload

import manim as m

from manim_utils.mobjects import GroupDict


@overload
def V(mob: GroupDict[Any] | m.VDict, raise_: bool = True) -> m.VDict: ...
@overload
def V(mob: m.Group | m.VGroup, raise_: bool = True) -> m.VGroup: ...
@overload
def V(mob: m.Mobject | m.VMobject, raise_: bool = True) -> m.VMobject: ...


def V(mob: m.Mobject, raise_: bool = True) -> m.VMobject:
    """Narrow Manim objects to their vectorized types.

    Useful to inform type checkers (and optionally perform a runtime check) that a
    variable typed as a union (e.g. `Group | VGroup`) is actually the vectorized type
    (e.g. `VGroup`).

    input mob           What type checkers will see
    -----------------------------------------------
    GroupDict           VDict
    VDict               VDict
    GroupDict|VDict     VDict
    Group               VGroup
    VGroup              VGroup
    Group|VGroup        VGroup
    Mobject             VMobject
    VMobject            VMobject
    Mobject|VMobject    VMobject
    3                   <error>
    "string"            <error>
    Group|VDict         Mixed unions are unpredictable


    Parammeters
    -----------
    mob
        The mobject whose type to narrow.
    raise_
        If ``True`` a runtime assertion will be performed.

    Returns
    -------
    The input mobject unchanged as far as runtime is concerned.
    """
    if raise_:
        assert isinstance(mob, m.VMobject), f"{mob} is not a vectorized object."
    if isinstance(mob, m.Group):
        return cast(m.VGroup, mob)
    if isinstance(mob, GroupDict):
        return cast(m.VDict, mob)
    if isinstance(mob, m.Mobject):
        return cast(m.VMobject, mob)
    return mob
