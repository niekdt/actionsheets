# https://www.mkdocs.org/dev-guide/plugins/#events
import os

from mksheet import generate_all_sheets


def on_serve(server, config, builder):
    print('== Actionsheets hook ==')
    print(f'CWD: {os.getcwd()}')
    print(config['docs_dir'])

    generate_all_sheets(path=config['docs_dir'])
