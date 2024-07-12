import pytest
from actionsheets.sheets import default_sheets

sheets = default_sheets()


@pytest.mark.parametrize('query,result', [
    ('datetime', 'python.scalars.datetime'),
    ('dataframe', 'python.pandas.dataframe'),
    ('asdfsdf dataframe', 'python.pandas.dataframe'),
    ('polars dataframe', 'python.polars.dataframe'),
    ('pandas dataframe', 'python.pandas.dataframe'),
    ('dict', 'python.collections.dict')
])
def test_find_sheet(query: str, result: str):
    assert sheets.find_sheet(query) == result


@pytest.mark.parametrize('limit', [1, 2, 5, 10])
def test_find_snippets(limit):
    result = sheets.find_snippets('create', limit=limit)
    assert result.height == limit


@pytest.mark.parametrize('sheet', ['python.collections.dict', 'python.scalars.datetime'])
def test_find_sheet_snippets(sheet):
    result = sheets.find_sheet_snippets(id=sheet, query='create')
    assert (result['sheet_id'] == sheet).all()
