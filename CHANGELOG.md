## v0.3.0 (2026-09-26)

### Feat

- **V**: add `V` function to narrow `Mobject` types to vectorized types
- **geometry**: add `clip_vmobject` function
- **geometry**: add `get_bounds` and `is_inside_bounds`
- **animations**: add `CallbackAnimation`
- **ui**: add `Cursor`
- **Button**: add `content_alignmnent` parameter inside button
- **mobjects**: add `VIconText`
- **mobjects**: add `GroupDict`
- **mobjects**: add `IconText`
- **ui**: add `direction` to `ButtonGroup` for auto-arrange functionality
- **ui**: add `ButtonDict`

### Fix

- **Code**: fix logic to parse code lines
- **PushButton**: make offsets relative to the button width
- **PushButton**: improve highlighting effect
- **ui**: restore opacity on `Button` templates for all submobjects
- **Stencil**: adjust stencil around wrapped mobject

### Refactor

- **Stencil**: use `get_bounds` in `_adapt_stencil`

## v0.2.0 (2026-04-25)

### Feat

- **ui**: add `ButtonGroup`
- **ui**: add `HighlightButton`
- **ui**: add `PushButton`
- **animations**: add `LazyAnimation`
- **animations**: add `TrackedAnimationMixin`
- **code**: add `Code` highlighting utility
- **Stencil**: add `Stencil` utility
