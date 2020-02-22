"""Module for settings-related code."""
# WORKAROUND: https://mypy.readthedocs.io/en/stable/common_issues.html#using-classes-that-are-generic-in-stubs-but-not-at-runtime  # noqa: E501
from __future__ import annotations
from typing import Any, List, Optional
from dataclasses import dataclass
import os
import json
from pathlib import Path

from github import Github  # type: ignore

from hublabbot.util import set_frozen_attr, JsonDict


@dataclass(frozen=True)
class GithubAutoMergeOption:
	r"""Immutable record to `gh_auto_merge_pr` option.

	Attributes:
		authors_white_list: List of authors whose PR can be auto-merged. Your login and your bot's
			login always in this list.
		delay: Delay before do auto-merge. Default is `60` seconds.
		required_label_name: Name of label required for PR to be auto-merged. Default is `'auto-merge'`.
		required_label_color: Label color in hex format. Default is `'#852576'`.
		required_label_description: Label description.
			Default is `'HubLabBot\'s "gh_auto_merge_pr" required label'`.

	"""

	authors_white_list: List[str]
	delay: int
	required_label_name: str
	required_label_color: str
	required_label_description: str
	_gh_login: str
	_gh_bot_login: str

	def __post_init__(self) -> None:
		"""Validate fields and set defaults."""
		if self.authors_white_list is None:
			set_frozen_attr(self, 'authors_white_list', [])
		self.authors_white_list.extend([self._gh_login, self._gh_bot_login])
		if self.delay is None:
			set_frozen_attr(self, 'delay', 60)
		if self.required_label_name in (None, ''):
			set_frozen_attr(self, 'required_label_name', 'auto-merge')
		if self.required_label_color in (None, ''):
			set_frozen_attr(self, 'required_label_color', '#852576')
		if self.required_label_description in (None, ''):
			set_frozen_attr(self, 'required_label_description',
			                'HubLabBot\'s "gh_auto_merge_pr" required label')


@dataclass(frozen=True)
class GithubShowGitlabCIFailOption:
	"""Immutable record to `gh_show_gitlab_ci_fail` option.

	Attributes:
		max_lines: Maximum length of short log. Default is `25`.

	"""

	max_lines: int

	def __post_init__(self) -> None:
		"""Validate fields and set defaults."""
		if self.max_lines is None:
			set_frozen_attr(self, 'max_lines', 25)


@dataclass(frozen=True, init=False)
class RepoOptions:
	"""Immutable record to store repo options.

	Attributes:
		gh_repo_path: Path like {namespace}/{repo name} in GitHub.
		gl_repo_path: Path like {namespace}/{repo name} in GitLab.
		gh_auto_merge_pr: `GithubAutoMergeOption`: Merge Pull Request if: GitLab CI passed,
			no conflicts found, has required label and author in white list.
			If `None`, it is disabled.
		gh_show_gitlab_ci_fail: `GithubShowGitlabCIFailOption`: Post comment with GitLab CI fail-report
			in PR's thread. If `None`, it is disabled.
		gh_gitlab_ci_for_external_pr: Enable GitLab CI for external Pull Requests.
		gl_auto_cancel_pipelines: Cancel all prevarious Pipelines with the same branch,
			if started new one.
		gl_auto_delete_branches: Delete branch in GitLab when she deleted in GitHub.
		gl_delete_pipeline_btn: With [userscript](https://github.com/Potpourri/HubLabBot/blob/master/userscript/gitlab_delete_pipeline_button.user.js)
			add delete buttons on Pipelines list page in [gitlab.com](https://gitlab.com).

	"""  # noqa: E501

	gh_repo_path: str
	gl_repo_path: str
	gh_auto_merge_pr: Optional[GithubAutoMergeOption]
	gh_show_gitlab_ci_fail: Optional[GithubShowGitlabCIFailOption]
	gh_gitlab_ci_for_external_pr: bool
	gl_auto_cancel_pipelines: bool
	gl_auto_delete_branches: bool
	gl_delete_pipeline_btn: bool

	def __init__(self, options: JsonDict, gh_login: str, gh_bot_login: str):
		"""Creates from `options` dict.

		Values can be: 'false' or doesn't exist - option disabled, 'true' - option enabled.

		`gh_auto_merge_pr` and `gh_show_gitlab_ci_fail` can be: 'false' or JSON dict
		or '{}' (enabled with defaults).

		Args:
			options: JSON dict.
			gh_login: Your GitHub login.
			gh_bot_login: Your bot's GitHub login.

		Raises:
			ValueError: An error occurred reading unknown option.

		"""
		set_frozen_attr(self, 'gh_repo_path', None)
		set_frozen_attr(self, 'gl_repo_path', None)
		set_frozen_attr(self, 'gh_auto_merge_pr', None)
		set_frozen_attr(self, 'gh_show_gitlab_ci_fail', None)
		set_frozen_attr(self, 'gh_gitlab_ci_for_external_pr', False)
		set_frozen_attr(self, 'gl_auto_cancel_pipelines', False)
		set_frozen_attr(self, 'gl_auto_delete_branches', False)
		set_frozen_attr(self, 'gl_delete_pipeline_btn', False)
		for option, value in options.items():
			if option == 'gh_repo_path':
				set_frozen_attr(self, 'gh_repo_path', value)
			elif option == 'gl_repo_path':
				set_frozen_attr(self, 'gl_repo_path', value)
			elif option == 'gh_auto_merge_pr':
				if value is False:
					continue
				set_frozen_attr(self, 'gh_auto_merge_pr', GithubAutoMergeOption(
					authors_white_list=value.get('authors_white_list'),
					delay=value.get('delay'),
					required_label_name=value.get('required_label_name'),
					required_label_color=value.get('required_label_color'),
					required_label_description=value.get('required_label_description'),
					_gh_login=gh_login,
					_gh_bot_login=gh_bot_login))
			elif option == 'gh_show_gitlab_ci_fail':
				if value is False:
					continue
				set_frozen_attr(self, 'gh_show_gitlab_ci_fail', GithubShowGitlabCIFailOption(
					max_lines=value.get('max_lines')))
			elif option == 'gh_gitlab_ci_for_external_pr':
				set_frozen_attr(self, 'gh_gitlab_ci_for_external_pr', value)
			elif option == 'gl_auto_cancel_pipelines':
				set_frozen_attr(self, 'gl_auto_cancel_pipelines', value)
			elif option == 'gl_auto_delete_branches':
				set_frozen_attr(self, 'gl_auto_delete_branches', value)
			elif option == 'gl_delete_pipeline_btn':
				set_frozen_attr(self, 'gl_delete_pipeline_btn', value)
			else:
				raise ValueError(f'Unknown repo option: "{option}"!')

	def __post_init__(self) -> None:
		"""Validate fields."""
		if (self.gh_auto_merge_pr is None
		    and self.gh_show_gitlab_ci_fail is None
		    and not self.gh_gitlab_ci_for_external_pr
		    and not self.gl_auto_cancel_pipelines
		    and not self.gl_auto_delete_branches
		    and not self.gl_delete_pipeline_btn):
			raise ValueError(
				'At least one repo option must be enabled: gh_auto_merge_pr, '
				+ 'gh_show_gitlab_ci_fail, gh_gitlab_ci_for_external_pr, '
				+ 'gl_auto_cancel_pipelines, gl_auto_delete_branches, gl_delete_pipeline_btn!')
		if self.gh_repo_path is None:
			raise ValueError('Required repo option gh_repo_path not found!')
		if self.gl_repo_path is None:
			raise ValueError('Required repo option gl_repo_path not found!')


RepoList = List[RepoOptions]
"""Type - list of `RepoOptions`."""


@dataclass(frozen=True, init=False)
class HubLabBotSettings:
	"""Immutable record to store all HubLabBot settings.

	Attributes:
		assets_path: Path to assets dir. Automatically set.
		base_url: Reads from settings file. URL of your HubLabBot instance.
		port: Reads from environ `HUBLABBOT_PORT`. Default is `8080`.
		gh_bot_token: Reads from environ `GITHUB_BOT_TOKEN`. Bot GitHub Personal access token.
		gh_bot_login: Bot's GitHub login. Automatically set.
		gh_bot_profile_url: URL to bot's GitHub profile. Automatically set.
		gh_bot_avatar_url: URL to bot's GitHub avatar. Automatically set.
		gh_token: Reads from environ `GITHUB_TOKEN`. Your GitHub Personal access token.
		gh_login: Your GitHub login. Automatically set.
		gh_secret: Reads from environ `GITHUB_SECRET`. Secret phrase to authorize requests to bot.
		gl_base_url: Reads from settings file. URL of GitLab instance. Default is `'https://gitlab.com'`.
		gl_token: Reads from environ `GITLAB_TOKEN`. Your GitLab Personal access token.
		gl_secret: Reads from environ `GITLAB_SECRET`. Secret phrase to authorize requests to bot.
		repos: List of `RepoOptions`, for which bot is enabled.

	"""

	assets_path: Path
	base_url: str
	port: int
	gh_bot_token: str
	gh_bot_login: str
	gh_bot_profile_url: str
	gh_bot_avatar_url: str
	gh_token: str
	gh_login: str
	gh_secret: str
	gl_base_url: str
	gl_token: str
	gl_secret: str
	repos: RepoList

	def __init__(self, settings_path: os.PathLike[Any], assets_path: os.PathLike[Any]):
		"""Creates from `settings_path`.

		Args:
			settings_path: Path to HubLabBot settings file (JSON).
			assets_path: Path to assets dir.

		"""
		with open(settings_path) as f:
			settings_json = json.load(f)
		set_frozen_attr(self, 'assets_path', Path(assets_path))
		set_frozen_attr(self, 'base_url', settings_json['base_url'])
		set_frozen_attr(self, 'port', int(os.environ.get('HUBLABBOT_PORT', 8080)))
		set_frozen_attr(self, 'gh_bot_token', os.environ['GITHUB_BOT_TOKEN'])
		github_bot = Github(self.gh_bot_token)
		bot = github_bot.get_user()
		set_frozen_attr(self, 'gh_bot_login', bot.login)
		set_frozen_attr(self, 'gh_bot_profile_url', bot.html_url)
		set_frozen_attr(self, 'gh_bot_avatar_url', bot.avatar_url)
		set_frozen_attr(self, 'gh_token', os.environ['GITHUB_TOKEN'])
		github = Github(self.gh_token)
		login = github.get_user().login
		set_frozen_attr(self, 'gh_login', login)
		set_frozen_attr(self, 'gh_secret', os.environ['GITHUB_SECRET'])
		set_frozen_attr(self, 'gl_base_url',
		                settings_json.get('gl_base_url', 'https://gitlab.com'))
		set_frozen_attr(self, 'gl_token', os.environ['GITLAB_TOKEN'])
		set_frozen_attr(self, 'gl_secret', os.environ['GITLAB_SECRET'])
		repos: RepoList = []
		for options in settings_json['repos']:
			repos.append(RepoOptions(options, self.gh_login, self.gh_bot_login))
		set_frozen_attr(self, 'repos', repos)

	def get_repo_by_github(self, repo_path: str) -> RepoOptions:
		"""Returns `RepoOptions` by `repo_path` in GitHub.

		Raises:
			RuntimeError: An error occurred when `RepoOptions` with this `repo path` not found.

		"""
		for repo_options in self.repos:
			if repo_options.gh_repo_path == repo_path:
				return repo_options
		raise RuntimeError(f'Repo options with path GH:{repo_path} not found!')

	def get_repo_by_gitlab(self, repo_path: str) -> RepoOptions:
		"""Returns `RepoOptions` by `repo_path` in GitLab.

		Raises:
			RuntimeError: An error occurred when `RepoOptions` with this `repo_path` not found.

		"""
		for repo_options in self.repos:
			if repo_options.gl_repo_path == repo_path:
				return repo_options
		raise RuntimeError(f'Repo options with path GL:{repo_path} not found!')
