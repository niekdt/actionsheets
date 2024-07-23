from actionsheets.sheet import parse_toml

header = """
language = "python"
parent = "python.basic"
name = "dict"
title = "Dict"
"""

empty_sheet = header + """
[create]
section = "Create"
"""


def test_empty_sheet():
    sheet = parse_toml(empty_sheet)

    assert sheet.info['name'] == 'dict'
    assert sheet.has_section('create')
    assert not sheet.has_section('c')
    assert not sheet.has_section('created')
    assert not sheet.has_section('test')

    assert sheet.entries(type='section') == ['create']
    assert sheet.entries(type='action') == []

    assert sheet.count_snippets() == 0


single_snippet_sheet = empty_sheet + """
[create.empty]
what = "Empty"
code = "x = {}"
"""


def test_single_snippet_sheet():
    sheet = parse_toml(single_snippet_sheet)

    assert sheet.has_section('create')

    assert sheet.entries(type='section') == ['create']
    assert sheet.entries(type='action') == ['create.empty']

    assert sheet.has_snippet('create.empty')
    assert not sheet.has_snippet('create.e')

    assert sheet.count_snippets() == 1


multi_snippet_sheet = single_snippet_sheet + """
[create.string]
what = "Define with string keys"
code = "x = {'color': 'blue', 'size': 'large'}"

[create.int]
what = "Define with integer keys"
code = "x = {1: 'a', 2: 'b', 3: 'c'}"
"""


def test_multi_snippet_sheet():
    sheet = parse_toml(multi_snippet_sheet)

    assert sheet.has_section('create')

    assert sheet.entries(type='section') == ['create']
    assert sheet.entries(type='action') == ['create.empty', 'create.string', 'create.int']

    assert sheet.has_snippet('create.empty')
    assert sheet.has_snippet('create.string')
    assert sheet.has_snippet('create.int')

    assert sheet.count_snippets() == 3


sections_sheet = multi_snippet_sheet + """
[test]
section = "Test"

[test.empty]
what = "Empty"
code = "not x"
"""


def test_sections_sheet():
    sheet = parse_toml(sections_sheet)

    assert sheet.has_section('create')
    assert sheet.has_section('test')

    assert sheet.entries(type='section') == ['create', 'test']
    assert sheet.entries(type='action') == [
        'create.empty', 'create.string', 'create.int', 'test.empty'
    ]

    assert sheet.has_snippet('create.empty')
    assert sheet.has_snippet('test.empty')

    assert sheet.count_snippets() == 4


subsections_sheet = sections_sheet + """
[derive]
section = "Derive"

[derive.copy]
what = "Copy"
code = "x.copy()"

[derive.subset]
section = "Subset"

[derive.subset.keys]
what = "Subset for keys"
code = "{k: x[k] for k in keys}"

[derive.subset.keys.default]
what = "Subset for keys with default _v_"
code = "{k: x.get(k, default=v) for k in keys}"
"""


def test_subsections_sheet():
    sheet = parse_toml(subsections_sheet)

    assert sheet.has_section('create')
    assert sheet.has_section('test')
    assert sheet.has_section('derive')

    assert sheet.entries(type='section') == ['create', 'test', 'derive', 'derive.subset']
    assert sheet.entries(type='action') == [
        'create.empty', 'create.string', 'create.int',
        'test.empty',
        'derive.copy', 'derive.subset.keys', 'derive.subset.keys.default'
    ]

    assert sheet.has_snippet('create.empty')
    assert sheet.has_snippet('test.empty')
    assert sheet.has_snippet('derive.subset.keys.default')

    assert sheet.count_snippets() == 7


alt_sheet = subsections_sheet + """
[derive.copy.new]
code = "dict(x)"
"""


def test_alt_sheet():
    sheet = parse_toml(alt_sheet)

    assert sheet.has_section('create')
    assert sheet.has_section('test')
    assert sheet.has_section('derive')

    assert sheet.entries(type='section') == ['create', 'test', 'derive', 'derive.subset']
    assert sheet.entries(type='action') == [
        'create.empty', 'create.string', 'create.int',
        'test.empty',
        'derive.copy', 'derive.copy.new',
        'derive.subset.keys', 'derive.subset.keys.default'
    ]

    assert sheet.has_snippet('create.empty')
    assert sheet.has_snippet('test.empty')
    assert sheet.has_snippet('derive.subset.keys.default')
    assert sheet.has_snippet('derive.copy.new')

    assert sheet.count_snippets() == 8


def test_find_snippets():
    sheet = parse_toml(alt_sheet)

    assert sheet.find_snippets(query='antidisestablishmentarianism').height == 0

    assert sheet.find_snippets(query='create')['entry'].to_list() == [
        'create.empty', 'create.string', 'create.int'
    ]

    assert sheet.find_snippets(query='empty')['entry'].to_list() == [
        'create.empty', 'test.empty'
    ]

