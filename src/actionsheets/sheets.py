from importlib import resources
from importlib.resources.abc import Traversable

import polars as pl
import re

from actionsheets.sheet import ActionsheetView
from actionsheets import sheet


class Actionsheets:
    def __init__(self, sheets: pl.DataFrame, snippets: pl.DataFrame):
        self.sheets_data = sheets
        self.snippets_data = snippets

    def ids(self, parent_id: str = '') -> list[str]:
        return self.sheets_data.filter(
            pl.col('sheet_parent') == parent_id
        )['sheet_id'].to_list()

    def sheet_info(self, id: str) -> dict:
        assert id in self.sheets_data['sheet_id'], \
            f'attempted to access data of undefined sheet "{id}"'
        info = self.sheets_data.row(by_predicate=pl.col('sheet_id') == id, named=True)

        info['parents'] = id.split(sep='.')[:-1]

        return info

    def sheet_view(self, id: str) -> ActionsheetView:
        assert id in self.snippets_data['sheet_id'], \
            f'attempted to access snippets of undefined sheet "{id}"'
        return ActionsheetView(data=self.snippets_data.filter(pl.col('sheet_id') == id))

    def find_sheet(self, query: str) -> str:
        terms = re.split(r'\s+|,|\.|\|', query)

        result = self.sheets_data.with_columns(
            matches=pl.col('sheet_id').str.count_matches('|'.join(terms))
        ).filter(pl.col('matches') > 0)

        assert result.height > 0, f'no sheets found for query: "{query}"'

        return result.sort('matches', descending=True).head(n=1)[0, 'sheet_id']

    def find_snippets(self, query: str, limit: int = 10) -> pl.DataFrame:
        terms = re.split(r'\s+|,|\.|\|', query)
        search_pattern = '|'.join(terms)

        result = self.snippets_data.with_columns(
            matches=pl.col('snippet_id').str.count_matches(search_pattern) + pl.col(
                'sheet_id').str.count_matches(search_pattern)
        ).filter(pl.col('matches') > 0)

        assert result.height > 0, f'no snippets found for query: "{query}"'

        return (
            result.sort('matches', descending=True).
            head(n=limit).
            select(pl.exclude('matches'))
        )

    def find_sheet_snippets(self, id: str, query: str, limit: int = 10) -> pl.DataFrame:
        terms = re.split(r'\s+|,|\.|\|', query)

        result = self.sheet_view(id=id).data.with_columns(
            matches=pl.col('snippet_id').str.count_matches('|'.join(terms))
        ).filter(pl.col('matches') > 0)

        assert result.height > 0, f'no snippets found for query: "{query}"'

        return (
            result.sort('matches', descending=True).
            head(n=limit).
            select(pl.exclude('matches'))
        )


def _gather_default_files() -> list[str]:
    data_root = resources.files('actionsheets.data')

    def gather_files(entries: Traversable) -> list[str]:
        files = []
        for entry in entries:
            if entry.is_dir():
                files += gather_files(entry.iterdir())
            elif entry.name.endswith('.toml'):
                files += [entry]
        return files

    files = gather_files(data_root.iterdir())

    assert files, 'no TOML topic files found inside the data subpackage'
    return files


def parse_toml(files: list[str]) -> Actionsheets:
    sheet_info_list = []
    sheet_data_list = []
    for file in files:
        print(f'Parsing file {file}...')
        sheet_info, snippets_data = sheet.parse_toml(file)
        print(f'Parsed topic: {sheet_info["name"]}')

        sheet_info_list.append(sheet_info)
        sheet_data_list.append(snippets_data)

    return _process_sheet_list(sheet_info_list, sheet_data_list)


def _process_sheet_list(
        sheet_info_list: list[dict],
        sheet_data_list: list[pl.DataFrame]
) -> Actionsheets:
    sheets_data = _process_sheets(pl.DataFrame(sheet_info_list))
    snippets_data = _process_snippets(pl.concat(sheet_data_list, how='diagonal'))

    return Actionsheets(sheets_data, snippets_data)


def _process_sheets(sheets: pl.DataFrame) -> pl.DataFrame:
    # Rename columns
    sheets = sheets.rename({'name': 'sheet_name', 'parent': 'sheet_parent'})

    # Generate IDs
    sheets = sheets.with_columns(
        sheet_id=pl.when(pl.col('sheet_parent') == '').
        then(pl.col('sheet_name')).
        otherwise(pl.col('sheet_parent') + '.' + pl.col('sheet_name'))
    )

    # Check for missing parent topics
    missing_sheet_names = (
        sheets['sheet_parent'].
        filter(sheets['sheet_parent'].is_in(sheets['sheet_id']).not_()).
        replace('', None).
        drop_nulls()
    )
    assert missing_sheet_names.is_empty(), \
        f'missing definition for parent topic(s): {", ".join(missing_sheet_names)}'

    # Fill optional fields, compute depth
    sheets = sheets.with_columns(
        pl.col('description').fill_null(''),
        pl.col('details').fill_null(''),
        depth=pl.col('sheet_id').str.count_matches('\.')
    )

    # Set column order
    col_order = ['sheet_id', 'sheet_parent', 'sheet_name', 'language']
    return sheets.select(pl.col(col_order), pl.exclude(col_order))


def _process_snippets(snippets_data: pl.DataFrame) -> pl.DataFrame:
    col_order = ['sheet_id', 'sheet_parent', 'sheet_name', 'snippet_id']

    return snippets_data.with_columns(
        pl.col('title').fill_null(pl.col('snippet_id')),
        pl.col('details').fill_null('').str.strip_chars_end(),
        pl.col('description').fill_null('').str.strip_chars_end(),
        depth=pl.col('snippet_id').str.count_matches('.', literal=True),
        sheet_id=pl.when(pl.col('sheet_parent') == '').
        then(pl.col('sheet_name')).
        otherwise(pl.col('sheet_parent') + '.' + pl.col('sheet_name'))
    ).select(
        pl.col(col_order),
        pl.exclude(col_order)
    )


_default_sheets: Actionsheets = None


def default_sheets() -> Actionsheets:
    global _default_sheets

    if _default_sheets is None:
        files = _gather_default_files()
        _default_sheets = parse_toml(files)

    return _default_sheets


if __name__ == '__main__':
    sheets = default_sheets()
