import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar, overload

import pygments
from manim import ManimColor, MarkupText
from pygments.formatter import Formatter
from pygments.formatters import PangoMarkupFormatter
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name, guess_lexer, guess_lexer_for_filename
from pygments.styles import get_all_styles
from pygments.util import html_escape

T = TypeVar("T")


@dataclass
class HighlightedCode(Generic[T]):
    """Encapsulate the highlited code and the background color."""

    lines: T
    bgcolor: ManimColor


class ManimPangoFomatter(PangoMarkupFormatter[str]):
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
    code_file: Path | str | None = ...,
    code_string: str | None = ...,
    language: str | None = ...,
    style: str = ...,
    tab_width: int = ...,
    font: str = ...,
    font_size: int = ...,
    dedent: bool = ...,
    *,
    as_list: Literal[True] = ...,
) -> HighlightedCode[list[MarkupText]]: ...


@overload
def highlight_code(
    code_file: Path | str | None = ...,
    code_string: str | None = ...,
    language: str | None = ...,
    style: str = ...,
    tab_width: int = ...,
    font: str = ...,
    font_size: int = ...,
    dedent: bool = ...,
    *,
    as_list: Literal[False] = ...,
) -> HighlightedCode[MarkupText]: ...


def highlight_code(
    code_file: Path | str | None = None,
    code_string: str | None = None,
    language: str | None = None,
    style: str = "vim",
    tab_width: int = 4,
    font: str = "Monospace",
    font_size: int = 22,
    dedent: bool = True,
    *,
    as_list: bool = True,
) -> HighlightedCode[list[MarkupText]] | HighlightedCode[MarkupText]:
    """Highlight a piece of code with the pygments library.

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
    as_list
        If `True`, a list of MarkupText objects is generated, one per line of code.
        If `False`, a single MarkupText object is generated.

    Returns
    -------
    An instance of :class:`.HighlightedCode`. This instance has 2 attributes:
    * `lines`: either a list of individual code lines as :class:`manim.MarkupText`
    (if `as_list` is `True`) or a single `MarkupText` object (if `as_list` is `False`).
    * `bgcolor`: the background color as defined by the chosen style.

    Examples
    --------
    >>> import manim as m

    >>> from manim_utils.code import highlight_code

    >>> class CodeHighlighting(m.Scene):
    ...     def construct(self):
    ...         code = highlight_code(
    ...             code_string='''
    ...         def func():
    ...             pass
    ...         ''',
    ...             language="python",
    ...             style="gruvbox-light",
    ...         )
    ...         code_group = m.VGroup(code.lines).arrange(m.DOWN, aligned_edge=m.LEFT)
    ...         self.add(
    ...             m.SurroundingRectangle(code_group).set_fill(
    ...                 code.bgcolor, opacity=1
    ...             ),
    ...             code_group,
    ...         )
    ...         print(code.bgcolor, type(code.bgcolor))
    #FBF1C7 <class 'manim.utils.color.core.ManimColor'>

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

    formatter = ManimPangoFomatter(style=style, font=font)

    if as_list:
        highlighted_lines = _highlight_as_pango_lines(code_string, lexer, formatter)

        def prepare_line(line: str) -> MarkupText:
            # NOTE: add leading dot to preserve indentation when building the MarkupText
            # Needs to be done after highlighting to not mess with the lexer
            dotted = "." + line
            markup = MarkupText(dotted, font_size=font_size)
            markup[0].set_opacity(0)
            return markup

        highlighted_code_lines = map(prepare_line, highlighted_lines)
        return HighlightedCode[list[MarkupText]](
            list(highlighted_code_lines),
            ManimColor(formatter.style.background_color),
        )
    else:
        highlighted = pygments.highlight(code_string, lexer, formatter)
        markup = MarkupText(highlighted)
        return HighlightedCode[MarkupText](
            markup, ManimColor(formatter.style.background_color)
        )


def _highlight_as_pango_lines(
    code: str, lexer: Lexer, formatter: Formatter[str]
) -> list[str]:
    # Get all tokens
    tokens = list(lexer.get_tokens(code))

    # Group tokens by line
    lines = []
    current_line_tokens = []
    for tok_type, tok_text in tokens:
        for token in tok_text.splitlines(keepends=True):
            if token.endswith("\n"):
                current_line_tokens.append((tok_type, token[:-1]))
                lines.append(current_line_tokens)
                current_line_tokens = []
            else:
                current_line_tokens.append((tok_type, token))

    if current_line_tokens:
        lines.append(current_line_tokens)

    # Format each line
    highlighted_lines = []
    for token_line in lines:
        markup_line = ""
        markup_line += pygments.format(token_line, formatter)
        highlighted_lines.append(markup_line)

    return highlighted_lines


def get_styles_list() -> list[str]:
    """Return the list of available pygments styles."""
    return list(get_all_styles())
