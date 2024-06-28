from importlib import resources
import polars as pl

from actionsheets.sheet import parse_toml

pl.Config.set_tbl_cols(20) # TMP

class Actionsheets:
    def __init__(self, sheets: pl.DataFrame, snippets: pl.DataFrame):
        self.sheets_data = sheets
        self.snippets_data = snippets

    def sheet_ids(self, parent_id: str = '') -> list[str]:
        return self.sheets_data.filter(pl.col('parent') == parent_id)['sheet_id'].to_list()
    
    def sheet_info(self, id: str) -> dict:
        assert id in self.sheet_data['sheet_id'], f'attempted to access data of undefined sheet "{id}"'
        return self.sheet_data.row(by_predicate=pl.col('sheet_id') == id, named=True)

    def sheet_snippets(self, id: str) -> pl.DataFrame:
        assert id in self.get_sheets_ids(), f'attempted to access snippets of undefined sheet "{id}"'
        return self.snippets_data.filter(pl.col('sheet_id') == id)
    
    def find_sheet(self, query: str) -> str:
        return ''
    
    def find_snippets(self, query: str) -> pl.DataFrame:
        return self.snippets_data
    
    def find_sheet_snippets(self, id: str, query: str) -> pl.DataFrame:
        sheet_snippets_data = self.sheet_snippets(id=id)
        return sheet_snippets_data
    

def _parse() -> Actionsheets:
    data_root = resources.files('actionsheets.data')

    def gather_files(entries: resources.abc.Traversable) -> list[str]:
        files = []
        for entry in entries:
            if entry.is_dir():
                files += gather_files(entry.iterdir())
            elif entry.name.endswith('.toml'):
                files += [entry]
        return files

    files = gather_files(data_root.iterdir())
    assert files, 'no TOML topic files found inside the data subpackage'

    sheets_info = []
    sheet_data_list = []
    for file in files:
        print(f'Parsing file {file}...')
        sheet_info, snippets_data = parse_toml(file)
        print(f'Parsed topic: {sheet_info["name"]}')

        sheets_info.append(sheet_info)
        sheet_data_list.append(snippets_data)

    sheets_data = _process_sheets(pl.DataFrame(sheets_info))
    snippets_data = _process_snippets(pl.concat(sheet_data_list, how='diagonal'))

    return Actionsheets(sheets_data, snippets_data)        
        

def _process_sheets(sheets: pl.DataFrame) -> pl.DataFrame:
    # Generate sheet IDs
    sheets = sheets. \
        rename({'name': 'sheet_name', 'parent': 'sheet_parent'}). \
        with_columns(
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
    assert missing_sheet_names.is_empty(), f'missing definition for parent topic(s): {", ".join(missing_sheet_names)}'

    # Compute depth
    sheets = sheets.with_columns(
        depth=pl.col('sheet_id').str.count_match('\.')
    )

    # Set column order
    col_order = ['sheet_id', 'sheet_parent', 'sheet_name', 'language']
    parsed_sheets = sheets.select(pl.col(col_order), pl.exclude(col_order))

    return parsed_sheets

def _process_snippets(snippets_data: pl.DataFrame) -> pl.DataFrame:
    col_order = ['sheet_id', 'sheet_parent', 'sheet_name', 'snippet_id']

    return snippets_data.with_columns(
        sheet_id=pl.when(pl.col('sheet_parent') == '').
            then(pl.col('sheet_name')).
            otherwise(pl.col('sheet_parent') + '.' + pl.col('sheet_name'))
        ).select(
            pl.col(col_order),
            pl.exclude(col_order)
        )

sheets = _parse()

print('\n\nSHEETS:')
print(sheets.sheets_data)
print('\n\nSNIPPETS:')
print(sheets.snippets_data)
