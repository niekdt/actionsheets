import tomllib

import pytest
import polars as pl

from actionsheets.sheet import parse_toml, ActionsheetView, action_keys, entry_keys, reserved_keys


@pytest.mark.parametrize('entry,result', [
    ('a', set()),
    ('a.b', {'a'}),
    ('a.b.c', {'a', 'a.b'}),
    ('a.b.c.d', {'a', 'a.b', 'a.b.c'}),
    ('create.list.join.str', {'create', 'create.list', 'create.list.join'}),
])
def test_get_parents(entry: str, result: set[str]):
    assert set(ActionsheetView.get_parents(entry)) == result


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


main_sheet = parse_toml(alt_sheet)


@pytest.mark.parametrize('entries,result', [
    (['create'], {'create'}),
    (['create.empty'], {'create', 'create.empty'}),
    (['create', 'create.empty'], {'create', 'create.empty'}),
    (['create.empty', 'create.string'], {'create', 'create.empty', 'create.string'}),
    (['create.empty', 'test.empty'], {'create', 'create.empty', 'test', 'test.empty'}),
])
def test_filter_view(entries: list[str], result: set[str]):
    assert set(main_sheet.filter(entries=entries).data['entry'].to_list()) == result


def test_find_snippets():
    assert main_sheet.find_snippets(query='antidisestablishmentarianism').height == 0

    assert main_sheet.find_snippets(query='create')['entry'].to_list() == [
        'create.empty', 'create.string', 'create.int'
    ]

    assert main_sheet.find_snippets(query='empty')['entry'].to_list() == [
        'create.empty', 'test.empty'
    ]


def test_unicode():
    sheet = parse_toml(empty_sheet + '[create.pi]\naction = "π"\ncode = "abcΣπ"\ndetails = "🙂"')

    assert (sheet.snippets()['title'] == 'π').all()
    assert (sheet.snippets()['code'] == 'abcΣπ').all()
    assert (sheet.snippets()['details'] == '🙂').all()


@pytest.mark.parametrize('source', [
    'https://github.com/niekdt/actionsheets',
    'From a friend'
])
def test_source(source):
    sheet = parse_toml(
        single_snippet_sheet +
        f'[create.ref]\naction = "Borrowed snippet"\ncode = "1 + 1"\nsource = "{source}"'
    )

    assert sheet.snippets().filter(pl.col('entry') == 'create.empty')['source'][0] is None
    assert sheet.snippets().filter(pl.col('entry') == 'create.ref')['source'][0] == source


@pytest.mark.parametrize('keywords', [
    '""', '"a"', '[""]', '["a", ""]', '["", "b"]', '["", ""]'
])
def test_wrong_keywords(keywords):
    with pytest.raises(Exception):
        parse_toml(header + f'keywords = {keywords}')


@pytest.mark.parametrize('keywords,result', [
    ([], set()),
    (['a'], {'a'}),
    (['a', 'b'], {'a', 'b'}),
    (['a', 'b', 'b'], {'a', 'b'}),
    (['a', 'b', 'c'], {'a', 'b', 'c'})
])
def test_keywords(keywords: list[str], result: set[str]):
    if not keywords:
        keywords_str = '[]'
    else:
        keywords_str = '["' + '", "'.join(keywords) + '"]'

    sheet = parse_toml(header + f'keywords = {keywords_str}')
    assert sheet.info['keywords'] == list(result)


@pytest.mark.parametrize('field', set(entry_keys + reserved_keys))
def test_reserved_field(field):
    with pytest.raises((AssertionError, tomllib.TOMLDecodeError)) as e:
        parse_toml(single_snippet_sheet + f'[create.{field}]\naction="To fail"\ncode="1 = 1"')
    print(e.type)
    print(e.value)
