import warnings
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Iterator, Self

import polars as pl
import re

from actionsheets.sheet import ActionsheetView, parse_toml_file


class Actionsheets:
    def __init__(self, sheets_data: pl.DataFrame, snippets_data: pl.DataFrame):
        self.sheets_data = sheets_data
        self.snippets_data = snippets_data

    def sheets(self, parent: str = '', nested: bool = True) -> list[str]:
        """
        Get the sheet IDs belonging to the given parent sheet (or root)
        :param parent: Sheet ID
        :param nested: Whether to include nested children in the list
        :return: List of sheet IDs
        """
        if nested:
            return self._all_sheet_ids(parent=parent)
        else:
            return self._child_sheet_ids(parent=parent)

    def __len__(self) -> int:
        """
        Get the total number of sheets
        :return: Number of sheets
        """
        return self.count_sheets()

    def count_sheets(self, parent: str = '', nested: bool = True) -> int:
        """
        Count the number of sheets under the given parent sheet
        :param parent: Parent sheet ID (optional)
        :param nested: Whether to count nested sheets
        :return: Number of sheets
        """
        return len(self.sheets(parent=parent, nested=nested))

    def count_snippets(self, parent: str = '', nested: bool = True) -> int:
        """
        Count the number of snippets under the given parent sheet
        :param parent: Parent sheet ID (optional)
        :param nested: Whether to count snippets from nested sheets
        :return: Number of snippets
        """
        sheet_ids = self.sheets(parent=parent, nested=nested)

        return self.snippets_data.filter(
            (pl.col('sheet').is_in(sheet_ids)) & (pl.col('type') == 'action')
        ).height

    def _all_sheet_ids(self, parent: str = '') -> list[str]:
        return self.sheets_data.filter(
            pl.col('sheet').str.starts_with(parent)
        )['sheet'].to_list()

    def _child_sheet_ids(self, parent: str = '') -> list[str]:
        return self.sheets_data.filter(
            pl.col('sheet_parent') == parent
        )['sheet'].to_list()

    def has_sheet(self, sheet: str, parent: str = '', nested: bool = True) -> bool:
        """
        Check whether the sheet is defined
        :param sheet: Sheet ID
        :param parent: Parent sheet ID (optional)
        :param nested: Whether to search for nested sheets
        :return: Whether the sheet is defined
        """
        return sheet in self.sheets(parent=parent, nested=nested)

    def sheet_info(self, sheet: str) -> dict:
        """
        Get info about a sheet
        :param sheet: Sheet ID
        :return: Dictionary with sheet info
        """
        assert sheet in self.sheets_data['sheet'], \
            f'attempted to access data of undefined sheet "{sheet}"'
        info = self.sheets_data.row(by_predicate=pl.col('sheet') == sheet, named=True)

        info['parents'] = sheet.split(sep='.')[:-1]

        return info

    def sheet_view(self, sheet: str) -> ActionsheetView:
        """
        Create an actionsheet view for the given sheet
        :return: View restricted to this sheet
        """
        return ActionsheetView(
            info=self.sheet_info(sheet),
            data=self.snippets_data.filter(pl.col('sheet') == sheet)
        )

    def filter(self, sheet: str) -> Self:
        sheet_ids = self.sheets(parent=sheet) + [sheet]

        return Actionsheets(
            sheets_data=self.sheets_data.filter(pl.col('sheet').is_in(sheet_ids)),
            snippets_data=self.snippets_data.filter(pl.col('sheet').is_in(sheet_ids))
        )

    def find_sheet(self, query: str) -> str:
        """
        Find the best-matching sheet ID for the given query
        :param query: Search query
        :return: Sheet ID, or empty string if no matches
        """
        terms = re.split(r'\s+|,|\.|\|', query)
        re_query = '|'.join(terms)

        result = self.sheets_data.with_columns(
            id_matches=pl.col('sheet').str.count_matches(re_query),
            keyword_matches=pl.col('keywords').list.count_matches(re_query)
        ).with_columns(
            matches=pl.sum_horizontal('id_matches', 'keyword_matches')
        ).filter(
            pl.col('matches') > 0
        )

        if result.height:
            return result.sort('matches', descending=True).head(n=1)[0, 'sheet']
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

        result = self.snippets_data.filter(pl.col('type') == 'action').with_columns(
            (
                    pl.col('entry').str.count_matches(search_pattern) +
                    pl.col('sheet').str.count_matches(search_pattern)
            ).alias('matches')
        ).filter(pl.col('matches') > 0)

        filtered_data = (
            result.sort('matches', descending=True).
            head(n=limit).
            select(pl.exclude('matches'))
        )

        return Actionsheets(self.sheets_data, filtered_data)


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


def parse_toml_files(files: list[str]) -> Actionsheets:
    sheet_info_list = []
    sheet_data_list = []
    for file in files:
        print(f'Parsing file {file}...')
        sheet = parse_toml_file(file)
        print(f'Parsed topic: {sheet.info["name"]}')

        sheet_info_list.append(sheet.info)
        sheet_data_list.append(sheet.data)

    return _process_sheet_list(sheet_info_list, sheet_data_list)


def _process_sheet_list(
        sheet_info_list: list[dict],
        sheet_data_list: list[pl.DataFrame]
) -> Actionsheets:
    sheets_data = _process_sheets(pl.DataFrame(sheet_info_list))
    snippets_data = _process_snippets(pl.concat(sheet_data_list, how='diagonal'))

    return Actionsheets(sheets_data, snippets_data)


def _process_sheets(sheets_data: pl.DataFrame) -> pl.DataFrame:
    # Rename columns
    sheets_data = sheets_data.rename({'name': 'sheet_name', 'parent': 'sheet_parent'})

    # Generate IDs
    sheets_data = sheets_data.with_columns(
        pl.when(pl.col('sheet_parent') == '').
        then(pl.col('sheet_name')).
        otherwise(pl.col('sheet_parent') + '.' + pl.col('sheet_name')).
        alias('sheet')
    )

    # Check for missing parent topics
    missing_sheet_names = (
        sheets_data['sheet_parent'].
        filter(sheets_data['sheet_parent'].is_in(sheets_data['sheet']).not_()).
        replace('', None).
        drop_nulls()
    )
    assert missing_sheet_names.is_empty(), \
        f'missing definition for parent topic(s): {", ".join(missing_sheet_names)}'

    # Fill optional fields, compute depth
    sheets_data = sheets_data.with_columns(
        pl.col('description').fill_null(''),
        pl.col('details').fill_null(''),
        pl.col('sheet').str.count_matches(r'\.').alias('depth')
    )

    # Handle sheet ordering
    sheets_data = _subprocess_sheets_order(sheets_data)

    # Set column order
    col_order = ['sheet', 'sheet_parent', 'sheet_name', 'language']
    return sheets_data.select(pl.col(col_order), pl.exclude(col_order))


def _subprocess_sheets_order(sheets_data: pl.DataFrame) -> pl.DataFrame:
    df_after = sheets_data.select(
        ['sheet_name', 'sheet', 'sheet_parent', 'after']
    )
    # Find sheets without after-reference
    df_resolved = df_after.filter(
        pl.col('after').is_null()
    )

    # Resolve after-references incrementally
    while True:
        # Compute key for resolved sheets
        df_resolved = df_resolved.with_columns(
            _key=pl.concat_str(pl.col('after').fill_null(''), pl.lit('.'), pl.col('sheet_name'))
        )
        # Find remaining unresolved sheets
        df_unresolved = df_after.join(df_resolved, on=['sheet_parent', 'sheet_name'], how='anti')

        # Update after column to the _key of referenced sheet
        df_new = df_unresolved.join(
            df_resolved.select(['sheet_parent', 'sheet_name', '_key']),
            left_on=['sheet_parent', 'after'],
            right_on=['sheet_parent', 'sheet_name'],
            coalesce=True
        ).with_columns(
            after=pl.col('_key')
        )

        # Add newly resolved sheets to the resolved frame
        df_resolved = df_resolved.vstack(df_new)

        if not df_new.height:
            assert not df_unresolved.height, \
                'unresolvable "after" entries for sheets: {sheets}, missing reference sheet'.format(
                    sheets=', '.join(df_unresolved['sheet'].to_list())
                )
            break

    return (
        sheets_data.
        select(pl.exclude('after')).
        join(
            df_resolved.select(pl.exclude(['sheet_name', 'sheet_parent'])),
            on='sheet',
            how='left'
        ).
        sort(by=['sheet_parent', '_key']).
        with_columns(
            rank=pl.cum_count('_key').over('sheet_parent')
        ).
        select(pl.exclude(['after', '_key']))
    )


def _process_snippets(snippets_data: pl.DataFrame) -> pl.DataFrame:
    # compute derived columns
    snippets_data = snippets_data.with_columns(
        pl.col('title').fill_null(pl.col('entry')),
        pl.col('details').fill_null('').str.strip_chars_end(),
        pl.col('description').fill_null('').str.strip_chars_end(),
        pl.col('entry').str.count_matches('.', literal=True).alias('depth'),
        (
            pl.when(pl.col('sheet_parent') == '').
            then(pl.col('sheet_name')).
            otherwise(pl.col('sheet_parent') + '.' + pl.col('sheet_name'))
        ).alias('sheet')
    )

    # check for code exceeding 80 chars
    long_snippets = (
        snippets_data.
        select(
            pl.col('sheet'),
            pl.col('entry'),
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
                f'{long_snippets.height} code snippet(s) exceed 80 chars per line:\n{long_snippets}'
            )

    # ensure column order
    col_order = ['sheet', 'sheet_parent', 'sheet_name', 'entry']
    return snippets_data.select(pl.col(col_order), pl.exclude(col_order))


_default_sheets: Actionsheets | None = None


def default_sheets() -> Actionsheets:
    global _default_sheets

    if _default_sheets is None:
        files = _gather_default_files()
        _default_sheets = parse_toml_files(files)

    return _default_sheets


if __name__ == '__main__':
    sheets = default_sheets()
