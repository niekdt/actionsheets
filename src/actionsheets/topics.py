from importlib import resources
import polars as pl

from actionsheets.topic import parse_toml

class Topics:
    def __init__(self, topics: pl.DataFrame, data: pl.DataFrame):
        self.topics = topics
        self.data = data

    @staticmethod
    def parse_topics():
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

        topic_headers = []
        topic_data_list = []
        for file in files:
            print(f'Parsing file {file}...')
            topic_header, topic_data = parse_toml(file)
            print(f'Parsed topic: {topic_header["name"]}')

            topic_headers.append(topic_header)
            topic_data_list.append(topic_data)

        topics = pl.DataFrame(topic_headers)
        data = pl.concat(topic_data_list, how='diagonal')

        print('\n\nHEADERS:')
        print(topics)
        print('\n\nDATA:')
        print(data)

        return Topics(topics, data)
                
        
topics = Topics.parse_topics()
