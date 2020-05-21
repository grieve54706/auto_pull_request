#!/usr/bin/env python3

import datetime
import logging
import os
from logging.config import fileConfig

import coloredlogs
import git

from utils import init_config, get_tags, find_latest_tag

# Environmental variables
env_name = os.environ['ENV']
log_level = os.environ['LOG_LEVEL']
git_folder_path = os.environ['GIT_FOLDER_PATH']

# logger config
fileConfig('resource/logging_config.ini')
logger = logging.getLogger(__name__)
coloredlogs.install(level=log_level)

repos = ['microservice', 'frontend-ib', 'web-ui']


def main():
    today = datetime.date.today().strftime('%Y%m%d')

    logger.debug('Today is ' + today)

    tags = []

    logger.debug('Start to get lastest tags')

    for repo in repos:

        logger.info('Start to get lastest tag of {}'.format(repo))

        tag = get_lastest_tag(repo, today)

        if tag is not None:
            tags.append(tag)

    joined_tag_str = '\n'.join(tags)

    logger.info('All latest tags \n{}'.format(joined_tag_str))


def get_lastest_tag(repo_name, today):
    logger.debug('Init config')

    config = init_config(repo_name)

    environment = config['environments'][env_name]

    env_key = environment['env_key'][repo_name]

    tag_re_patten = config['tag_re_patten']

    logger.debug('Searched tag patten is {}'.format(tag_re_patten))

    git_path = git_folder_path + repo_name

    logger.debug('Git path is {}'.format(git_path))

    logger.debug('Init repo')

    repo = git.Repo.init(path=git_path)

    repo.git.fetch()

    logger.debug('Fetch remote tags')

    all_tag = repo.git.ls_remote('--tags')

    tags = get_tags(all_tag)

    logger.debug('Start to find latest tag')

    tag_re_patten = tag_re_patten.format(env_key, today)

    tag_name = find_latest_tag(tag_re_patten, tags)

    if tag_name is None:
        logger.warning('Can\'t find matched tag of {}. Maybe no tag today, or check tag patten.'.format(repo_name))
        return None

    logger.info('The latest tag of {} is {}'.format(repo_name, tag_name))

    return tag_name


if __name__ == '__main__':
    main()
