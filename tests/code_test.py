import re
from pathlib import Path

from manim import ManimColor

from manim_utils import highlight_code


# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
def strip_pango_tags(text):
    """Remove Pango markup tags to get plain text for assertions."""
    # Remove the outer wrapper and the leading dot.
    text = re.sub(r"^<span\s+[^>]*>\.(.*)</span>$", r"\1", text)

    # Remove all remaining tags (<tt>, <span>, etc.) but KEEP the text inside.
    text = re.sub(r"<[^>]+>", "", text)

    # Remove leading dot
    text = text[1:]
    return text


def get_plain_lines(highlighted_obj):
    """Extract plain text lines from HighlightedCode object."""
    return [strip_pango_tags(line.original_text) for line in highlighted_obj.lines]


# ----------------------------------------------------------------------
# highlight_code
# ----------------------------------------------------------------------
def test_simple_single_line():
    """Test basic single line code."""
    code = "x = 1"
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 1
    assert plain == ["x = 1"]


def test_multiple_lines_no_multiline_tokens():
    """Test standard multi-line code."""
    code = """def foo():
    return 42"""
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 2
    assert plain == ["def foo():", "    return 42"]


def test_docstring_basic():
    """Test a simple single-line docstring."""
    code = '"""Simple docstring."""'
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 1
    assert plain == ['"""Simple docstring."""']


def test_docstring_multiline():
    """Test a multi-line docstring."""
    code = '''"""Line 1
Line 2
Line 3"""'''
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    # Should be exactly 3 lines, no extra empty lines
    assert len(result.lines) == 3
    assert plain == ['"""Line 1', "Line 2", 'Line 3"""']


def test_docstring_with_indentation():
    """Test docstring with indentation."""
    code = '''def foo():
    """Line 1
    Line 2"""
    return 1'''
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    # Should be exactly 4 lines
    assert len(result.lines) == 4
    assert plain == ["def foo():", '    """Line 1', '    Line 2"""', "    return 1"]

    # Ensure no empty lines were inserted
    assert all(line.strip() != "" for line in plain)


def test_docstring_followed_by_code_same_line():
    """Test docstring ending a line, followed by code on the same line."""
    code = '''"""Doc
Line 2""" + 1
x = 2'''
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 3
    assert plain == ['"""Doc', 'Line 2""" + 1', "x = 2"]


def test_triple_quoted_string_in_function():
    """Test triple quoted string inside a function with mixed content."""
    code = '''def func():
    s = """Multi
    line
    string"""
    return s'''
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    # Check structure
    assert len(result.lines) == 5
    assert plain == [
        "def func():",
        '    s = """Multi',
        "    line",
        '    string"""',
        "    return s",
    ]


def test_empty_lines_preserved():
    """Test that explicit empty lines in code are preserved."""
    code = """x = 1

y = 2"""
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 3
    assert plain == ["x = 1", "", "y = 2"]


def test_comment_multiline():
    """Test multi-line comments."""
    code = """# Line 1
# Line 2
x = 1"""
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 3
    assert plain == ["# Line 1", "# Line 2", "x = 1"]


def test_fstring_multiline():
    """Test multi-line f-strings."""
    code = '''f"""Line 1
Line 2"""'''
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 2
    assert plain == ['f"""Line 1', 'Line 2"""']


def test_mixed_indentation_levels():
    """Test code with varying indentation levels."""
    code = '''if True:
    if True:
        """Deep
        Doc"""
    x = 1'''
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    # Check indentation is preserved on docstring lines
    assert len(result.lines) == 5
    assert plain == [
        "if True:",
        "    if True:",
        '        """Deep',
        '        Doc"""',
        "    x = 1",
    ]


def test_no_trailing_newline():
    """Test code without a trailing newline."""
    code = "x = 1"
    result = highlight_code(code_string=code, language="python")

    assert len(result.lines) == 1


def test_only_newlines():
    """Test code that is just newlines."""
    code = "\n\n\n"
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    # Leading new lines are stripped
    assert len(result.lines) == 1
    assert plain == [""]


def test_unicode_characters():
    """Test code with unicode characters."""
    code = '''"""Hello 世界 🌍
Line 2"""'''
    result = highlight_code(code_string=code, language="python")
    plain = get_plain_lines(result)

    assert len(result.lines) == 2
    assert plain == ['"""Hello 世界 🌍', 'Line 2"""']


def test_special_characters_in_string():
    """Test strings with special characters that might break Pango."""
    code = r'''"""<script>alert('x')</script>
Line 2"""'''
    result = highlight_code(code_string=code, language="python")

    # Should not crash and should preserve the text
    assert result is not None
    assert len(result.lines) == 2


def test_from_file():
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\ny = 2")
        temp_path = f.name

    try:
        result = highlight_code(code_file=temp_path, language="python")
        plain = get_plain_lines(result)
        assert len(result.lines) == 2
        assert plain == ["x = 1", "y = 2"]
    finally:
        Path(temp_path).unlink()


def test_background_color_extracted():
    """Test that background color is extracted from the style."""
    code = "x = 1"
    result = highlight_code(code_string=code, language="python", style="vim")

    # bgcolor should be a ManimColor
    assert isinstance(result.bgcolor, ManimColor)


def test_tab_expansion():
    """Test that tabs are expanded correctly."""
    code = "x\t=\t1"
    result = highlight_code(code_string=code, language="python", tab_width=4)
    plain = get_plain_lines(result)

    assert len(result.lines) == 1
    assert "\t" not in plain[0]
    assert plain == ["x   =   1"]


def test_dedent_True():
    code = "\tx\t=\t1"
    result = highlight_code(
        code_string=code, language="python", tab_width=4, dedent=True
    )
    plain = get_plain_lines(result)

    assert len(result.lines) == 1
    assert "\t" not in plain[0]
    assert plain == ["x   =   1"]


def test_dedent_False():
    code = "\tx\t=\t1"
    result = highlight_code(
        code_string=code, language="python", tab_width=4, dedent=False
    )
    plain = get_plain_lines(result)

    assert len(result.lines) == 1
    assert "\t" not in plain[0]
    assert plain == ["    x   =   1"]


def test_console_output():
    code = """(venv) user@host:~/dir$ ls -la
total 2
drwxrwxr-x  8 mj mj   4096 avril 30 00:32 .
drwxrwxr-x 24 mj mj   4096 mars  17 14:45 ..
    """
    result = highlight_code(code_string=code, language="console")
    plain = get_plain_lines(result)
    assert len(result.lines) == 4
    assert plain == [
        "(venv) user@host:~/dir$ ls -la",
        "total 2",
        "drwxrwxr-x  8 mj mj   4096 avril 30 00:32 .",
        "drwxrwxr-x 24 mj mj   4096 mars  17 14:45 ..",
    ]
    print(plain)


def test_markup_includes_font_and_color():
    code = "def hello():\n    pass"
    output = highlight_code(code_string=code, font="Fira Code", style="vim")
    assert (
        output.lines[0].text
        == '.<tt><spanfgcolor="#cccccc"font="FiraCode">defhello():</span></tt>'
    )
    output = highlight_code(code_string=code, font="Fira Code", style="algol")
    assert (
        output.lines[0].text
        == '.<tt><spanfgcolor="#000000"font="FiraCode">defhello():</span></tt>'
    )
