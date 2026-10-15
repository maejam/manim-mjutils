import itertools
import re
from abc import abstractmethod
from collections import defaultdict
from collections.abc import Sequence
from enum import Enum
from typing import Any, NamedTuple, Protocol, cast, runtime_checkable

import manim as m


class _Quantifier(Enum):
    ALL = "<ALL>"
    NONE = "<NONE>"

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


ALL = _Quantifier.ALL
"""Sentinel used to select all possible values."""

NONE = _Quantifier.NONE
"""Sentinel used to select no value."""

DEFAULT_TOKEN = "DEFAULT"
"""The default token.

Assigned to all character positions not explicitly covered by named token spans.
"""


class TokenSpan(NamedTuple):
    """Define a named token region in the original text.

    Tokens can overlap, nest, or be contained within other tokens.
    Character positions are line-relative (char_start=0 means first char of that line).

    Parameters
    ----------
    token_type
        Semantic classification of the token (e.g., "title", "keyword"...).
    lineno
        Line number where this token appears (0-based).
    char_start
        Inclusive start position of the token on the line (0-based).
    char_end
        Exclusive end position of the token on the line (0-based).
    """

    token_type: str
    lineno: int
    char_start: int
    char_end: int


class _TokenOccurrence(NamedTuple):
    """Represent a single token instance found during a line-level search."""

    token_type: str
    char_start: int
    char_end: int


@runtime_checkable
class Searchable(Protocol):
    """Contract for searchable manim objects."""

    def search(
        self,
        pattern: str = r".+",
        include_tokens: list[str] | tuple[str, ...] | set[str] | _Quantifier = ALL,
        exclude_tokens: list[str] | tuple[str, ...] | set[str] | _Quantifier = NONE,
        lines: int | Sequence[int] | slice | _Quantifier = ALL,
        lineno_from: int = 0,
        regex_flags: Sequence[re.RegexFlag] = (),
    ) -> m.VDict: ...

    def get_tokens(self) -> list[str]: ...

    def get_num_lines(self) -> int: ...


class SearchMixin:
    """Mixin for Text-like objects adding support for regex and semantic querying.

    Enables semantic-aware searching by combining standard regex matching with
    user-defined token annotations. Supports overlapping tokens and flexible filtering
    by token type and line number.

    Key Features
    ------------
    - Regex pattern matching with token boundary awareness
    - Multiple token types can overlap or nest
    - Automatic DEFAULT token computation for unannotated regions
    - Filtering by token inclusion/exclusion parameters
    - Support for hierarchical tokens and `*` pattern matching
    - Filtering by line numbers (int, list or slice)

    Parameters
    ----------
    *text
        Positional arguments forwarded to parent class. Included to preserve the
        Paragraph API.
    original_string
        The complete raw text content before any processing such as adding markup.
    token_spans
        Sequence of predefined token annotations. Each span defines (token_type, lineno,
        char_start, char_end). Accepts a 4-tuple or a TokenSpan instance.
        Defaults to empty sequence (whole text will be annotated as DEFAULT).
    **kwargs
        Keyword arguments forwarded to parent Text-like class.

    Attributes
    ----------
    _original_lines
        Preprocessed text split into individual lines. Must match the submobject glyphs
        1 to 1.
    _token_spans
        Complete token annotations including computed DEFAULT spans.
    _token2lines
        Mapping from token type to set of line numbers containing that type.
    _line2tokens
        Mapping from line number to sorted list of token occurrences on that line.

    See Also
    --------
    SearchableText: Ready-to-use Text subclass implementation.
    SearchableMarkup : Ready-to-use Markup subclass implementation.
    SearchableParagraph : Ready-to-use Paragraph subclass implementation.
    """

    def __init__(
        self,
        *text: str,
        original_string: str,
        token_spans: Sequence[TokenSpan | tuple[str, int, int, int]] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(*text, **kwargs)
        self._original_lines = self._process_original_string(original_string)

        spans = tuple(TokenSpan(*span) for span in token_spans)
        spans = self._process_token_spans(spans, original_string)
        default_spans = self._compute_default_token_spans(spans, self._original_lines)
        self._token_spans = spans + tuple(default_spans)

        self._token2lines = self._build_token_to_lines_map(self._token_spans)
        self._line2tokens = self._build_line_to_tokens_map(self._token_spans)

    def get_num_lines(self) -> int:
        """Return the number of lines contained in this Searchable object."""
        return len(self._original_lines)

    def search(
        self,
        pattern: str = r".+",
        include_tokens: list[str] | tuple[str, ...] | set[str] | _Quantifier = ALL,
        exclude_tokens: list[str] | tuple[str, ...] | set[str] | _Quantifier = NONE,
        lines: int | Sequence[int] | slice | _Quantifier = ALL,
        lineno_from: int = 0,
        regex_flags: Sequence[re.RegexFlag] = (),
    ) -> m.VDict:
        """Search for regex patterns with optional token and line filtering.

        Performs regex matching on the text, returning glyphs grouped by token type
        that satisfy the filter criteria. Results respect token boundaries even when
        regex matches span multiple tokens.

        Parameters
        ----------
        pattern
            Regular expression pattern to search for. Default r'.+' matches any
            character sequence.
        include_tokens
            Token types to include in results. Use ALL (default) for any token
            (including "DEFAULT"), NONE for no token. It is possible to use wildcard
            patterns anding with `*` to match all tokens beginning with the same
            characters. Useful when tokens have a hierarchical structure
            (e.g. `"Literal*"` will match all `Literal` pygments generated tokens such
            as `Literal.Number` and `Literal.String`).
        exclude_tokens
            Token types to exclude from results. Same convention as `include_tokens`.
            Takes precedence over include. Defaults to NONE (no exclusion).
        lines
            Line numbers to scan. Use int for single line, list/sequence for multiple
            lines, slice for ranges, ALL/NONE for universal selection. Defaults to ALL.
        lineno_from
            Line number offset. Defaults to `0`.
        regex_flags
            Flags passed to re.compile (e.g. `re.IGNORECASE`, `re.MULTILINE`).

        Returns
        -------
        VDict
            Dictionary mapping token types to VGroups of matched glyphs.
            Structure:
                {token_type1:
                    VGroup( # 1st match for token_type1
                        VGroup(glyphs_for_match1),
                        VGroup(glyphs_for_match2)),
                    VGroup(...) # 2nd match for token_type1
                token_type2: ...}

        Notes
        -----
        - Overlapping tokens all appear separately in results. This means that the same
          glyph could appear multiple times in different matches. But it will appear
          only once in the submobjects.
        - DEFAULT token represents unannotated text regions and can be included/excluded
          like any other token.
        """
        compiled = re.compile(pattern, *regex_flags)
        results = m.VDict()

        tokens_to_include = self._get_tokens_to_include(include_tokens, exclude_tokens)
        if not tokens_to_include:
            return results

        lines_to_scan = self._get_lines_to_scan(tokens_to_include, lines, lineno_from)
        if not lines_to_scan:
            return results

        for lineno, line in enumerate(self._original_lines):
            global_lineno = lineno + lineno_from
            if global_lineno not in lines_to_scan:
                continue

            for match in compiled.finditer(line):
                char_start = match.start()
                char_end = match.end()
                if char_start == char_end:  # empty match
                    continue

                token_matches = self._get_tokens_at(lineno, char_start, char_end)

                for token_type, token_start, token_end in token_matches:
                    if token_type not in tokens_to_include:
                        continue
                    glyphs = self._chars_to_glyphs(lineno, token_start, token_end)
                    if token_type not in results:
                        results[token_type] = m.VGroup()
                    results[token_type].add(glyphs)

        return results

    def _get_tokens_at(
        self,
        lineno: int,
        char_start: int,
        char_end: int,
    ) -> list[_TokenOccurrence]:
        """Find all token occurrences overlapping a character range on a given line."""
        if lineno not in self._line2tokens:
            return []

        tokens = self._line2tokens[lineno]
        matches: list[_TokenOccurrence] = []

        # Collect all overlapping tokens
        for token in tokens:
            if token.char_start >= char_end:
                break
            if char_start < token.char_end:
                # Return the intersected range
                actual_start = max(char_start, token.char_start)
                actual_end = min(char_end, token.char_end)
                if actual_start < actual_end:  # Valid intersection
                    matches.append(
                        _TokenOccurrence(token.token_type, actual_start, actual_end)
                    )

        return matches

    def _compute_default_token_spans(
        self,
        token_spans: tuple[TokenSpan, ...],
        original_lines: list[str],
    ) -> list[TokenSpan]:
        """Compute DEFAULT spans covering regions not explicitly annotated."""
        named_spans = [span for span in token_spans if span.token_type != DEFAULT_TOKEN]
        named_spans.sort(key=lambda t: (t.lineno, t.char_start, -t.char_end))

        default_spans: list[TokenSpan] = []
        line_lengths = [len(line) for line in original_lines]

        max_seen_line = -1
        max_seen_end = 0
        line_cursor = 0

        for span in named_spans:
            if span.lineno > max_seen_line:
                # Flush tail gap from previous line
                if max_seen_line >= 0 and max_seen_end < line_lengths[max_seen_line]:
                    default_spans.append(
                        TokenSpan(
                            DEFAULT_TOKEN,
                            max_seen_line,
                            max_seen_end,
                            line_lengths[max_seen_line],
                        )
                    )

                # Fill lines between previous and current with DEFAULT
                for line in range(max_seen_line + 1, span.lineno):
                    default_spans.append(
                        TokenSpan(DEFAULT_TOKEN, line, 0, line_lengths[line])
                    )

                # Reset per-line tracking
                max_seen_line = span.lineno
                line_cursor = 0
                max_seen_end = 0

            if span.char_start > line_cursor:
                # Gap found before this span
                default_spans.append(
                    TokenSpan(DEFAULT_TOKEN, span.lineno, line_cursor, span.char_start)
                )

            max_seen_end = max(max_seen_end, span.char_end)
            line_cursor = max_seen_end

        # Flush final tail gap on last line with spans
        if max_seen_line >= 0 and max_seen_end < line_lengths[max_seen_line]:
            default_spans.append(
                TokenSpan(
                    DEFAULT_TOKEN,
                    max_seen_line,
                    max_seen_end,
                    line_lengths[max_seen_line],
                )
            )

        # Fill remaining lines after all spans
        for line in range(max_seen_line + 1, len(original_lines)):
            default_spans.append(TokenSpan(DEFAULT_TOKEN, line, 0, line_lengths[line]))

        return default_spans

    def _build_line_to_tokens_map(
        self, token_spans: tuple[TokenSpan, ...]
    ) -> dict[int, list[_TokenOccurrence]]:
        """Build mapping from line numbers to token occurrences."""
        line2tokens: dict[int, list[_TokenOccurrence]] = {}
        for span in token_spans:
            line2tokens.setdefault(span.lineno, []).append(
                _TokenOccurrence(span.token_type, span.char_start, span.char_end)
            )

        # Sort each line for faster lookup (early break)
        for tokens in line2tokens.values():
            tokens.sort(key=lambda t: t.char_start)
        return line2tokens

    def _build_token_to_lines_map(
        self,
        token_spans: tuple[TokenSpan, ...],
    ) -> dict[str, set[int]]:
        """Build indexed mapping from token types to line numbers containing them."""
        token2lines = defaultdict(set)
        for span in token_spans:
            token2lines[span.token_type].add(span.lineno)
        return token2lines

    def _get_tokens_to_include(
        self,
        include: list[str] | tuple[str, ...] | set[str] | _Quantifier,
        exclude: list[str] | tuple[str, ...] | set[str] | _Quantifier,
    ) -> set[str]:
        """Resolve include/exclude lists to final token set for filtering."""
        all_tokens = set(self._token2lines.keys())

        if include == ALL:
            include = all_tokens
        if include == NONE:
            include = set()
        if exclude == ALL:
            exclude = all_tokens
        if exclude == NONE:
            exclude = set()

        assert not isinstance(include, _Quantifier)
        assert not isinstance(exclude, _Quantifier)

        # * pattern matching
        expanded_include = set(include)
        for pattern in include:
            if not pattern.endswith("*"):
                continue
            prefix = pattern[:-1]
            expanded_include.update(t for t in all_tokens if t.startswith(prefix))
        include = expanded_include

        expanded_exclude = set(exclude)
        for pattern in exclude:
            if not pattern.endswith("*"):
                continue
            prefix = pattern[:-1]
            expanded_exclude.update(t for t in all_tokens if t.startswith(prefix))
        exclude = expanded_exclude

        if not include:
            return set()

        if not self._token_spans:
            return set()

        tokens_to_include = include.difference(exclude)
        return tokens_to_include

    def _get_lines_to_scan(
        self,
        tokens_to_include: set[str],
        lines: int | Sequence[int] | slice | _Quantifier,
        lineno_from: int,
    ) -> set[int]:
        """Pre-compute the set of line numbers to scan during search."""
        if lines == ALL:
            lines = tuple(range(lineno_from, len(self._original_lines) + lineno_from))
        if lines == NONE:
            lines = ()
        assert not isinstance(lines, _Quantifier)

        if not lines and lines != 0:
            return set()

        lines_to_scan: set[int] = set()

        for token in tokens_to_include:
            lines_to_scan.update(self._token2lines[token])

        lines_to_scan = {lineno + lineno_from for lineno in lines_to_scan}
        for lineno in lines_to_scan.copy():
            if not self._match_lines_filter(lineno, lines, lineno_from):
                lines_to_scan.remove(lineno)

        return lines_to_scan

    def _match_lines_filter(
        self,
        lineno: int,
        lines: int | Sequence[int] | slice,
        lineno_from: int,
    ) -> bool:
        """Check if a line number satisfies the user's line filter specification."""
        if isinstance(lines, int):
            return lineno == lines
        if isinstance(lines, Sequence):
            return lineno in lines
        if isinstance(lines, slice):
            return lineno in range(
                *lines.indices(len(self._original_lines) + lineno_from)
            )
        return False

    @abstractmethod
    def _process_original_string(self, original_string: str) -> list[str]:
        """Transform the text to prepare it for glyphs lookup.

        Subclasses must implement this to convert the raw text string into
        a line-by-line representation matching the submobject glyphs.

        Parameters
        ----------
        original_string
            Raw text content.

        Returns
        -------
        List of individual lines as strings. It must match the glyphs structure or the
        mapping from character to glyph must be performed in :meth:`_chars_to_glyphs`.
        """
        raise NotImplementedError

    def _process_token_spans(
        self, spans: tuple[TokenSpan, ...], original_string: str
    ) -> tuple[TokenSpan, ...]:
        """Transform the user-provided token spans if needed."""
        return spans

    @abstractmethod
    def _chars_to_glyphs(self, lineno: int, char_start: int, char_end: int) -> m.VGroup:
        """Map character positions to glyph submobjects.

        Maps line-relative character indices to the underlying glyph submobjects.
        Essential for extracting visual representations of matches.

        Parameters
        ----------
        lineno
            Line number containing the target characters.
        char_start
            Inclusive start position on the line.
        char_end
            Exclusive end position on the line.

        Returns
        -------
        VGroup containing the glyphs for the specified character range.
        """
        raise NotImplementedError

    def get_tokens(self) -> list[str]:
        """Return unique token types available in this text object.

        Provides introspection capability to discover all semantic annotations
        including the automatically generated DEFAULT token.

        Returns
        -------
        Alphabetically sorted list of unique token types.
        Always includes DEFAULT_TOKEN if any unannotated text exists.
        """
        return sorted({*self._token2lines.keys()})


class SearchableText(SearchMixin, m.Text):
    """A Text subclass with regex and semantic querying.

    Extends Text with regex-searching capabilities and token-based filtering.

    Warning: mutating the glyphs will desynchronize them with the internal string
    representation and will render subsequent searches brittle.

    Parameters
    ----------
    text
        The text content to display and make searchable.
    token_spans
        Predefined token annotations. Each span defines (token_type, lineno,
        char_start, char_end). Accepts a 4-tuple or a TokenSpan instance.
        Defaults to empty sequence (whole text will be annotated as DEFAULT).
        Positions are relative to the beginning of each line (0-based).
    **kwargs
        Additional arguments forwarded to Text (color, size, font, etc.).

    Notes
    -----
    - Ligatures are disabled by default to maintain glyph-character correspondence.
      It is possible to enable them explicitly but an exception will be raised if
      characters and glyphs don't match.
    - Whitespace characters generate invisible Dot glyphs.
    - Defining token spans manually is possible but not very useful. If the text is
      short, searching capabilities are not very useful; if it is long, defining the
      spans manually is tedious. Parsing libraries such as `pygments` can be used to
      tokenize long texts. See :func:`manim_mjutils.code.highlight_code` for a code
      implementation based on SearchableMarkup.

    See Also
    --------
    SearchableParagraph : Paragraph-based alternative.
    SearchableMarkup : MarkupText-based alternative.
    SearchMixin : base functionality.
    manim_mjutils.code.highlight_code: function returning a highlighted and searchable
        piece of code.

    Examples
    --------
    >>> text = SearchableText("Hello World", token_spans=[("greeting", 0, 0, 5)])
    >>> result = text.search(r"Hello")
    VDict({'greeting': VGroup(VGroup of 5 submobjects)})
    """

    def __init__(
        self,
        text: str,
        token_spans: Sequence[TokenSpan] | Sequence[tuple[str, int, int, int]] = (),
        **kwargs: Any,
    ) -> None:
        # NOTE: disabling ligatures is necessary so the number of glyphs matches the
        # number of characters. It also has another consequence: invisible glyphs (Dot)
        # are generated for  whitespaces (including line breaks).
        kwargs.setdefault("disable_ligatures", True)
        super().__init__(
            text=text,
            original_string=text,
            token_spans=token_spans,
            **kwargs,
        )

    def _process_original_string(self, original_string: str) -> list[str]:
        """Split text into lines and compute line offsets for indexing.

        Processes the raw string and establishes character-to-glyph mapping
        through cumulative offset calculation.
        """
        original_lines = original_string.split("\n")
        self._line_starts = [0] + list(
            itertools.accumulate(len(line) + 1 for line in original_lines)
        )
        num_glyphs = len(self.submobjects)
        num_chars = len(original_string)
        assert num_chars == num_glyphs, (
            f"The number of glyphs in this {type(self).__name__!r} object "
            f"({num_glyphs!r}) does not match the number of characters in the original "
            f"string ({num_chars!r}). "
            f"Did you enable ligatures?"
        )
        return original_lines

    def _chars_to_glyphs(self, lineno: int, char_start: int, char_end: int) -> m.VGroup:
        """Retrieve glyphs for character range using offset-based indexing.

        Computes absolute glyph index from line number and character position
        and extracts corresponding submobjects.
        """
        offset = self._line_starts[lineno]
        return cast(m.VGroup, self[offset + char_start : offset + char_end])


class SearchableMarkup(SearchMixin, m.MarkupText):
    r"""A MarkupText subclass with regex and semantic querying.

    Extends MarkupText with regex-searching capabilities and token-based filtering.

    Warning: mutating the glyphs will desynchronize them with the internal string
    representation and will render subsequent searches brittle.

    Contrary to Text and Paragraph, MarkupText does NOT generate invisible glyphs for
    whitespace characters. To maintain a 1:1 correspondence between characters and
    glyphs, this class creates invisible characters the same way Text and Paragraph do
    it.

    Parameters
    ----------
    markup_text
        The text, including markup, to display.
    original_string
        The string from which the markup was generated. Must not include tags.
    token_spans
        Predefined token annotations. Each span defines (token_type, lineno,
        char_start, char_end). Accepts a 4-tuple or a TokenSpan instance.
        Defaults to empty sequence (whole text will be annotated as DEFAULT).
        Positions are relative to the beginning of each line (0-based).
    **kwargs
        Additional arguments forwarded to MarkupText (color, size, font, etc.).

    Notes
    -----
    - Ligatures are disabled by default to maintain glyph-character correspondence.
      It is possible to enable them explicitly but an exception will be raised if
      characters and glyphs don't match.
    - Some markup tags (e.g. `<u>`) generate extra glyphs that will disalign the
      number of characters and the number of glyphs.
    - Defining token spans manually is possible but not very useful. If the text is
      short, searching capabilities are not very useful; if it is long, defining the
      spans manually is tedious. Parsing libraries such as `pygments` can be used to
      tokenize long texts. See :func:`manim_mjutils.code.highlight_code` for a code
      implementation.

    See Also
    --------
    SearchableText : Text-based alternative.
    SearchableParagraph : Paragraph-based alternative.
    SearchMixin : base functionality.
    manim_mjutils.code.highlight_code: function returning a highlighted and searchable
        piece of code.
    """

    def __init__(
        self,
        markup_text: str,
        original_string: str,
        token_spans: Sequence[TokenSpan] | Sequence[tuple[str, int, int, int]] = (),
        **kwargs: Any,
    ) -> None:
        # NOTE: disabling ligatures is necessary so the number of glyphs matches the
        # number of characters. But, contrary to Text and Paragraph, this DOES NOT
        # generate invisible glyphs for whitespace characters.
        # TODO: to support tags generating extra glyphs, one solution would be to check
        # the numbner of points in each glyph: underlines have 20 points, when even a
        # period has 36. Further investigation needed.
        kwargs.setdefault("disable_ligatures", True)
        super().__init__(
            text=markup_text,
            original_string=original_string,
            token_spans=token_spans,
            **kwargs,
        )

    def _process_original_string(self, original_string: str) -> list[str]:
        """Split text into lines and compute glyph offsets for indexing.

        Processes the raw string and establishes character-to-glyph mapping
        through cumulative offset calculation. Injects invisible Dot glyphs
        for whitespace to achieve 1:1 character-to-glyph correspondence.
        """
        # NOTE: Injecting Dots makes MarkupText work in a similar fashion to other
        # classes. It is cleaner and probably more efficient than other solutions:
        # 1. removing spaces in original_lines and processing token spans to match
        # problems: regex broken (\w+ matches across spaces) / mismatch string-visual
        # 2. keeping spaces in original_lines and changing char_to_glyph lookup
        # problems: slower lookup per search / mismatch string-glyphs

        original_lines = original_string.split("\n")

        glyphs: list[m.VMobject] = []
        glyph_index = 0
        line_starts = [0]

        for line in original_lines:
            line_starts.append(len(line) + line_starts[-1])
            for char_index, char in enumerate(line):
                if char.isspace():
                    space = m.Dot(radius=0, fill_opacity=0, stroke_opacity=0)
                    if char_index == 0:
                        # Leading space: position at first glyph of this line
                        if glyph_index < len(self.submobjects):
                            space.move_to(self.submobjects[glyph_index].get_center())
                        else:
                            # No glyphs on this line: position at origin
                            space.move_to(self.get_center())
                    else:
                        # Middle/end space: position at previous glyph
                        space.move_to(glyphs[-1].get_center())
                    glyphs.append(space)
                else:
                    # Regular character: take next glyph from submobjects
                    if glyph_index < len(self.submobjects):
                        glyphs.append(self.submobjects[glyph_index])
                        glyph_index += 1

        self.submobjects = glyphs
        self._line_starts = line_starts

        num_glyphs = len(self.submobjects)
        num_chars = sum(len(line) for line in original_lines)
        assert num_chars == num_glyphs, (
            f"The number of glyphs in this {type(self).__name__!r} object "
            f"({num_glyphs!r}) does not match the number of characters in the "
            f"original string ({num_chars!r}). "
            f"Did you enable ligatures? Did you use markup tags that generate extra "
            "glyphs such as `<u>`?"
        )
        return original_lines

    def _chars_to_glyphs(self, lineno: int, char_start: int, char_end: int) -> m.VGroup:
        """Retrieve glyphs for character range using offset-based indexing.

        Computes absolute glyph index from line number and character position
        then extracts corresponding submobjects.
        """
        offset = self._line_starts[lineno]
        return cast(m.VGroup, self[offset + char_start : offset + char_end])


class SearchableParagraph(SearchMixin, m.Paragraph):
    """A Paragraph subclass with regex and semantic querying.

    Extends Paragraph with regex-searching capabilities and token-based filtering.

    Warning: mutating the glyphs will desynchronize them with the internal string
    representation and will render subsequent searches brittle.

    Parameters
    ----------
    *text
        The text lines to display and make searchable.
    token_spans
        Predefined token annotations. Each span defines (token_type, lineno,
        char_start, char_end). Accepts a 4-tuple or a TokenSpan instance.
        Defaults to empty sequence (whole text will be annotated as DEFAULT).
        Positions are relative to the beginning of each line (0-based).
    **kwargs
        Additional arguments forwarded to Paragraph (color, size, font, etc.).

    Notes
    -----
    - Ligatures are disabled by default to maintain glyph-character correspondence.
      It is possible to enable them explicitly but an exception will be raised if
      characters and glyphs don't match.
    - Whitespace characters generate invisible Dot glyphs.
    - Defining token spans manually is possible but not very useful. If the text is
      short, searching capabilities are not very useful; if it is long, defining the
      spans manually is tedious. Parsing libraries such as `pygments` can be used to
      tokenize long texts. See :func:`manim_mjutils.code.highlight_code` for a code
      implementation based on SearchableMarkup.

    See Also
    --------
    SearchableText : Text-based alternative.
    SearchableMarkup : MarkupText-based alternative.
    SearchMixin : base functionality.
    manim_mjutils.code.highlight_code: function returning a highlighted and searchable
        piece of code.

    """

    def __init__(
        self,
        *text: str,
        token_spans: Sequence[TokenSpan] | Sequence[tuple[str, int, int, int]] = (),
        **kwargs: Any,
    ) -> None:
        # NOTE: disabling ligatures is necessary so the number of glyphs matches the
        # number of characters. It also has another consequence: invisible glyphs (Dot)
        # are generated for  whitespaces (including line breaks)
        kwargs.setdefault("disable_ligatures", True)
        super().__init__(
            *text,
            original_string="\n".join(list(text)),
            token_spans=token_spans,
            **kwargs,
        )

    def _process_original_string(self, original_string: str) -> list[str]:
        """Split text into lines.

        Ensures each visual line has matching character/glyph counts for
        accurate position-based glyph retrieval.
        """
        res = original_string.split("\n")
        num_chars_per_line = [len(line) for line in res]
        num_glyphs_per_line = [len(line.submobjects) for line in self.submobjects]
        assert num_chars_per_line == num_glyphs_per_line, (
            f"The number of glyphs per line in this {type(self).__name__!r} object "
            f"({num_glyphs_per_line!r}) does not match the number of characters in the "
            f"original string ({num_chars_per_line!r}). "
            f"Did you enable ligatures?"
        )
        return res

    def _chars_to_glyphs(self, lineno: int, char_start: int, char_end: int) -> m.VGroup:
        """Retrieve glyphs for character range using nested indexing.

        Accesses submobjects via line-first indexing (Paragraph structure).
        """
        return cast(m.VGroup, self[lineno][char_start:char_end])


class SearchableVGroup(m.VGroup):
    r"""Container for multiple Searchable objects with unified search capability.

    Aggregates search results from all Searchable submobjects while maintaining
    global line numbering across the group. Supports recursive nesting
    (SearchableVGroup containing SearchableVGroup...). Can contain any kind of
    VMobjects (non-searchable ones will simply be ignored during serach operations).
    This makes it possible to use it instead of a VGroup with zero overhead.

    Parameters
    ----------
    *vmobjects
        One or more VMobjects to add to the group. Can include Searchable objects
        (SearchableText, SearchableMarkup, SearchableParagraph) and nested
        SearchableVGroups. Non-searchable objects are ignored by search().
    **kwargs
        Additional keyword arguments forwarded to VGroup.__init__.

    See Also
    --------
    SearchableText : Text subclass with regex and semantic querying.
    SearchableMarkup : MarkupText subclass with regex and semantic querying.
    SearchableParagraph : Paragraph subclass with regex and semantic querying.
    SearchMixin : Base mixin providing search functionality to Text-like objects.
    manim_mjutils.code.highlight_code: function returning a highlighted and searchable
        piece of code as a SearchableVGroup when `split_lines` is True.

    Examples
    --------
    >>> from manim_mjutils import SearchableText, SearchableVGroup
    >>>
    >>> # Create multiple searchable text objects
    >>> line1 = SearchableText("Hello World", token_spans=[("greeting", 0, 0, 5)])
    >>> line2 = SearchableText("Foo Bar Baz", token_spans=[("word", 0, 0, 3)])
    >>>
    >>> # Combine into searchable container
    >>> group = SearchableVGroup(line1, line2)
    >>>
    >>> # Search with global line indexing
    >>> result = group.search(include_tokens=["DEFAULT"], lines=1)
    >>> result
    VDict({'DEFAULT': VGroup(VGroup of 3 submobjects, VGroup of 3 submobjects)})

    """

    def get_num_lines(self) -> int:
        """Return the number of lines contained in this Searchable object.

        Only Searchable submobjects, including SearchableVGroups, are considered.
        """
        return sum(
            mob.num_lines() for mob in self.submobjects if isinstance(mob, Searchable)
        )

    def search(
        self,
        pattern: str = r".+",
        include_tokens: list[str] | tuple[str, ...] | set[str] | _Quantifier = ALL,
        exclude_tokens: list[str] | tuple[str, ...] | set[str] | _Quantifier = NONE,
        lines: int | Sequence[int] | slice | _Quantifier = ALL,
        lineno_from: int = 0,
        regex_flags: Sequence[re.RegexFlag] = (),
    ) -> m.VDict:
        """Search for regex patterns with optional token and line filtering.

        Performs regex matching across all Searchable submobjects using global line
        numbering. Token results are consolidated by type and returned as a VDict
        mapping token names to VGroups of matched glyphs with a structure identical
        to other Searchable mobjects.

        Parameters
        ----------
        pattern
            Regular expression pattern to search for. Default r'.+' matches any
            character sequence.
        include_tokens
            Token types to include in results. Use ALL (default) for any token
            (including "DEFAULT"), NONE for no token. It is possible to use wildcard
            patterns anding with `*` to match all tokens beginning with the same
            characters. Useful when tokens have a hierarchical structure
            (e.g. `"Literal*"` will match all `Literal` pygments generated tokens such
            as `Literal.Number` and `Literal.String`).
        exclude_tokens
            Token types to exclude from results. Same convention as `include_tokens`.
            Takes precedence over include. Defaults to NONE (no exclusion).
        lines
            Line numbers to scan. Use int for single line, list/sequence for multiple
            lines, slice for ranges, ALL/NONE for universal selection. Defaults to ALL.
        lineno_from
            Line number offset. Defaults to `0`.
        regex_flags
            Flags passed to re.compile (e.g. `re.IGNORECASE`, `re.MULTILINE`).

        Returns
        -------
        m.VDict
            Dictionary mapping token types to VGroups of matched glyphs.
            Structure:
                {token_type1:
                    VGroup( # 1st match for token_type1
                        VGroup(glyphs_for_match1),
                        VGroup(glyphs_for_match2)),
                    VGroup(...) # 2nd match for token_type1
                token_type2: ...}

        Notes
        -----
        - Non-Searchable submobjects are skipped without error.
        - Nested SearchableVGroups work correctly; lineno_from accumulates sibling line
          counts automatically.
        - Overlapping tokens all appear separately in results. This means that the same
          glyph could appear multiple times in different matches. But it will appear
          only once in the submobjects.
        - DEFAULT token represents unannotated text regions and can be included/excluded
          like any other token.
        """
        results = m.VDict()

        for mob in self.submobjects:
            if isinstance(mob, Searchable):
                res = mob.search(
                    pattern,
                    include_tokens,
                    exclude_tokens,
                    lines,
                    lineno_from,
                    regex_flags,
                )

                lineno_from += mob.get_num_lines()

                # Consolidate results into a single VDict
                if res.submobjects:
                    for key, matches_vg in res.submob_dict.items():
                        if key not in results:
                            results[key] = m.VGroup()
                        for match in matches_vg:
                            results[key].add(match)

        return results

    def get_tokens(self) -> list[str]:
        """Return unique token types available in all Searchable submobjects.

        Provides introspection capability to discover all semantic annotations
        across the entire group.

        Returns
        -------
        list[str]
            Alphabetically sorted list of unique token types. Always includes
            'DEFAULT' if any unannotated text exists.
        """
        tokens = set()
        for mob in self.submobjects:
            if isinstance(mob, Searchable):
                tokens.update(mob.get_tokens())
        return sorted(tokens)
