import re

import manim as m
import numpy as np
import pytest

from manim_mjutils import SearchableText
from manim_mjutils.mobject.text import (
    ALL,
    NONE,
    SearchableMarkup,
    SearchableParagraph,
    SearchableVGroup,
)

# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
oneline = "This is a oneline string."
multiline = """This is a multiline string.
This is the second line.
And the third and last one."""


@pytest.fixture
def oneline_text():
    return SearchableText(
        oneline,
        token_spans=[
            ("pronoun", 0, 0, 4),  # this
            ("verb", 0, 5, 7),  # is
            ("article", 0, 8, 9),  # a
            ("adjective", 0, 10, 13),  # one (mid-word)
            # "line" does not get a token assigned => DEFAULT
            ("noun", 0, 18, 24),  # string
            ("punctuation", 0, 24, 25),  # .
        ],
        color=m.BLUE,
    )


@pytest.fixture
def multiline_text():
    return SearchableText(
        multiline,
        token_spans=[
            ("line0", 0, 0, 27),
            ("line1", 1, 0, 24),
            ("line2", 2, 0, 27),
            # tokens contained within previous ones
            ("pronoun", 0, 0, 4),  # This line 1
            ("pronoun", 1, 0, 4),  # This line 2
            ("verb", 0, 5, 7),  # is line 1
            ("verb", 1, 5, 7),  # is line 2
        ],
    )


@pytest.fixture
def paragraph():
    return SearchableParagraph(
        *multiline.splitlines(),
        token_spans=[
            ("line1", 0, 0, 27),
            ("line2", 1, 0, 24),
            ("line3", 2, 0, 27),
            # tokens contained within previous ones
            ("pronoun", 0, 0, 4),  # This line 1
            ("pronoun", 1, 0, 4),  # This line 2
            ("verb", 0, 5, 7),  # is line 1
            ("verb", 1, 5, 7),  # is line 2
        ],
        height=8,
    )


@pytest.fixture
def markup():
    return SearchableMarkup(
        multiline,
        multiline,
        token_spans=[
            ("line1", 0, 0, 27),
            ("line2", 1, 0, 24),
            ("line3", 2, 0, 27),
            # tokens contained within previous ones
            ("pronoun", 0, 0, 4),  # This line 1
            ("pronoun", 1, 0, 4),  # This line 2
            ("verb", 0, 5, 7),  # is line 1
            ("verb", 1, 5, 7),  # is line 2
        ],
        height=8,
    )


class Inspector:
    """Inspect the result of a call to .search

    result = VDict(
                "token1": # token_type
                    VGroup( # all matches for that token
                        VGroup(g1, g2), # all glyphs for match1
                        VGroup(g2, g3), # all glyphs for match2
                    ),
                "token2": ...
    """

    def __init__(self, result: m.VDict):
        self._result = result

    def tokens(self) -> list[str]:
        return list(self._result.submob_dict.keys())

    def matches(self, token: str | None = None) -> list[m.VGroup]:
        if token is not None:
            return list(self._result[token])
        res = []
        for token in self.tokens():
            res.extend(self._result[token])
        return res

    def glyphs(
        self, token: str | None = None, match: int | None = None
    ) -> list[m.VMobject]:
        matches = self.matches(token)
        if match is not None:
            return matches[match].submobjects
        res = []
        for mm in matches:
            res.extend(mm.submobjects)
        return res


# ----------------------------------------------------------------------
# Basic Search Tests
# ----------------------------------------------------------------------
def test_basic_search(oneline_text):
    """Basic regex search should return matching glyphs."""
    result = oneline_text.search(r"is")
    insp = Inspector(result)
    assert len(insp.matches()) == 2
    assert isinstance(result, m.VDict)
    assert all(isinstance(match, m.VGroup) for match in result)
    assert len(insp.glyphs(match=0)) == 2
    assert insp.glyphs(match=0) == oneline_text[2:4].submobjects


def test_token_bondaries(oneline_text):
    """Test that tokens are defined [inclusive, exclusive[."""
    result = oneline_text.search(r"one")
    insp = Inspector(result)
    assert len(insp.matches()) == 1
    assert isinstance(result, m.VDict)
    assert all(isinstance(match, m.VGroup) for match in result)
    assert len(insp.glyphs(match=0)) == 3
    assert insp.glyphs(match=0) == oneline_text[10:13].submobjects


def test_search_with_no_match(oneline_text):
    """Search for non-existent pattern returns empty VGroup."""
    result = oneline_text.search(r"xyz123")
    assert len(result.submobjects) == 0


def test_default_pattern(oneline_text):
    """Default pattern '.+' matches one character per match."""
    result = oneline_text.search()  # Uses default r".+"
    insp = Inspector(result)
    assert len(insp.tokens()) == 7  # 6 defined + DEFAULT
    assert len(insp.matches()) == 10  # 6 defined + 4 DEFAULT (3 spaces and "line ")
    assert len(insp.glyphs()) == len(oneline_text.submobjects)


@pytest.mark.parametrize(
    ("pattern", "expected_num_matches", "expected_token_types"),
    [
        (r"T", 1, {"pronoun"}),  # first char
        (r"\.", 1, {"punctuation"}),  # last char
        (r"i", 4, {"pronoun", "verb", "DEFAULT", "noun"}),
        (r"This", 1, {"pronoun"}),
        (r"string.", 2, {"noun", "punctuation"}),
        (
            r"a oneline string",
            5,
            {"article", "DEFAULT", "adjective", "noun"},
        ),  # spans multiple tokens - DEFAULT*2 (space+"line ")
        (r"xyz123", 0, set()),  # no matches
    ],
)
def test_basic_regex_search(
    oneline_text, pattern, expected_num_matches, expected_token_types
):
    """Test basic regex patterns with various expected outcomes."""
    result = oneline_text.search(pattern)
    insp = Inspector(result)

    total_matches = len(insp.matches())
    assert total_matches == expected_num_matches
    assert set(insp.tokens()) == expected_token_types


@pytest.mark.parametrize(
    ("include_tokens", "expected_match_count"),
    [
        (["pronoun"], 1),  # Only "This" at start
        (["article"], 1),  # Only "a"
        (["noun"], 1),  # Only "string"
        (["pronoun", "verb"], 2),  # Both pronouns and verbs
        (["DEFAULT"], 4),  # All untokenized spans
        ([], 0),  # Empty include list
    ],
)
def test_include_tokens_filter(
    oneline_text, include_tokens: list[str], expected_match_count: int
):
    """Test filtering results by include_tokens parameter."""
    result = oneline_text.search(include_tokens=include_tokens)
    insp = Inspector(result)
    assert set(insp.tokens()) == set(include_tokens)
    assert len(insp.matches()) == expected_match_count


@pytest.mark.parametrize(
    ("pattern", "exclude_tokens", "expected_count"),
    [
        (r"i", [], 4),  # "i" in This/is/line/string
        (r"i", ["pronoun"], 3),  # "i" in is/line/string
        (r"i", ["pronoun", "verb"], 2),  # "i" in line/string
        (r"i", ["pronoun", "verb", "DEFAULT"], 1),  # "i" in string
        (r"i", ["pronoun", "verb", "DEFAULT", "noun"], 0),
        (r"i", ["pronoun", "verb", "DEFAULT", "noun", "adjective"], 0),
        (r"i", ALL, 0),
    ],
)
def test_exclude_tokens_filter(oneline_text, pattern, exclude_tokens, expected_count):
    """Test filtering results by exclude_tokens parameter."""
    result = oneline_text.search(pattern, exclude_tokens=exclude_tokens)
    insp = Inspector(result)
    assert len(insp.matches()) == expected_count


@pytest.mark.parametrize(
    ("lines", "expected_lines_scanned"),
    [
        (0, {0}),  # Single line as int
        ([0, 1], {0, 1}),  # List of lines
        (slice(1, 3), {1, 2}),  # Slice object
        (ALL, {0, 1, 2}),  # all lines
        (NONE, set()),  # NONE quantifier
        ([], set()),  # empty
    ],
)
def test_lines_filter(multiline_text, lines, expected_lines_scanned):
    """Test line filtering with various line specifications."""
    result = multiline_text.search(lines=lines)
    insp = Inspector(result)
    not_scanned = {0, 1, 2}.difference(expected_lines_scanned)
    for line in expected_lines_scanned:
        assert f"line{line}" in insp.tokens()
    for line in not_scanned:
        assert f"line{line}" not in insp.tokens()


@pytest.mark.parametrize(
    ("pattern", "include_tokens", "exclude_tokens", "expected_matches"),
    [
        (r"one", ["adjective"], ["noun"], 1),  # "one" - excluded is not in included
        (r"line", ["DEFAULT"], ["DEFAULT"], 0),  # excluded precedence
        (
            r"is",
            ["pronoun", "verb"],
            ["pronoun"],
            1,
        ),
    ],
)
def test_combined_filters(
    oneline_text, pattern, include_tokens, exclude_tokens, expected_matches
):
    """Test combining include_tokens and exclude_tokens filters."""
    result = oneline_text.search(
        pattern, include_tokens=include_tokens, exclude_tokens=exclude_tokens
    )
    insp = Inspector(result)
    assert len(insp.matches()) == expected_matches


def test_multiple_occurrences_same_token_type(multiline_text):
    """Verify all occurrences of a token type are returned, not just last one."""
    result = multiline_text.search(include_tokens=["verb"])
    insp = Inspector(result)
    assert len(insp.matches()) == 2
    assert insp.tokens() == ["verb"]


def test_overlapping_tokens(multiline_text):
    """Test that overlapping tokens are all captured correctly."""
    result = multiline_text.search(r"This", lines=0)
    insp = Inspector(result)
    assert insp.tokens() == ["line0", "pronoun"]
    assert len(insp.matches()) == 2


def test_paragraph_multiline(paragraph):
    """Test SearchableParagraph with multiline content."""
    result = paragraph.search(r"This", include_tokens=["pronoun"])
    insp = Inspector(result)
    assert len(insp.matches()) == 2
    assert insp.tokens() == ["pronoun"]


def test_empty_match_excluded(oneline_text):
    """Empty regex matches should be filtered out."""
    result = oneline_text.search(r"")
    assert len(result.submobjects) == 0


def test_get_tokens_method(oneline_text):
    """Test get_tokens returns all available token types."""
    tokens = oneline_text.get_tokens()
    assert isinstance(tokens, list)
    assert "pronoun" in tokens
    assert "DEFAULT" in tokens
    assert set(tokens) == {
        "pronoun",
        "DEFAULT",
        "noun",
        "adjective",
        "punctuation",
        "article",
        "verb",
    }


@pytest.mark.parametrize(
    ("flags", "expected_matches"),
    [
        ([re.IGNORECASE], 3),  # Case insensitive finds "Thi(s)" and "thi(rd)" patterns
        ([], 2),  # Case sensitive only finds "Thi(s)"
    ],
)
def test_regex_flags(multiline_text, flags, expected_matches):
    """Test regex flag handling."""
    result = multiline_text.search(
        r"Thi", exclude_tokens=["line0", "line1"], regex_flags=flags
    )
    insp = Inspector(result)
    assert len(insp.matches()) == expected_matches


@pytest.mark.parametrize(
    ("original_string", "num_lines"),
    [
        ("Single line.", 1),
        ("Line1\nLine2", 2),
        ("\nA\nB\nC\nD\n", 6),
    ],
)
def test_various_line_counts(original_string, num_lines):
    """Test text with various line counts."""
    text = SearchableText(original_string, token_spans=[])
    text._lazy_init()
    assert len(text._original_lines) == num_lines
    par = SearchableParagraph(*original_string.splitlines(), token_spans=[])
    assert len(text._original_lines) == num_lines


def test_kwargs_are_passed_to_parent(oneline_text, paragraph):
    assert oneline_text.color == m.BLUE
    assert paragraph.height == 8


def test_mixin_does_not_run_lazy_init_on_creation(oneline_text):
    assert not oneline_text._cached
    assert not hasattr(oneline_text, "_token2lines")


def test_mixin_runs_lazy_init_once_on_first_call(oneline_text):
    oneline_text.search()
    assert oneline_text._cached
    assert hasattr(oneline_text, "_token2lines")
    t2l = oneline_text._token2lines
    oneline_text.search()
    assert t2l is oneline_text._token2lines


# --------------------------------------------------------------------
# mutate
# --------------------------------------------------------------------
def _first(obj, pattern):
    return obj.search(pattern).first()


@pytest.mark.parametrize(
    "fixture_name",
    ["oneline_text", "multiline_text", "paragraph", "markup"],
)
def test_mutate_replaces_glyphs_and_updates_string(request, fixture_name):
    obj = request.getfixturevalue(fixture_name)
    glyphs = _first(obj, r"\bis\b")  # standalone "is", not the one in "This"
    before = obj._get_glyphs_container(0).submobjects

    with obj.mutate(glyphs, "WAS") as line:
        ...

    after = obj._get_glyphs_container(0).submobjects
    assert [g for g in after if g not in line["new"]] == [
        g for g in before if g not in glyphs
    ]  # untouched glyphs, in order
    assert not any(g is og for g in after for og in glyphs)  # old gone
    assert all(any(g is ng for ng in after) for g in line["new"])  # new present
    assert obj._original_lines[0].startswith("This WAS a ")


@pytest.mark.parametrize(
    "fixture_name",
    ["oneline_text", "multiline_text", "paragraph", "markup"],
)
def test_mutate_yielded_structure(request, fixture_name):
    obj = request.getfixturevalue(fixture_name)
    glyphs = _first(obj, r"\bis\b")

    with obj.mutate(glyphs, "WAS") as line:
        assert set(line.submob_dict.keys()) == {"head", "old", "new", "tail"}
        assert (
            line["head"].submobjects
            + line["old"].submobjects
            + line["tail"].submobjects
            == obj._get_glyphs_container(0).submobjects[: len(obj._original_lines[0])]
        )  # slice for multiline texts

    # after CM new replaces old
    assert (
        line["head"].submobjects + line["new"].submobjects + line["tail"].submobjects
        == obj._get_glyphs_container(0).submobjects[: len(obj._original_lines[0])]
    )  # slice for multiline texts


def test_mutate_aligns_new_glyphs_on_given_edge(oneline_text):
    glyphs = _first(oneline_text, r"oneline")

    with oneline_text.mutate(glyphs, "abc", align=m.UP) as line:
        np.testing.assert_allclose(
            line["new"].get_edge_center(m.UP), line["old"].get_edge_center(m.UP)
        )


def test_mutate_inherits_style_from_first_old_glyph(oneline_text):
    # fixture sets color=m.BLUE
    glyphs = _first(oneline_text, r"oneline")

    with oneline_text.mutate(glyphs, "Hello") as line:
        pass

    styles = {g.fill_color for g in line["new"]}
    assert styles == {m.BLUE}


def test_mutate_first_chains_search_and_mutate(oneline_text):
    with oneline_text.search(r"oneline").mutate_first("two words") as line:
        pass

    result = oneline_text.search(r"two\s+words")
    inspector = Inspector(result)
    assert (
        len(inspector.matches()) == 3
    )  # 1 per old token span: adjective, DEFAULT, noun
    assert (
        oneline_text._original_lines[0] == "This is a two wordsline string."
    )  # 'first' only matches "one" (adjective)


def test_search_maps_to_same_glyphs_after_length_changing_mutate(multiline_text):
    before = _first(multiline_text, r"string")

    with multiline_text.mutate(_first(multiline_text, r"multiline"), "tiny") as line:
        pass

    after = _first(multiline_text, r"string")
    assert {id(g) for g in after} == {id(g) for g in before}


def test_mutated_text_is_found_by_subsequent_search(oneline_text):
    with oneline_text.mutate(_first(oneline_text, r"oneline"), "swell") as line:
        pass

    result = oneline_text.search(r"swell")
    assert len(Inspector(result).glyphs()) == len("swell")


def test_mutate_foreign_glyphs_raise_ValueError(oneline_text, multiline_text):
    foreign = _first(multiline_text, r"This")

    with (
        pytest.raises(ValueError, match="Glyphs not found"),
        oneline_text.mutate(foreign, "x") as line,
    ):
        pass


def test_mutate_empty_glyph_group_raises_on_group():
    group = SearchableVGroup(SearchableText("Hello World"))

    with (
        pytest.raises(ValueError, match="Empty"),
        group.mutate(m.VGroup(), "x") as line,
    ):
        pass


def test_group_mutate_dispatches_through_nesting():
    inner = SearchableText("Hello World")
    group = SearchableVGroup(SearchableVGroup(inner))
    glyphs = group.search(r"World").first()

    with group.mutate(glyphs, "Planet") as line:
        pass

    assert inner._original_lines[0] == "Hello Planet"
    assert not any(g is og for g in group.get_family() for og in glyphs)


def test_group_mutate_skips_non_searchable_siblings():
    inner = SearchableText("Hello World")
    group = SearchableVGroup(m.Square(), inner)  # non-searchable sibling first
    glyphs = group.search(r"World").first()

    with group.mutate(glyphs, "Planet") as line:
        pass

    assert inner._original_lines[0] == "Hello Planet"


def test_mutate_to_empty_string_deletes_glyphs(oneline_text):
    obj = oneline_text
    glyphs = _first(obj, r"oneline")
    n_old = len(glyphs)
    n_before = len(obj.submobjects)

    with obj.mutate(glyphs, "") as line:
        n_new = len(line["new"])

    assert n_new == 0
    assert len(obj.submobjects) == n_before - n_old
    assert obj._original_lines[0] == "This is a line string."
    # remaining glyphs are still findable at their shifted positions
    assert len(Inspector(obj.search(r"string")).glyphs()) == len("string")
