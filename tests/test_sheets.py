import pytest
import polars as pl
from actionsheets.sheets import default_sheets

sheets = default_sheets()


def test_keywords():
    assert sheets.sheets_data.schema['keywords'] == pl.List(pl.String)


def test_filter():
    py_sheets = sheets.filter('python')
    assert not py_sheets.has_sheet('r')
    assert py_sheets.has_sheet('python')
    assert py_sheets.has_sheet('python.collections')

    py_sheets = sheets.filter('python.collections')
    assert py_sheets.has_sheet('python.collections')
    assert py_sheets.has_sheet('python.collections.dict')
    assert not py_sheets.has_sheet('python')
    assert not py_sheets.has_sheet('r')

    r_sheets = sheets.filter('r')
    assert not r_sheets.has_sheet('python')
    assert r_sheets.has_sheet('r')


@pytest.mark.parametrize('query,result', [
    ('pneumonoultramicroscopicsilicovolcanoconiosis', ''),
    ('datetime', 'python.scalars.datetime'),
    ('polars dataframe', 'python.polars.dataframe'),
    ('pandas dataframe', 'python.pandas.dataframe'),
    ('dict', 'python.collections.dict')
])
def test_find_sheet(query: str, result: str):
    assert sheets.find_sheet(query) == result


@pytest.mark.parametrize('limit', [1, 2, 5, 10])
def test_find_snippets(limit):
    result = sheets.find_snippets('create', limit=limit)
    assert result.count_snippets() == limit


@pytest.mark.parametrize('sheet', ['python.collections.dict', 'python.scalars.datetime'])
def test_find_sheet_snippets(sheet):
    result = sheets.sheet_view(sheet).find_snippets(query='create')
    assert (result['sheet'] == sheet).all()
