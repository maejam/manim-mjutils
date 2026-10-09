from collections.abc import ItemsView, Iterable, KeysView, Mapping, ValuesView
from types import NoneType
from typing import Any, Generic, Self, TypeVar

import manim as m

T = TypeVar("T", bound=m.Mobject)


class GroupDict(m.Mobject, Generic[T]):
    """A VDict equivalent for Mobjects.

    Allows string labels access to submobjects. Does not implement displaying the keys.

    Parameters
    ----------
    mapping_or_iterable
        The initial key value pairs to assign to the GroupDict.

    """

    def __init__(
        self,
        mapping_or_iterable: Mapping[str, T] | Iterable[tuple[str, T]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._data: dict[str, T] = {}

        if mapping_or_iterable is not None:
            for k, v in dict(mapping_or_iterable).items():
                self[k] = v

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"

    def add(  # type: ignore[override]
        self,
        mapping_or_iterable: Mapping[str, T] | Iterable[tuple[str, T]] | None = None,
    ) -> Self:
        if not isinstance(
            mapping_or_iterable, (Mapping, Iterable, NoneType)
        ) or isinstance(mapping_or_iterable, str):
            raise TypeError(
                "Only mappings or iterables can be added to "
                f"{type(self).__name__}. Got {mapping_or_iterable!r}."
            )
        if mapping_or_iterable is not None:
            for key, value in dict(mapping_or_iterable).items():
                self[key] = value
        return self

    def remove(self, key: str) -> Self:  # type: ignore[override]
        del self[key]
        return self

    def __setitem__(self, key: str, value: T) -> None:
        if key in self._data:
            old_value = self._data[key]
            super().remove(old_value)
        super().add(value)
        self._data[key] = value

    def __getitem__(self, key: str) -> T:
        if key not in self._data:
            raise KeyError(f"Key {key!r} not found in GroupDict.")
        return self._data[key]

    def __delitem__(self, key: str) -> None:
        if key not in self._data:
            raise KeyError(f"Key {key!r} not found in GroupDict.")

        value = self._data.pop(key)
        super().remove(value)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def keys(self) -> KeysView[str]:
        return self._data.keys()

    def values(self) -> ValuesView[T]:
        return self._data.values()

    def items(self) -> ItemsView[str, T]:
        return self._data.items()
