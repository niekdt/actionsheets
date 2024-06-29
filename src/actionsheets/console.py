from actionsheets.sheets import Actionsheets, sheets
from actionsheets.sheet import ActionsheetView
import polars as pl

from rich.console import RenderResult, Group, group
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.tree import Tree
from rich import print

def print_sheets(sheets: Actionsheets, parent_id: str = ''):
    print(_render_sheets(sheets, parent_id=parent_id))

def print_sheet(sheets: Actionsheets, id: str):
    print(_render_sheet(sheets, id))

def print_snippets(snippets: pl.DataFrame, limit=10):
    print(_render_snippets(snippets.head(n=limit)))

def _render_sheets(sheets: Actionsheets, parent_id: str) -> RenderResult:
    tree = Tree(label=parent_id, hide_root=True)
    for sheet_id in sheets.ids(parent_id=parent_id):
        sheet_render = _render_sheet(sheets, id=sheet_id)
        assert sheet_render
        sheet_tree = _render_sheets(sheets, parent_id=sheet_id)
        assert sheet_tree
        tree.add(Group(sheet_render, sheet_tree))

    return tree

def _render_sheet(sheets: Actionsheets, id: str) -> RenderResult:
    info = sheets.sheet_info(id=id)
    view = sheets.sheet_view(id=id)

    markup = f"""# {info['title']}
{info['description']}
{info['details']}
"""

    md = Markdown(
        markup=markup,
        justify='left',
        inline_code_lexer=info['language']
    )

    tree = Tree(id)
    tree.add(md)
    _render_sections(view, section='', tree=tree)

    return tree

def _render_sections(view: ActionsheetView, section: str, tree: Tree) -> None:
    for section_id in view.child_ids(section = section, type = 'section'):
        _render_section(view, section=section_id, tree=tree)

def _render_section(view: ActionsheetView, section: str, tree: Tree) -> None:
    info = view.section_info(section=section)

    # Render section info
    markup = f"""## {info['title']}
{info['description']}
"""

    md = Markdown(
        markup=markup,
        inline_code_lexer=info['language']
    )
    snippets_render = _render_section_snippets(view, section)
    assert snippets_render

    section_group = Group(md, snippets_render)
    section_tree = tree.add(section_group)

    # Render subsections
    _render_sections(view, section=section, tree=section_tree)

def _render_section_snippets(view: ActionsheetView, section: str) -> RenderResult:
    data = view.section_snippets(section=section)
    return _render_snippets(data)

def _render_snippets(data: pl.DataFrame) -> RenderResult:
    table = Table(
        collapse_padding=True, 
        pad_edge=False,
        show_lines=True,
        expand=True
    )

    table.add_column('What', vertical='center', style='cyan', min_width=15)
    table.add_column('Code', justify='left', style='magenta', no_wrap=True, overflow='fold', min_width=40, max_width=100)
    table.add_column('Details', style="green", min_width=10)

    for snippet in data.iter_rows(named=True):
        table.add_row(
            Markdown(snippet['title'], justify='right'), 
            Syntax(snippet['code'], snippet['language'], code_width=120, tab_size=2), 
            Markdown(snippet['details'])
        )
    
    return table

if __name__ == '__main__':
    print('== Actionsheets.console package ==')
    print_sheets(sheets)
