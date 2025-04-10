from parso import split_lines

from starkiller.refactoring import EditRange, get_rename_edits

TEST_CASE = """
a = ndarray([[1, 0], [0, 1]])
b = ndarray([[4, 1], [2, 2]])
print(dot(a, b))
"""

EXPECTED_RESULT = """
a = np.ndarray([[1, 0], [0, 1]])
b = np.ndarray([[4, 1], [2, 2]])
print(np.dot(a, b))
"""


def apply_inline_changes(source: str, changes: list[tuple[EditRange, str]]) -> str:
    changes.sort(key=lambda x: (x[0].start.line, x[0].start.char), reverse=True)
    lines = list(split_lines(source))
    for range_, new_text in changes:
        assert range_.start.line == range_.end.line, "Multiline changes are not supported yet"
        line = lines[range_.start.line]
        lines[range_.start.line] = line[:range_.start.char] + new_text + line[range_.end.char:]
    return "\n".join(lines)


def test_rename() -> None:
    rename_map = {"ndarray": "np.ndarray", "dot": "np.dot"}
    changes = list(get_rename_edits(TEST_CASE, rename_map))
    assert apply_inline_changes(TEST_CASE, changes) == EXPECTED_RESULT
