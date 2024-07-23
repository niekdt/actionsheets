from actionsheets.sheets import Actionsheets, default_sheets
from actionsheets.sheet import ActionsheetView
import polars as pl

from rich.console import RenderResult, Group, group
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel
from rich import print, box

_header_color = 'magenta'
_path_color = 'grey50'
_description_color = 'hot_pink'
_details_color = 'cyan'
_action_color = 'sea_green1'
_bg_color2 = 'grey15'


def print_sheets(sheets: Actionsheets, parent_id: str = ''):
    print(_render_sheets(sheets, parent_id=parent_id))


def print_sheet(sheets: Actionsheets, id: str):
    print(_render_sheet(sheets, id))


def print_snippets(snippets: pl.DataFrame, limit=10):
    print(_render_snippets(snippets.head(n=limit)))


@group()
def _render_sheets(sheets: Actionsheets, parent_id: str) -> RenderResult:
    for sheet_id in sheets.sheets(parent=parent_id, nested=False):
        sheet_render = _render_sheet(sheets, id=sheet_id)
        sheets_render = _render_sheets(sheets, parent_id=sheet_id)
        yield Group(sheet_render, sheets_render)


@group()
def _render_sheet(sheets: Actionsheets, id: str) -> RenderResult:
    info = sheets.sheet_info(sheet=id)
    view = sheets.sheet_view(sheet=id)

    sheet_path = ' > '.join([v.capitalize() for v in info['sheet_id'].split('.')])

    yield Panel(
        Text.assemble(
            (Text(info['title'])),
            (' Actionsheet', 'i'),
            '    ',
            (sheet_path, f'{_path_color}')
        ),
        box=box.DOUBLE_EDGE,
        style=_header_color
    )

    if info['description']:
        yield Text('DESCRIPTION', style=f'{_description_color} bold')
        yield Markdown(markup=info['description'], style=_description_color,
                       inline_code_lexer=info['language'])
        yield ''

    if info['details']:
        yield Text('DETAILS', style=f'{_details_color} bold')
        yield Markdown(markup=info['details'], style=_details_color,
                       inline_code_lexer=info['language'])
        yield ''

    yield _render_sections(view, section='')


@group()
def _render_sections(view: ActionsheetView, section: str) -> RenderResult:
    for section_id in view.entries(parent=section, type='section'):
        yield _render_section(view, section=section_id)


@group()
def _render_section(view: ActionsheetView, section: str) -> RenderResult:
    info = view.section_info(section=section)

    sheet_path = ' > '.join([v.capitalize() for v in info['sheet_id'].split('.')])
    parent_path = ' > '.join([v.capitalize() for v in info['parent_section'].split('.')])
    has_snippets = view.section_snippets(section=section).height > 0

    md = Markdown(
        markup=info['description'],
        style=_description_color,
        inline_code_lexer=info['language']
    )
    snippets_group = _render_section_snippets(view, section)
    yield Panel(
        Group(md, snippets_group),
        title=Text.assemble(
            ('' if info['parent_section'] == '' else f' {parent_path} >',
             f'black on {_header_color} bold'),
            (f' {info["title"]} ', f'white on {_header_color} bold'),
            ' ── ',
            (f'Section {section}', 'black on default')
        ),
        title_align='left',
        subtitle='' if not has_snippets else Text.assemble(
            (f'Actionsheet {sheet_path} ', f'{_path_color} italic'),
            ('───', 'white'),
            (f' Section {section}', f'{_path_color} italic')
        ),
        subtitle_align='left'
    )

    # Render subsections
    yield _render_sections(view, section=section)


def _render_section_snippets(view: ActionsheetView, section: str) -> RenderResult:
    data = view.section_snippets(section=section)
    if data.height:
        return _render_snippets(data)
    else:
        return Group()


def _render_snippets(data: pl.DataFrame) -> RenderResult:
    table = Table(
        collapse_padding=False,
        pad_edge=False,
        show_edge=False,
        show_lines=False,
        expand=True,
        row_styles=['', f'on {_bg_color2}']
    )

    table.add_column('Action', style=_action_color, min_width=15)
    table.add_column('Code', no_wrap=True, overflow='fold', min_width=40, max_width=100)
    table.add_column('Details', style=f'{_details_color} i', min_width=10)

    for snippet in data.iter_rows(named=True):
        table.add_row(
            Markdown(snippet['title']),
            Syntax(
                code=snippet['code'],
                lexer=snippet['language'],
                code_width=120,
                tab_size=2,
                background_color='default' if table.row_count % 2 == 0 else _bg_color2
            ),
            Markdown(snippet['details']),
            style='' if table.row_count % 2 == 0 else f'on {_bg_color2}'
        )

    return table


if __name__ == '__main__':
    print('== Actionsheets.console package ==')
    print_sheets(default_sheets())
