import warnings
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Iterator, Self

import polars as pl
import re

from actionsheets.sheet import ActionsheetView
from actionsheets import sheet


class Actionsheets:
    def __init__(self, sheets_data: pl.DataFrame, snippets_data: pl.DataFrame):
        self.sheets_data = sheets_data
        self.snippets_data = snippets_data

    def ids(self, parent_id: str = '', nested: bool = True) -> list[str]:
        """
        Get the defined sheets for the given parent (or root)
        :param parent_id: Sheet ID
        :param nested: Whether to include nested children in the list
        :return: List of sheet IDs
        """
        if nested:
            return self._all_sheet_ids(parent_id=parent_id)
        else:
            return self._child_sheet_ids(parent_id=parent_id)

    def __len__(self) -> int:
        """
        Get the total number of sheets
        :return: Number of sheets
        """
        return self.count_sheets()

    def count_sheets(self, parent_id: str = '', nested: bool = True) -> int:
        """
        Count the number of sheets under the given parent sheet
        :param parent_id: Parent sheet ID (optional)
        :param nested: Whether to count nested sheets
        :return: Number of sheets
        """
        return len(self.ids(parent_id=parent_id, nested=nested))

    def count_snippets(self, parent_id: str = '', nested: bool = True) -> int:
        """
        Count the number of snippets under the given parent sheet
        :param parent_id: Parent sheet ID (optional)
        :param nested: Whether to count snippets from nested sheets
        :return: Number of snippets
        """
        sheet_ids = self.ids(parent_id=parent_id, nested=nested)

        return self.snippets_data.filter(pl.col('sheet_id').is_in(sheet_ids)).height

    def _all_sheet_ids(self, parent_id: str = '') -> list[str]:
        return self.sheets_data.filter(
            pl.col('sheet_id').str.starts_with(parent_id)
        )['sheet_id'].to_list()

    def _child_sheet_ids(self, parent_id: str = '') -> list[str]:
        return self.sheets_data.filter(
            pl.col('sheet_parent') == parent_id
        )['sheet_id'].to_list()

    def has_sheet(self, id: str, parent_id: str = '', nested: bool = True):
        """
        Check whether the sheet is defined
        :param id: Sheet ID
        :param parent_id: Parent sheet ID (optional)
        :param nested: Whether to search for nested sheets
        :return: Whether the sheet is defined
        """
        return id in self.ids(parent_id=parent_id, nested=nested)

    def sheet_info(self, id: str) -> dict:
        """
        Get info about a sheet
        :param id: Sheet ID
        :return: Dictionary with sheet info
        """
        assert id in self.sheets_data['sheet_id'], \
            f'attempted to access data of undefined sheet "{id}"'
        info = self.sheets_data.row(by_predicate=pl.col('sheet_id') == id, named=True)

        info['parents'] = id.split(sep='.')[:-1]

        return info

    def sheet_view(self, id: str) -> ActionsheetView:
        """
        Create a snippet view for the given sheet
        :return: View restricted to this sheet
        """
        assert id in self.snippets_data['sheet_id'], \
            f'attempted to access snippets of undefined sheet "{id}"'
        return ActionsheetView(data=self.snippets_data.filter(pl.col('sheet_id') == id))

    def find_sheet(self, query: str) -> str:
        """
        Find the best-matching sheet ID for the given query
        :param query: Search query
        :return: Sheet ID, or empty string if no matches
        """
        terms = re.split(r'\s+|,|\.|\|', query)

        result = self.sheets_data.with_columns(
            matches=pl.col('sheet_id').str.count_matches('|'.join(terms))
        ).filter(pl.col('matches') > 0)

        if result.height:
            return result.sort('matches', descending=True).head(n=1)[0, 'sheet_id']
        else:
            return ''

    def find_snippets(self, query: str, limit: int = 10) -> Self:
        """
        Find snippets across sheets
        :param query: Search query
        :param limit: Max number of snippets in the result
        :return: Actionsheets collection of matches. May be empty in case of no matches.
        """
        terms = re.split(r'\s+|,|\.|\|', query)
        search_pattern = '|'.join(terms)

        result = self.snippets_data.with_columns(
            matches=pl.col('snippet_id').str.count_matches(search_pattern) +
                    pl.col('sheet_id').str.count_matches(search_pattern)
        ).filter(pl.col('matches') > 0)

        filtered_data = (
            result.sort('matches', descending=True).
            head(n=limit).
            select(pl.exclude('matches'))
        )

        return Actionsheets(self.sheets_data, filtered_data)

    def find_sheet_snippets(self, id: str, query: str, limit: int = 10) -> pl.DataFrame:
        terms = re.split(r'\s+|,|\.|\|', query)

        result = self.sheet_view(id=id).data.with_columns(
            matches=pl.col('snippet_id').str.count_matches('|'.join(terms))
        ).filter(pl.col('matches') > 0)

        return (
            result.sort('matches', descending=True).
            head(n=limit).
            select(pl.exclude('matches'))
        )


def _gather_default_files() -> list[str]:
    data_root = resources.files('actionsheets.data')

    def gather_files(entries: Iterator[Traversable]) -> list[str]:
        files_list = []
        for entry in entries:
            if entry.is_dir():
                files_list += gather_files(entry.iterdir())
            elif entry.name.endswith('.toml'):
                files_list += [entry]
        return files_list

    files = gather_files(data_root.iterdir())

    assert files, 'no TOML topic files found inside the data subpackage'
    return files


def parse_toml(files: list[str]) -> Actionsheets:
    sheet_info_list = []
    sheet_data_list = []
    for file in files:
        print(f'Parsing file {file}...')
        sheet_info, snippets_data = sheet.parse_toml_file(file)
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
    # compute derived columns
    snippets_data = snippets_data.with_columns(
        pl.col('title').fill_null(pl.col('snippet_id')),
        pl.col('details').fill_null('').str.strip_chars_end(),
        pl.col('description').fill_null('').str.strip_chars_end(),
        depth=pl.col('snippet_id').str.count_matches('.', literal=True),
        sheet_id=pl.when(pl.col('sheet_parent') == '').
        then(pl.col('sheet_name')).
        otherwise(pl.col('sheet_parent') + '.' + pl.col('sheet_name'))
    )

    # check for code exceeding 80 chars
    long_snippets = (
        snippets_data.
        select(
            pl.col('sheet_id'),
            pl.col('snippet_id'),
            pl.col('code').str.split(by='\n').alias('code_lines')
        ).
        drop_nulls(subset='code_lines').
        explode(columns='code_lines').
        filter(
            pl.col('code_lines').str.len_chars() > 80
        ).
        select(pl.exclude('code_lines'))
    )

    if long_snippets.height > 0:
        with pl.Config() as cfg:
            cfg.set_tbl_hide_dataframe_shape(True)
            cfg.set_tbl_hide_column_data_types(True)
            cfg.set_fmt_str_lengths(100)
            warnings.warn(
                f'{long_snippets.height} code snippet(s) exceed max width of 80 chars:\n{long_snippets}'
            )

    # ensure column order
    col_order = ['sheet_id', 'sheet_parent', 'sheet_name', 'snippet_id']
    return snippets_data.select(pl.col(col_order), pl.exclude(col_order))


_default_sheets: Actionsheets = None


def default_sheets() -> Actionsheets:
    global _default_sheets

    if _default_sheets is None:
        files = _gather_default_files()
        _default_sheets = parse_toml(files)

    return _default_sheets


if __name__ == '__main__':
    sheets = default_sheets()
