import tomllib
import polars as pl

header_keys = ('name', 'language', 'parent', 'title', 'description', 'details', 'code')
section_keys = ('section', 'description', 'details', 'code')
solution_keys = ('code', 'details')
action_keys = tuple(['what', 'description'] + list(solution_keys))
entry_keys = tuple(set(section_keys + action_keys + solution_keys))

def parse_toml(path) -> tuple[dict, pl.DataFrame]:
    with open(path) as file:
        file_content = file.read()
        content = tomllib.loads(file_content)

    assert content, f'{path} yielded empty content (None)'

    # Process header content
    header_dict = _process_header(content, path)

    print(f'\tParse topic: {header_dict["name"]}')

    # Process sections & snippets
    df = _process_body(content, name=content['name'], id=content['name'])

    return header_dict, df
    

def _process_header(content: dict, path) -> dict:
    assert 'name' in content, f'{path}: no name defined'
    assert isinstance(content['name'], str), f'{path}: name must be str'
    assert content['name'], f'{path}: name is empty'

    assert 'parent' in content, f'no parent defined'
    assert isinstance(content['parent'], str), f'parent must be str'

    assert 'language' in content, f'no language defined'
    assert isinstance(content['language'], str), f'language must be str'
    assert content['language'], f'language is empty'

    assert 'title' in content, f'no title defined'
    assert isinstance(content['title'], str), f'title must be str'
    assert content['title'], f'title is empty'

    assert 'description' not in content or isinstance(content['description'], str), f'description must be str'
    assert 'details' not in content or isinstance(content['details'], str), f'details must be str'
        
    return {k: content[k] for k in content.keys() if k in header_keys}


def _process_body(content: dict, name: str, id: str) -> pl.DataFrame:
    return _process_entries(content, id=id, parent_entry=dict(), depth=1)


def _process_entries(content: dict, id: str, parent_entry: dict, depth: int) -> pl.DataFrame:
    print(f'process_entries for id {id}')
    df = pl.DataFrame()
    
    entries = _get_entries(content)
    for entry_name in entries:
        entry_id = id + '.' + entry_name
        entry_dict = _process_entry(content[entry_name], name = entry_name, id = entry_id, parent_entry=parent_entry)
        entry_dict['depth'] = depth

        df2 = _process_entries(content[entry_name], id=entry_id, parent_entry=entry_dict, depth=depth + 1)
        
        df = pl.concat([df, pl.DataFrame(entry_dict), df2], how='diagonal_relaxed')

    print(f'done with id {id}')
    return df


def _get_entries(content: dict) -> list[str]:
        return [k for k in content if isinstance(content[k], dict)]
    

def _process_entry(content: dict, name: str, id: str, parent_entry: dict) -> dict:
    assert 'name' not in content, f'reserved field "name" used in entry {id}'
    assert 'id' not in content, f'reserved field "id" used in entry {id}'
    assert 'depth' not in content, f'reserved field "depth" used in entry {id}'

    entry_dict = {k: content[k] for k in content.keys() if k in entry_keys}

    is_virtual = len(entry_dict) == 0
    is_section = 'section' in entry_dict
    is_action = 'what' in entry_dict
    is_solution = not is_action and 'code' in entry_dict

    assert sum([is_virtual, is_section, is_action, is_solution]) == 1, f'ambigious entry with multiple possible types for entry {id}'
    assert is_solution ^ (is_section or is_action or is_virtual)

    entry_dict['name'] = name
    entry_dict['id'] = id

    if is_action:
        return _process_action(entry_dict, name=name, id=id)
    elif is_solution:
        return _process_solution(entry_dict, name=name, id=id, parent_entry=parent_entry)
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
    assert 'what' in entry, f'no "what" defined for entry {id}'
    assert isinstance(entry['what'], str), f'"what" must be str for entry {id}'
    assert entry['what'], f'no text for "what" defined for entry {id}'

    assert 'code' in entry, f'no "code" defined for entry {id}'
    assert isinstance(entry['code'], str), f'"code" must be str for entry {id}'
    assert entry['code'], f'no text for "code" defined for entry {id}'

    entry['type'] = 'action'
    entry['title'] = entry.pop('what')
    return entry


def _process_solution(entry: dict, name: str, id: str, parent_entry: dict) -> dict:
    assert parent_entry, f'empty parent action entry for solution {id}'
    entry['title'] = parent_entry['title']
    entry['type'] = 'action'
    return entry
