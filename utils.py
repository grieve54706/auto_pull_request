import re

import yaml


def init_config(repo_name):
    base_config = load_config('base')
    repo_config = load_config(repo_name)
    config = dict(base_config)
    config.update(repo_config)
    return config


def load_config(profile):
    file_name = 'resource/config_{}.yaml'.format(profile)
    with open(file_name, 'r') as stream:
        return yaml.load(stream)


def get_tags(all_tag):
    tags = all_tag.split('\n')
    return list(map(lambda tag: trim_tag_hash(tag), tags))


def trim_tag_hash(tag):
    return tag.split('\t', 1)[1]


def find_latest_tag(pattern, tags):
    tags = list(filter(lambda tag: re.search(pattern, tag), tags))

    if len(tags) == 0:
        return None

    tags = sorted(tags, key=lambda tag: find_tag_index(tag), reverse=True)

    return tags[0]


def find_tag_index(tag):
    target_index = 2
    index = tag.split('-')[-target_index]
    try:
        return int(index)
    except ValueError:
        return 0
