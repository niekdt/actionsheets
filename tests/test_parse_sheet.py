import pytest
import glob
import polars as pl

from actionsheets import sheet


def find_toml_files() -> list[str]:
    return glob.glob('../src/**/*.toml', recursive=True)


@pytest.mark.parametrize('file', find_toml_files())
def test_parse_toml_file(file: str):
    sheet_info, snippets_data = sheet.parse_toml(file)

    assert type(sheet_info) is dict
    assert 'name' in sheet_info
    assert 'title' in sheet_info
    assert 'language' in sheet_info

    assert type(snippets_data) is pl.DataFrame
    assert snippets_data.height > 0
