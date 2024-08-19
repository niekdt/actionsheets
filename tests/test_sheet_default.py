import pytest
import glob
import polars as pl

from actionsheets.sheet import parse_toml_file


def find_toml_files() -> list[str]:
    return glob.glob('../src/**/*.toml', recursive=True)


@pytest.mark.parametrize('file', find_toml_files())
def test_parse_toml_file(file: str):
    sheet = parse_toml_file(file)

    assert type(sheet.info) is dict
    assert 'name' in sheet.info
    assert 'title' in sheet.info
    assert 'language' in sheet.info
    assert 'partial' in sheet.info

    assert type(sheet.data) is pl.DataFrame
    assert sheet.data.height > 0
