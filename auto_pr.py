#!/usr/bin/env python

import datetime
import json
import logging
import os
import re
import sys
from logging.config import fileConfig

import coloredlogs
import git

from exception import BitbucketException, TagNotFoundException, BranchIsExistException, NoramlMessageException
from service import RequestService
from utils import init_config, get_tags, find_latest_tag

# Environmental variables
git_folder_path = os.environ['GIT_FOLDER_PATH']
env_name = os.environ['ENV']
source_branch = os.environ['SOURCE_BRANCH']
log_level = os.environ['LOG_LEVEL']
auth = {
    'id': os.environ['BITBUCKET_CREDS_USR'],
    'pxd': os.environ['BITBUCKET_CREDS_PSW']
}

# logger config
fileConfig('resource/logging_config.ini')
logger = logging.getLogger(__name__)
coloredlogs.install(level=log_level)


def main(repo_name):
    logger.debug('init config')

    config = init_config(repo_name)

    environment = config['environments'][env_name]

    env_key = environment['env_key'][repo_name]

    today = datetime.date.today().strftime('%Y%m%d')

    logger.debug('get today is ' + today)

    git_path = git_folder_path + repo_name

    logger.info('git path is ' + git_path)

    logger.debug('init repo')

    repo = git.Repo.init(path=git_path)

    # Need prune for branch is deleted then created with same name.
    repo.git.fetch('--prune')

    logger.debug('get remote tags')

    all_tag = repo.git.ls_remote('--tags')

    tags = get_tags(all_tag)

    logger.debug('find latest tag')

    tag_re_patten = config['tag_re_patten']

    tag_re_patten = tag_re_patten.format(env_key, today)

    tag_name = find_latest_tag(tag_re_patten, tags)

    if tag_name is None:
        raise TagNotFoundException()

    logger.info('latest tag is ' + tag_name)

    logger.debug('find latest branch')

    branches = repo.git.branch('-r').split('\n')

    merged_branch_name_re_patten = config['merged_branch_name_re_patten'].format(env_key, today)

    latest_branch = find_latest_branch(merged_branch_name_re_patten, branches)

    branch_index = get_branch_index(latest_branch)

    new_branch_name = config['new_branch_name_patten'].format(env_key, today, branch_index)

    logger.info('new branch is ' + new_branch_name)

    logger.debug('check branch is exists or not')

    is_exists = some(branches, lambda b: new_branch_name in b)

    if is_exists:
        raise BranchIsExistException(new_branch_name)
    else:
        logger.debug('branch is not exists')

    logger.debug('create branch')

    repo.git.checkout(tag_name, '-b', new_branch_name)

    logger.debug('push branch')

    repo.git.push('origin', new_branch_name)

    logger.debug('checkout to dev')

    repo.git.checkout(source_branch)

    logger.debug('get branch diff commit')

    all_log = repo.git.log('origin/{}..origin/{}'.format(config['uat_branch'], new_branch_name), '--oneline',
                           '--no-merges')

    logger.debug('build pull request desc')

    pr_desc = build_pr_desc(all_log)

    logger.debug('create request service')

    request_service = RequestService(config['host'], config['headers'], auth)

    logger.debug('get reviewers')

    uat_branch = config['uat_branch']

    default_reviewers_api = config['default_reviewers_api'].format(repo_name)

    reviewers = get_reviewers(request_service, default_reviewers_api, uat_branch, new_branch_name)

    logger.debug('build pull request obj')

    pr_obj = build_pr_obj(new_branch_name, uat_branch, pr_desc, reviewers)

    logger.debug('post to create pull request')

    pull_requests_api = config['pull_requests_api'].format(repo_name)

    rs = post_pr(request_service, pull_requests_api, pr_obj)

    if rs.status_code != 201:
        logger.error('{} {} create pull request failed.'.format(repo_name, new_branch_name))
        status_code = rs.status_code
        result = json.loads(rs.text, encoding='utf-8')
        message = result['errors'][0]['message']
        raise BitbucketException(status_code, message, new_branch_name)

    logger.info('create pull request success.')
    logger.info('finish')


def pretty_json_str(json_str):
    return json.dumps(json.loads(json_str), indent=4, sort_keys=True)


def get_reviewers(request_service, default_reviewers_api, uat_branch, new_branch_name):
    rs = request_service.get(default_reviewers_api)

    status_code = rs.status_code

    if status_code != 200:
        logger.error('get default reviewers failed.')
        result = json.loads(rs.text, encoding='utf-8')
        message = result['errors'][0]['message']
        raise BitbucketException(status_code, message, new_branch_name)

    result = rs.json()

    reviewer_group = find_reviewer_group_by_target_branch(result, uat_branch)

    return get_reviewers_name(reviewer_group['reviewers'])


def find_reviewer_group_by_target_branch(result, branch_name):
    return next(r for r in result if r['targetRefMatcher']['displayId'] == branch_name)


def get_reviewers_name(reviewer_objs):
    reviewer_objs = filter(lambda reviewer: reviewer['active'], reviewer_objs)
    return list(map(lambda reviewer: reviewer['name'], reviewer_objs))


def build_pr_obj(from_branch, to_branch, pr_desc, reviewers):
    title = ' '.join(from_branch.split('-'))
    from_ref_id = 'refs/heads/{}'.format(from_branch)
    to_ref_id = 'refs/heads/{}'.format(to_branch)
    reviewers_objs = list(map(lambda r: build_reviewer_obj(r), reviewers))
    return {
        'title': title,
        'description': pr_desc,
        'state': 'OPEN',
        'open': True,
        'closed': False,
        'fromRef': {
            'id': from_ref_id
        },
        'toRef': {
            'id': to_ref_id
        },
        'locked': False,
        'reviewers': reviewers_objs
    }


def build_reviewer_obj(reviewer_name):
    return {
        'user': {
            'name': reviewer_name
        }
    }


def post_pr(request_service, pull_requests_api, pr_obj):
    return request_service.post(pull_requests_api, json.dumps(pr_obj))


def find_latest_branch(pattern, branches):
    branches = list(filter(lambda b: re.search(pattern, b), branches))
    branches = sorted(branches, key=lambda b: int(b.split('-')[-2]), reverse=True)
    return branches[0] if len(branches) != 0 else None


def get_branch_index(latest_branch):
    if latest_branch is not None:
        branch_chunks = latest_branch.split('-')
        branch_index = branch_chunks[-2]
        new_branch_index = int(branch_index) + 1
        return str(new_branch_index).zfill(2)
    else:
        return '01'


def build_pr_desc(all_log):
    logs = all_log.split('\n')

    pr_desc_arr = list(map(lambda log: format_log(log), logs))

    return '\n'.join(pr_desc_arr)


def format_log(log):
    trim_log = trim_log_hash(log)
    return '* {}'.format(trim_log)


def trim_log_hash(log):
    chunks = log.split(' ', 1)
    if len(chunks) > 2:
        return chunks[1]
    else:
        return ''


def some(list_, pred):
    return any(pred(i) for i in list_)


def rollback_branch(repo_name, new_branch_name):

    git_path = git_folder_path + repo_name

    repo = git.Repo.init(path=git_path)

    logger.warning('delete remote branch')
    repo.git.push('origin', ':' + new_branch_name)

    logger.warning('delete local branch')
    repo.git.branch('-D', new_branch_name)


if __name__ == '__main__':

    input_repo_name = sys.argv[1:][0]

    try:
        main(input_repo_name)
    except BitbucketException as e:
        logger.error('Has exception\nCode: {}\nMessage: {}'.format(e.code, e.message))
        rollback_branch(input_repo_name, e.new_branch_name)
        logger.error('Process is failed')
        raise e
    except NoramlMessageException as e:
        logger.error('Has exception\nMessage: {}'.format(e.message))
        logger.error('Process is failed')
        raise e
