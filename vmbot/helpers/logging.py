# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import logging

import requests

import config


class GitHubIssueHandler(logging.Handler):
    headers = {'Accept': "application/vnd.github.v3+json", 'User-Agent': "XVMX VMBot"}
    known_issues = set()

    def __init__(self, owner, repo, user, access_token):
        super(GitHubIssueHandler, self).__init__()

        self.url = "https://api.github.com/repos/{}/{}/issues".format(owner, repo)
        self.auth = (user, access_token)

    def _detect_duplicate(self, title, labels=None):
        if title in self.known_issues:
            return True

        params = {'state': "open", 'sort': "created", 'direction': "desc"}
        if labels:
            params['labels'] = ','.join(labels)

        issues = []
        try:
            r = requests.get(self.url, params=params, headers=self.headers)
            r.raise_for_status()
            issues.extend(i['title'] for i in r.json())
            while 'next' in r.links:
                r = requests.get(r.links['next']['url'], headers=self.headers)
                r.raise_for_status()
                issues.extend(i['title'] for i in r.json())
        except requests.RequestException:
            pass

        self.known_issues.update(issues)
        return title in self.known_issues

    def emit(self, record):
        payload = {}
        body = self.format(record)

        if '\n' in body:
            payload['title'], payload['body'] = body.split('\n', 1)
        else:
            payload['title'] = body

        if hasattr(record, "gh_labels"):
            payload['labels'] = record.gh_labels

        if self._detect_duplicate(payload['title'], payload.get('labels', None)):
            return

        try:
            r = requests.post(self.url, json=payload, auth=self.auth, headers=self.headers)
        except requests.RequestException:
            self.handleError(record)
        else:
            if r.status_code == 201:
                self.known_issues.add(payload['title'])


def setup_logging(main_handler):
    logger = logging.getLogger("vmbot")
    logger.setLevel(logging.DEBUG)

    main_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s",
                                                "%Y-%m-%d %H:%M:%S"))
    main_handler.setLevel(config.LOGLEVEL)
    logger.addHandler(main_handler)

    gh = config.GITHUB
    if gh['user'] and gh['token']:
        esi_handler = GitHubIssueHandler("XVMX", "VMBot", gh['user'], gh['token'])
        esi_handler.setLevel(logging.WARNING)
        logging.getLogger("vmbot.helpers.api.esi").addHandler(esi_handler)

    return logger
