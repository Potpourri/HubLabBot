"""Module for webhooks setup in GitHub repo."""
from typing import List, Optional
from urllib.parse import urljoin

import github.Repository as ghr  # type: ignore
import github.PaginatedList as ghp  # type: ignore
import github.Hook as ghh  # type: ignore
from github import Github

from hublabbot.const import GITHUB_ENDPOINT
from hublabbot.settings import RepoOptions


def _find(hooks: ghp.PaginatedList, hook_url: str) -> Optional[ghh.Hook]:
	for hook in hooks:
		if hook.config['url'] == hook_url:
			return hook
	return None


def _create(repo: ghr.Repository, hook_url: str, secret: str, events: List[str]) -> None:
	config = {
		'url': hook_url,
		'secret': secret,
		'content_type': 'json'
	}
	repo.create_hook('web', config, events, active=True)
	print(f'GH:{repo.full_name}: Hook created with events: {events}.')


def _update(hook: ghh.Hook, secret: str, events: List[str], repo_path: str) -> None:
	config = {
		'url': hook.config['url'],
		'secret': secret,
		'content_type': 'json'
	}
	hook.edit('web', config, events, active=True)
	print(f'GH:{repo_path}: Hook updated with events: {events}.')


def _delete(hook: ghh.Hook, repo_path: str) -> None:
	hook.delete()
	print(f'GH:{repo_path}: Hook deleted.')


def configure(token: str, secret: str, base_url: str, repo_options: RepoOptions) -> None:
	"""Configure webhooks in GitHub repo."""
	events: List[str] = []
	if repo_options.gh_auto_merge_pr is not None or repo_options.gh_show_gitlab_ci_fail is not None:
		events.append('status')
	if repo_options.gl_auto_delete_branches:
		events.append('delete')
	if repo_options.gh_gitlab_ci_for_external_pr:
		events.append('pull_request')
	hook_url = urljoin(base_url, GITHUB_ENDPOINT)
	github = Github(token)
	repo = github.get_repo(repo_options.gh_repo_path, lazy=True)
	hook = _find(repo.get_hooks(), hook_url)
	if len(events) > 0:
		if hook is None:
			_create(repo, hook_url, secret, events)
		else:
			if sorted(hook.events) != sorted(events) or not hook.active:
				_update(hook, secret, events, repo_options.gh_repo_path)
	else:
		if hook is not None:
			_delete(hook, repo_options.gh_repo_path)
