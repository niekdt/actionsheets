import itertools
import re
import tomllib
from functools import reduce
from typing import Literal, Self

import polars as pl

header_keys = ('name', 'language', 'parent', 'title', 'description', 'details',
               'keywords', 'code', 'after')
section_keys = ('section', 'description', 'details', 'code')
solution_keys = ('code', 'details', 'source')
action_keys = ('action', 'description') + solution_keys
entry_keys = tuple(set(section_keys + action_keys + solution_keys))
reserved_keys = ('name', 'id', 'depth')


class ActionsheetView:
    def __init__(self, info: dict, data: pl.DataFrame):
        self.info = info
        self.data = data

    def __len__(self) -> int:
        """
        Get the number of snippets contained in this view
        :return: Number of snippets
        """
        return self.snippets().height

    def entries(
            self,
            type: Literal['section', 'part', 'action'],
            parent: str = '',
            nested: bool = True
    ) -> list[str]:
        """
        Get the IDs of all entries belonging to the given section
        :param type: Entry type
        :param parent: Parent entry (optional)
        :param nested: Whether to include nested entries
        :return: List of IDs
        """
        if nested:
            return self.data.filter(
                (pl.col('parent_entry').str.starts_with(parent)) & (pl.col('type') == type)
            )['entry'].to_list()
        else:
            return self.data.filter(
                (pl.col('parent_entry') == parent) & (pl.col('type') == type)
            )['entry'].to_list()

    def count_snippets(self, parent: str = '', nested: bool = True) -> int:
        """
        Count the number of snippets under the given parent entry
        :param parent: Parent entry ID (optional)
        :param nested: Whether to count snippets of nested entries
        :return: Number of snippets
        """
        return len(self.entries(type='action', parent=parent, nested=nested))

    def has_section(self, section: str) -> bool:
        """
        Check whether the section is defined in the view
        :param section: Section ID
        :return: Whether the section exists
        """
        return section in self.data.filter(pl.col('type') == 'section')['entry']

    def has_snippet(self, snippet: str) -> bool:
        """
        Check whether the snippet is defined in the view
        :param snippet: Snippet ID
        :return: Whether the snippet exists in the view
        """
        return snippet in self.data.filter(pl.col('type') == 'action')['entry']

    def section_info(self, section: str) -> dict:
        """
        Get metadata about a section
        :param section: Section ID
        :return: Dictionary with info
        """
        info = self.data.row(
            by_predicate=(pl.col('type') == 'section') & (pl.col('entry') == section),
            named=True
        )

        info['parents'] = section.split(sep='.')[:-1]
        return info

    def filter(self, entries: list[str]) -> Self:
        """
        Get a filtered view comprising the given entries, and all of their parents
        :param entries: List of entry IDs to include in the reduced view
        :return: The filtered view
        """
        all_parents = set(itertools.chain.from_iterable(
            [self.get_parents(e) for e in entries]
        ))
        print(all_parents)

        df_parents = self.data.filter(
            pl.col('entry').is_in(all_parents)
        )
        df_entries = self.data.filter(
            pl.col('entry').is_in(entries)
        )
        filtered_data = pl.DataFrame.vstack(
            df_parents,
            df_entries
        ).unique(subset='entry')

        return ActionsheetView(info=self.info, data=filtered_data)

    def filter_section(self, section: str) -> Self:
        """
        Get a filtered view comprising only the children of a given section
        :param section: Section ID
        :return: The filtered view
        """
        return ActionsheetView(
            info=self.info,
            data=self.data.filter(pl.col('entry').str.starts_with(section))
        )

    def section_snippets(self, section: str) -> pl.DataFrame:
        """
        Get the snippets data of a section
        :param section: Section ID
        :return: Snippets data
        """
        return self.snippets().filter(pl.col('parent_entry') == section)

    def snippets(self) -> pl.DataFrame:
        """
        Get all snippets data
        :return: Snippets data
        """
        return self.data.filter(pl.col('type') == 'action')

    def find_snippets(self, query: str, limit: int = 10) -> pl.DataFrame:
        """
        Search for snippets
        :param query: Search query
        :param limit: Max number of snippets in the result
        :return: Snippets data for matching snippets. May be empty in case of no matches.
        """
        terms = re.split(r'\s+|,|\.|\|', query)

        result = self.snippets().with_columns(
            pl.col('entry').str.count_matches('|'.join(terms)).alias('matches')
        ).filter(pl.col('matches') > 0)

        return (
            result.sort('matches', descending=True).
            head(n=limit).
            select(pl.exclude('matches'))
        )

    @staticmethod
    def get_parent(entry: str) -> str:
        """
        Get the parent ID for the given entry
        :param entry: Entry ID
        :return: Parent entry ID, or '' if no parent
        """
        parent_names = entry.split(sep='.')[:-1]
        return '.'.join(parent_names)

    @staticmethod
    def get_parents(entry: str) -> list[str]:
        """
        Get a list of parent IDs for the given entry, up to the root
        :param entry: Entry ID
        :return: List of parent entry IDs
        """
        parent_names = entry.split(sep='.')[:-1]
        return reduce(
            lambda path, p: path + [path[-1] + '.' + p] if path else [p],
            parent_names,
            []
        )


def parse_toml_file(path) -> ActionsheetView:
    """
    Parse an actionsheet TOML file
    :param path: The path to open
    :return: Processed action sheet info and data
    """
    with open(path, encoding='utf-8') as file:
        file_content = file.read()
        return parse_toml(content=file_content, content_id=path)


def parse_toml(content: str, content_id: str = 'undefined') -> ActionsheetView:
    """
    Parse an actionsheet TOML string
    :param content: The TOML content to parse
    :param content_id: Identifier for this content in source reporting
    :return: Processed action sheet info and data
    """
    data = tomllib.loads(content)

    assert data, f'{content_id} has no TOML content'

    # Process header content
    sheet_info = _process_header(data=data, content_id=content_id)

    # Process sections & snippets
    sheet_data = _process_body(data, name=sheet_info['name'], id='').with_columns(
        pl.lit(sheet_info['name']).alias('sheet_name'),
        pl.lit(sheet_info['parent']).alias('sheet_parent'),
        pl.lit(sheet_info['language']).alias('language')
    )

    return ActionsheetView(info=sheet_info, data=sheet_data)


def _process_header(data: dict, content_id: str) -> dict:
    assert 'name' in data, f'{content_id}: no name defined'
    assert_name(data['name'], content_id)

    assert 'parent' in data, f'no parent defined'
    assert isinstance(data['parent'], str), f'parent must be str'

    assert 'language' in data, f'no language defined'
    assert isinstance(data['language'], str), f'language must be str'
    assert data['language'], f'language is empty'

    assert 'title' in data, f'no title defined'
    assert isinstance(data['title'], str), f'title must be str'
    assert data['title'], f'title is empty'

    assert 'description' not in data or isinstance(data['description'], str), \
        f'description must be str'

    assert 'details' not in data or isinstance(data['details'], str), f'details must be str'

    if 'keywords' in data:
        assert_keywords(data['keywords'])
        data['keywords'] = list(set(data['keywords']))

    sheet_info = {k: data[k] for k in data.keys() if k in header_keys}
    return sheet_info


def _process_body(content: dict, name: str, id: str) -> pl.DataFrame:
    return _process_entries(content, id=id, parent_entry=dict(), parent_section='')


def _process_entries(
        content: dict,
        id: str,
        parent_entry: dict,
        parent_section: str
) -> pl.DataFrame:
    df = pl.DataFrame()

    entries = _get_entries(content)

    for entry in entries:
        assert entry not in entry_keys, \
            f'''The entry name "{entry}" in section "{id}" is a reserved field.
            Suggested fix: use "_{entry}", or rename.'''

    for entry_name in entries:
        name = entry_name.lstrip('_')
        entry_id = id + '.' + name if id else name
        entry_dict = _process_entry(
            data=content[entry_name],
            name=name,
            id=entry_id,
            parent_data=parent_entry,
            parent_entry=parent_section
        )

        df2 = _process_entries(
            content=content[entry_name],
            id=entry_id,
            parent_entry=entry_dict,
            parent_section=entry_id if entry_dict['type'] == 'section' else parent_section
        )

        df = pl.concat([df, pl.DataFrame(entry_dict), df2], how='diagonal_relaxed')

    return df


def _get_entries(content: dict) -> list[str]:
    return [k for k in content if isinstance(content[k], dict)]


def _process_entry(
        data: dict,
        name: str,
        id: str,
        parent_data: dict,
        parent_entry: str
) -> dict:
    for k in reserved_keys:
        assert k not in data, f'reserved field "{k}" used in entry {id}'

    entry_dict = {k: data[k] for k in data.keys() if k in entry_keys}

    is_virtual = len(entry_dict) == 0
    is_section = 'section' in entry_dict
    is_action = 'action' in entry_dict
    is_solution = not is_action and 'code' in entry_dict

    assert sum([is_virtual, is_section, is_action, is_solution]) == 1, \
        f'entry {id} is ambiguous; invalid set of fields: {", ".join(entry_dict)}'
    assert is_solution ^ (is_section or is_action or is_virtual)

    entry_dict['entry'] = id
    entry_dict['parent_entry'] = parent_entry

    if is_action:
        return _process_action(entry_dict, name=name, id=id)
    elif is_solution:
        return _process_solution(entry_dict, name=name, id=id, parent_entry=parent_data)
    elif is_section:
        return _process_section(entry_dict, name=name, id=id)
    elif is_virtual:
        return _process_virtual_section(entry_dict, name=name, id=id)


def _process_section(entry: dict, name: str, id: str) -> dict:
    if 'section' in entry:
        assert isinstance(entry['section'], str), f'"section" must be str for entry {id}'
        assert entry['section'], f'no text for "section" defined for entry {id}'
    else:
        entry['section'] = name.capitalize()

    entry['type'] = 'section'
    entry['title'] = entry.pop('section')
    return entry


def _process_virtual_section(entry: dict, name: str, id: str) -> dict:
    entry['type'] = 'part'
    return entry


def _process_action(entry: dict, name: str, id: str) -> dict:
    assert 'action' in entry, f'no "action" defined for entry {id}'
    assert isinstance(entry['action'], str), f'"action" must be str for entry {id}'
    assert entry['action'], f'no text for "action" defined for entry {id}'

    assert 'code' in entry, f'no "code" defined for entry {id}'
    assert isinstance(entry['code'], str), f'"code" must be str for entry {id}'
    assert entry['code'], f'no text for "code" defined for entry {id}'

    entry['type'] = 'action'
    entry['title'] = entry.pop('action')
    return entry


def _process_solution(entry: dict, name: str, id: str, parent_entry: dict) -> dict:
    assert parent_entry, f'empty parent action entry for solution {id}'
    assert 'title' in parent_entry, f'missing title for parent of solution {id}'
    entry['title'] = parent_entry['title']
    entry['type'] = 'action'
    return entry


def assert_name(name: any, path: str):
    assert isinstance(name, str), f'{path}: name must be str'
    assert name, f'{path}: name is empty'
    assert '.' not in name, f'{path}: name cannot contain "."'


def assert_keywords(keywords: any):
    assert isinstance(keywords, list), 'keywords must be a list of non-empty strings'
    assert not keywords or all(isinstance(e, str) and e for e in keywords), \
        'keywords must be list of non-empty strings'
