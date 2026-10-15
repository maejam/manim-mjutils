import textwrap
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Literal, NamedTuple, TypeVar, overload

import pygments
from manim import ManimColor
from pygments.formatter import Formatter
from pygments.formatters import PangoMarkupFormatter
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name, guess_lexer, guess_lexer_for_filename
from pygments.styles import get_all_styles
from pygments.token import _TokenType
from pygments.util import html_escape

from manim_mjutils.mobject.text import SearchableMarkup, SearchableVGroup, TokenSpan

T = TypeVar("T")


@dataclass
class HighlightedCode(Generic[T]):
    """Encapsulate the highlighted code and the background color."""

    lines: T
    bgcolor: ManimColor


class _LineToken(NamedTuple):
    """A pygments token confined to a single line.

    ``char_start`` is relative to the beginning of the line, and ``value`` never
    contains a newline.
    """

    token_type: _TokenType
    char_start: int
    value: str


def _tokenize_by_line(code: str, lexer: Lexer) -> list[list[_LineToken]]:
    """Tokenize ``code`` and group the tokens by line.

    Tokens spanning several lines are split at newlines. The newline characters
    themselves are dropped from the values. Offsets are relative to the start of
    their line.
    """
    lines: list[list[_LineToken]] = [[]]
    line_start = 0

    for abs_start, token_type, value in lexer.get_tokens_unprocessed(code):
        for chunk in value.splitlines(keepends=True):
            ends_line = chunk.endswith("\n")
            if ends_line:
                chunk = chunk[:-1]
            lines[-1].append(_LineToken(token_type, abs_start - line_start, chunk))
            abs_start += len(chunk) + (1 if ends_line else 0)
            if ends_line:
                lines.append([])
                line_start = abs_start

    if len(lines) > 1 and not lines[-1]:
        # pygments guarantees a trailing newline (option ensurenl), so an
        # empty trailing line is an artifact of that, not part of the code
        lines.pop()

    return lines


def _format_lines(
    lines: list[list[_LineToken]], formatter: Formatter[str]
) -> list[str]:
    """Render each line's tokens to pango markup."""
    return [
        pygments.format([(token.token_type, token.value) for token in line], formatter)
        for line in lines
    ]


def _spans_for_line(
    line: list[_LineToken], lineno: int, char_offset: int
) -> Iterator[TokenSpan]:
    """Yield spans for the given line, renumbered as local line 0."""
    for token in line:
        if not token.value or token.value.isspace():
            continue
        yield TokenSpan(
            token_type=str(token.token_type)[6:],  # remove "Token."
            lineno=lineno,
            char_start=token.char_start + char_offset,
            char_end=token.char_start + len(token.value) + char_offset,
        )


class ManimPangoFormatter(PangoMarkupFormatter[str]):
    def __init__(self, **options: Any) -> None:
        Formatter.__init__(self, **options)

        self.styles = {}

        font = html_escape(options.get("font", "Monospace"))

        for token, style in self.style:
            # NOTE: Define a fallback color otherwise some styles are not rendered
            # properly (e.g. `algol`)
            color = style.get("color", "000000") if style["color"] else "000000"

            start = f'<span fgcolor="#{color}" font="{font}">'
            end = "</span>"

            if style["bold"]:
                start += "<b>"
                end = "</b>" + end
            if style["italic"]:
                start += "<i>"
                end = "</i>" + end
            if style["underline"]:
                start += "<u>"
                end = "</u>" + end
            self.styles[token] = (start, end)


@overload
def highlight_code(
    *,
    code_file: Path | str | None = ...,
    code_string: str | None = ...,
    language: str | None = ...,
    style: str = ...,
    tab_width: int = ...,
    font: str = ...,
    font_size: int = ...,
    dedent: bool = ...,
    split_lines: Literal[True],
) -> HighlightedCode[SearchableVGroup]: ...


@overload
def highlight_code(
    *,
    code_file: Path | str | None = ...,
    code_string: str | None = ...,
    language: str | None = ...,
    style: str = ...,
    tab_width: int = ...,
    font: str = ...,
    font_size: int = ...,
    dedent: bool = ...,
    split_lines: Literal[False],
) -> HighlightedCode[SearchableMarkup]: ...


@overload
def highlight_code(
    *,
    code_file: Path | str | None = ...,
    code_string: str | None = ...,
    language: str | None = ...,
    style: str = ...,
    tab_width: int = ...,
    font: str = ...,
    font_size: int = ...,
    dedent: bool = ...,
) -> HighlightedCode[SearchableMarkup]: ...


def highlight_code(
    *,
    code_file: Path | str | None = None,
    code_string: str | None = None,
    language: str | None = None,
    style: str = "vim",
    tab_width: int = 4,
    font: str = "Monospace",
    font_size: int = 22,
    dedent: bool = True,
    split_lines: bool = False,
) -> HighlightedCode[SearchableVGroup] | HighlightedCode[SearchableMarkup]:
    """Highlight code with the pygments library and make the result searchable.

    Parameters
    ----------
    code_file
        The path to the code file to highlight.
    code_string
        Alternatively, the code string to highlight.
    language
        The programming language of the code. If not specified, it will be
        guessed from the file extension or the code itself.
    style
        The style to use for the code highlighting. Defaults to ``"vim"``.
        A list of all available styles can be obtained by calling
        :func:`.get_styles_list`.
    tab_width
        The width of a tab character in spaces. Defaults to 4.
    font
        The font to be used.
    font_size
        The size of the font to be used
    dedent
        Whether the code should be dedented or not. Defaults to True.
    split_lines
        If `True`, a SearchableVGroup of SearchableMarkup objects is generated,
        one per line of code.
        If `False` (default), a single `SearchableMarkup` object is generated.

    Returns
    -------
    An instance of :class:`.HighlightedCode`. This instance has 2 attributes:
    * `lines`: either a SearchableVGroup of individual code lines as
    :class:`SearchableMarkup` (if `split_lines` is `True`) or a single
    `SearchableMarkup` object (if `split_lines` is `False`).
    * `bgcolor`: the background color as defined by the chosen style.

    Note on performance
    --------------------
    MarkupText is the bottleneck here and is inherently slow. Multi-threading and batch
    processing (building one big MarkupText instead of one per line) actually degrade
    performance. Even Text or Paragraph take only 25% less time to render 120 lines
    with no highlighting (they scale much better though but who needs to animate
    thousands of lines??). Code is 120% slower on 60 lines and breaks with 120.

    """
    lexer = get_lexer_by_name(language) if language is not None else None
    if code_file is not None:
        code_file = Path(code_file)
        code_string = code_file.read_text(encoding="utf-8")
        if lexer is None:
            lexer = guess_lexer_for_filename(code_file.name, code_string)
    elif code_string is not None:
        if lexer is None:
            lexer = guess_lexer(code_string)
    else:
        raise ValueError("Either a code file or a code string must be specified.")

    code_string = code_string.expandtabs(tabsize=tab_width).lstrip("\n")
    if dedent:
        code_string = textwrap.dedent(code_string)

    formatter = ManimPangoFormatter(style=style, font=font)

    tokenized_lines = _tokenize_by_line(code_string, lexer)

    if not code_string:
        tokenized_lines = []

    if split_lines:
        highlighted_lines = _format_lines(tokenized_lines, formatter)

        # Pop the ensurenl artifact if present
        if len(tokenized_lines) > 1 and not tokenized_lines[-1]:
            tokenized_lines.pop()

        def prepare_line(
            original: str, markup_string: str, tokenized_line: list[_LineToken]
        ) -> SearchableMarkup:
            # NOTE: add leading dot to preserve indentation when building the MarkupText
            # Needs to be done after highlighting to not mess with the lexer
            markup_string = "." + markup_string
            original = "." + original
            result = SearchableMarkup(
                markup_text=markup_string,
                original_string=original,
                token_spans=list(
                    _spans_for_line(tokenized_line, lineno=0, char_offset=1)
                ),
                font_size=font_size,
            )
            result[0].set_opacity(0)
            return result

        if not code_string:
            searchable_markups = [prepare_line("", "", [])]
        else:
            searchable_markups = [
                prepare_line(orig, highlighted, tokenized)
                for orig, highlighted, tokenized in zip(
                    code_string.splitlines(),
                    highlighted_lines,
                    tokenized_lines,
                    strict=True,
                )
            ]

        return HighlightedCode[SearchableVGroup](
            SearchableVGroup(searchable_markups),
            ManimColor(formatter.style.background_color),
        )

    else:
        markup_strings = "\n".join(_format_lines(tokenized_lines, formatter))
        token_spans = [
            span
            for lineno, tokenized_line in enumerate(tokenized_lines)
            for span in _spans_for_line(tokenized_line, lineno=lineno, char_offset=0)
        ]

        return HighlightedCode[SearchableMarkup](
            SearchableMarkup(
                markup_strings,
                code_string,
                token_spans=token_spans,
                font_size=font_size,
            ),
            ManimColor(formatter.style.background_color),
        )


def get_styles_list() -> list[str]:
    """Return the list of available pygments styles."""
    return list(get_all_styles())
