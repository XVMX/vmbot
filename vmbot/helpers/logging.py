# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import logging

from .exceptions import APIError
from . import api

import config


class GitHubIssueHandler(logging.Handler):
    """Emit logged messages as issues on GitHub."""

    headers = {'Accept': "application/vnd.github.v3+json"}
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
            r = api.request_api(self.url, params=params, headers=self.headers)
            issues.extend(i['title'] for i in r.json())
            while 'next' in r.links:
                r = api.request_api(r.links['next']['url'], headers=self.headers)
                issues.extend(i['title'] for i in r.json())
        except APIError:
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
            r = api.request_api(self.url, json=payload, auth=self.auth,
                                headers=self.headers, method="POST")
        except APIError:
            self.handleError(record)
        else:
            if r.status_code == 201:
                self.known_issues.add(payload['title'])


def setup_logging(main_handler):
    logger = logging.getLogger("vmbot")
    logger.setLevel(logging.DEBUG)
    cc_logger = logging.getLogger("cachecontrol")
    cc_logger.setLevel(logging.WARNING)

    main_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s",
                                                "%Y-%m-%d %H:%M:%S"))
    main_handler.setLevel(config.LOGLEVEL)
    logger.addHandler(main_handler)
    cc_logger.addHandler(main_handler)

    gh = config.GITHUB
    if gh['user'] and gh['token']:
        esi_handler = GitHubIssueHandler("XVMX", "VMBot", gh['user'], gh['token'])
        esi_handler.setLevel(logging.WARNING)
        logging.getLogger("vmbot.helpers.api.esi").addHandler(esi_handler)

    return logger
