"""Module for GitHub webhook functionality."""
from typing import Optional
import sys
import tempfile
from string import Template
from urllib.parse import urlsplit
from threading import Timer

import github.PullRequest as ghp  # type: ignore
from github import Github
import pygit2
from pyramid.interfaces import IResponse  # type: ignore

from hublabbot.util import JsonDict
from hublabbot.settings import HubLabBotSettings


class RemotePushCallback(pygit2.RemoteCallbacks):
	"""Callback for remote push."""

	def __init__(self, gh_repo_path: str, gl_repo_path: str, pr_num: int):
		self.gh_repo_path = gh_repo_path
		"""Path like {namespace}/{repo name} in GitHub."""
		self.gl_repo_path = gl_repo_path
		"""Path like {namespace}/{repo name} in GitLab."""
		self.pr_num = pr_num
		"""Number of PR."""

	def push_update_reference(self, refname: bytes, message: Optional[bytes]) -> None:
		"""Overrided callback for remote push.

		Args:
			refname: The name of the reference (on the remote).
			message: Rejection message from the remote. If None, the update was accepted.

		"""
		if message is None:
			print(f'GH:{self.gh_repo_path}: PR#{self.pr_num} ({refname.decode("utf-8")})'
			      + f' synced to GL:{self.gl_repo_path}.')
		else:
			print(f'GH:{self.gh_repo_path}: Fail sync PR#{self.pr_num} ({refname.decode("utf-8")})'
			      + f' to GL:{self.gl_repo_path} - "{message.decode("utf-8")}"!', file=sys.stderr)


class GithubWebhook:
	"""Main class with GitHub functionality."""

	def __init__(self, settings: HubLabBotSettings, repo_path: str, is_admin: bool = False):
		self.settings = settings
		"""`hublabbot.settings.HubLabBotSettings`."""
		self.repo_path = repo_path
		"""Path like {namespace}/{repo name} in GitHub."""
		self.repo_options = self.settings.get_repo_by_github(repo_path)
		"""`hublabbot.settings.RepoOptions`."""
		self.github = Github(self.settings.gh_token if is_admin else self.settings.gh_bot_token)
		"""Github object with bot credentials."""

	def _merge_pr(self, pr: ghp.PullRequest) -> None:
		assert self.repo_options.gh_auto_merge_pr is not None
		if pr.update() is True:
			if pr.state == 'closed' or not pr.mergeable:
				return
			if self.repo_options.gh_auto_merge_pr.required_label_name not in [l.name for l in pr.labels]:
				return
		status = pr.merge()
		if status.merged:
			print(f'GH:{self.repo_path}: PR#{pr.number} merged.')
		else:
			raise RuntimeError(f'GH:{self.repo_path}: PR#{pr.number} fail to merge - "{status.message}"!')

	def get_pr_by_sha(self, sha: str) -> Optional[ghp.PullRequest]:
		"""Get PR by head commit sha.

		Args:
			sha: Head commit sha.

		Returns:
			PullRequest or `None` if not found.

		"""
		repo = self.github.get_repo(self.repo_path)
		pr_list = [p for p in repo.get_pulls() if p.head.sha == sha]
		if len(pr_list) == 0:
			return None
		else:
			return pr_list[0]

	def get_branch_head(self, branch_name: str) -> str:
		"""Get head sha of `branch_name`.

		Args:
			branch_name: Branch name.

		Returns:
			Head commit sha.

		"""
		repo = self.github.get_repo(self.repo_path)
		branch = repo.get_branch(branch_name)
		head_sha: str = branch.commit.sha
		return head_sha

	def is_external_pr(self, pr: JsonDict) -> bool:
		"""Check PR is external or not.

		Args:
			pr: JSON from GitHub with PR dict.

		Returns:
			`True` if is external, `False` is not.

		"""
		pr_repo_path: str = pr['head']['repo']['full_name']
		return pr_repo_path != self.repo_path

	def auto_merge_pr(self, sha: str) -> IResponse:
		"""Action - auto-merge PR.

		Args:
			sha: SHA of HEAD commit in PR.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		if self.repo_options.gh_auto_merge_pr is None:
			return {
				'status': 'IGNORE',
				'note': f'Repo option gh_auto_merge_pr disabled for repo {self.repo_path}.'}
		pr = self.get_pr_by_sha(sha)
		if pr is None or pr.state == 'closed' or not pr.mergeable:
			return {'status': 'IGNORE'}
		if pr.user.login not in self.repo_options.gh_auto_merge_pr.authors_white_list:
			return {'status': 'IGNORE'}
		if self.repo_options.gh_auto_merge_pr.required_label_name not in [l.name for l in pr.labels]:
			return {'status': 'IGNORE'}
		if self.repo_options.gh_auto_merge_pr.delay > 0:
			timer = Timer(self.repo_options.gh_auto_merge_pr.delay, lambda: self._merge_pr(pr))
			timer.start()
		else:
			self._merge_pr(pr)
		return {'status': 'OK'}

	def show_gitlabci_fail(self, failed_job_sha: str, failed_stage: str, failed_job_url: str,
	                       failed_job_log: str) -> IResponse:
		"""Action - post comment with GitLab CI fail-report to PR.

		Args:
			failed_job_sha: SHA of HEAD commit in PR.
			failed_stage: Stage at which the error occurred.
			failed_job_url: Fail job URL.
			failed_job_log: Fail job log.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		pr = self.get_pr_by_sha(failed_job_sha)
		if pr is None:
			return {
				'status': 'IGNORE',
				'note': f'Commit "{failed_job_sha}" not found in Pull Requests.'}
		gitlabci_fail_tmd = (self.settings.assets_path / 'gitlabci_fail.templ.md').read_text()
		gitlabci_fail_templ = Template(gitlabci_fail_tmd)
		gitlabci_fail_md = gitlabci_fail_templ.substitute(
			failed_stage=failed_stage,
			failed_job_log=failed_job_log,
			failed_job_url=failed_job_url)
		pr.create_issue_comment(gitlabci_fail_md)
		print(f'GH:{self.repo_path}: Comment with GitLab CI fail-report posted to PR#{pr.number}.')
		return {'status': 'OK'}

	def sync_pr_to_gitlab(self, pr: JsonDict) -> IResponse:
		"""Action - push external PR's branch to GitLab.

		Args:
			pr: JSON from GitHub with PR dict.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		if not self.is_external_pr(pr):
			return {'status': 'IGNORE'}
		with tempfile.TemporaryDirectory() as gitdir:
			repo = pygit2.init_repository(gitdir, bare=True)
			pr_num = pr['number']
			pr_ref = f'refs/heads/pr-{pr_num}'
			creds = f'gitlab-ci-token:{self.settings.gl_token}'
			gl_host = urlsplit(self.settings.gl_base_url).netloc
			repo.remotes.create('github', f'https://github.com/{self.repo_path}.git')
			repo.remotes.create('gitlab', f'https://{creds}@{gl_host}/{self.repo_options.gl_repo_path}.git')
			repo.remotes['github'].fetch([f'+refs/pull/{pr_num}/head:{pr_ref}'])
			repo.remotes['gitlab'].push(
				['+' + pr_ref],
				RemotePushCallback(self.repo_path, self.repo_options.gl_repo_path, pr_num))
			return {'status': 'OK'}
