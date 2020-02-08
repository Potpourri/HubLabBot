"""Module for webhooks setup in GitLab repo."""
from typing import List, Dict, Optional
from urllib.parse import urljoin

from gitlab import Gitlab  # type: ignore
import gitlab.v4.objects as gl_types  # type: ignore

from hublabbot.const import GITLAB_ENDPOINT
from hublabbot.util import JsonDict
from hublabbot.settings import RepoOptions


def _find(hooks: List[gl_types.ProjectHook], url: str) -> Optional[gl_types.ProjectHook]:
	for hook in hooks:
		if hook.url == url:
			return hook
	return None


def _create(project: gl_types.Project, hook_url: str, secret: str, events: Dict[str, bool]) -> None:
	hook_cfg: JsonDict = {
		'url': hook_url,
		'token': secret,
		**events}
	project.hooks.create(hook_cfg)
	print(f'GL:{project.path_with_namespace}: Hook created with events: {events}.')


def _update(hook: gl_types.ProjectHook, secret: str, events: Dict[str, bool],
            repo_path: str) -> None:
	for event, value in events.items():
		setattr(hook, event, value)
	hook.token = secret
	hook.save()
	print(f'GL:{repo_path}: Hook updated with events: {events}.')


def _delete(hook: gl_types.ProjectHook, repo_path: str) -> None:
	hook.delete()
	print(f'GL:{repo_path}: Hook deleted.')


def configure(gl_base_url: str, token: str, secret: str, bot_base_url: str,
              repo_options: RepoOptions) -> None:
	"""Configure webhooks in GitLab repo."""
	events = {
		'push_events': False,
		'issues_events': False,
		'confidential_issues_events': False,
		'merge_requests_events': False,
		'tag_push_events': False,
		'note_events': False,
		'job_events': False,
		'pipeline_events': repo_options.gl_auto_cancel_pipelines,
		'wiki_page_events': False
	}
	hook_url = urljoin(bot_base_url, GITLAB_ENDPOINT)
	gitlab = Gitlab(gl_base_url, private_token=token)
	project = gitlab.projects.get(repo_options.gl_repo_path)
	hooks = project.hooks.list()
	hook = _find(hooks, hook_url)
	if events['pipeline_events'] is True:
		if hook is None:
			_create(project, hook_url, secret, events)
		else:
			events_is_equal = True
			for event, value in events.items():
				events_is_equal &= hook.attributes[event] == value
			if not events_is_equal:
				_update(hook, secret, events, repo_options.gl_repo_path)

	else:
		if hook is not None:
			_delete(hook, repo_options.gl_repo_path)
