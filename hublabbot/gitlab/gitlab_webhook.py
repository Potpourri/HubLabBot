"""Module for GitLab webhook functionality."""
from typing import Optional
import re
from datetime import datetime, timezone

from gitlab import Gitlab, GitlabDeleteError  # type: ignore
import gitlab.v4.objects as gl_types  # type: ignore
from pyramid.interfaces import IResponse  # type: ignore

from hublabbot.util import filter_out_ansi_escape
from hublabbot.settings import HubLabBotSettings


class GitlabWebhook:
	"""Main class with GitLab functionality."""

	def __init__(self, settings: HubLabBotSettings, repo_path: str):
		self.settings = settings
		"""`hublabbot.settings.HubLabBotSettings`."""
		self.repo_path = repo_path
		"""Path like {namespace}/{repo name} in GitLab."""
		try:
			repo_options = None
			repo_options = self.settings.get_repo_by_gitlab(repo_path)
		except RuntimeError:
			pass
		self.repo_options = repo_options
		"""`hublabbot.settings.RepoOptions`."""
		self.gitlab = Gitlab(self.settings.gl_base_url, private_token=self.settings.gl_token)
		"""Gitlab object with your credentials."""

	def parse_gitlabci_log(self, raw_log: bytes) -> str:
		"""Parse GitLab CI log.

		Args:
			raw_log: Log from GitLab CI job.

		Returns:
			Parsed and truncated log's tail.

		"""
		assert self.repo_options is not None
		assert self.repo_options.gh_show_gitlab_ci_fail is not None
		log = raw_log.decode('utf-8')
		log = filter_out_ansi_escape(log)
		log_lines = re.split('\n|\r', log)
		if log_lines[-1] == '':
			del log_lines[-1]
		for linum in range(len(log_lines)):
			if log_lines[linum].startswith('section_start:'):
				parts = log_lines[linum].split(':')
				start_time = datetime.fromtimestamp(int(parts[1]), timezone.utc)
				log_lines[linum] = f'Start {parts[2]}'
			elif log_lines[linum].startswith('section_end:'):
				parts = log_lines[linum].split(':')
				end_time = datetime.fromtimestamp(int(parts[1]), timezone.utc)
				time_delta = end_time - start_time
				time = datetime.fromtimestamp(time_delta.total_seconds(), timezone.utc)
				log_lines[linum] = f'End of {parts[2]}, time - {time:%M:%S}'
		log_lines = log_lines[-self.repo_options.gh_show_gitlab_ci_fail.max_lines:]
		log = '\n'.join(log_lines)
		return log

	def get_pipeline_by_url(self, target_url: str) -> gl_types.ProjectPipeline:
		"""Get pipeline object from URL to pipeline.

		Args:
			target_url: URL to pipeline.

		Returns:
			`ProjectPipeline` object.

		"""
		project = self.gitlab.projects.get(self.repo_path, lazy=True)
		pipeline_id = target_url.split('/')[-1]
		return project.pipelines.get(pipeline_id)

	def get_failed_job(self, pipeline: gl_types.ProjectPipeline
	) -> Optional[gl_types.ProjectPipelineJob]:
		"""Get failed job object from `pipeline``.

		Args:
			pipeline: `ProjectPipeline` object.

		Returns:
			`ProjectPipelineJob` object or `None`.

		"""
		project = self.gitlab.projects.get(self.repo_path, lazy=True)
		# jobs sorted by running order
		pipeline_jobs = pipeline.jobs.list(scope='failed')
		if len(pipeline_jobs) == 0:
			return None
		failed_job = project.jobs.get(pipeline_jobs[0].id)
		return failed_job

	def cancel_pipeline(self, pipeline_id: int) -> None:
		"""Cancel one pipeline.

		Args:
			pipeline_id: ID of pipeline.

		"""
		project = self.gitlab.projects.get(self.repo_path, lazy=True)
		pipeline = project.pipelines.get(pipeline_id)
		pipeline.cancel()
		print(f'GL:{self.repo_path}: Pipeline #{pipeline.id} canceled.')

	def cancel_old_pipelines(self, pipeline_id: int, pipeline_ref: str) -> IResponse:
		"""Action - auto-cancel old pipelines.

		Args:
			pipeline_id: ID of pipeline, which triggered by pull request. If `0` save latest pipeline.
			pipeline_ref: Branch name.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		project = self.gitlab.projects.get(self.repo_path, lazy=True)
		branch = project.branches.get(pipeline_ref)
		# don't touch protected branch pipelines
		if branch.protected:
			return {'status': 'IGNORE'}
		# pipelines sorted by ID by desc
		pipelines = project.pipelines.list(ref=pipeline_ref, status='running')
		pipelines += project.pipelines.list(ref=pipeline_ref, status='pending')
		if pipeline_id == 0:
			pipeline_id = pipelines[0].id
		for pipeline in pipelines:
			if pipeline.id == pipeline_id:
				continue
			pipeline.cancel()
			print(f'GL:{self.repo_path}: Pipeline #{pipeline.id} canceled.')
		return {'status': 'OK'}

	def delete_branch(self, branch: str) -> IResponse:
		"""Delete branch on GitLab.

		Args:
			branch: Branch name.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		project = self.gitlab.projects.get(self.repo_path, lazy=True)
		try:
			project.branches.delete(branch)
		except GitlabDeleteError as err:
			if err.args[0] == '404 Branch Not Found':
				return {
					'status': 'IGNORE',
					'note': err.args[0]}
			else:
				raise
		print(f'GH:{self.repo_path}: Branch {branch} deleted.')
		return {'status': 'OK'}

	def button_api_delete_pipeline(self, pipeline_id: int) -> IResponse:
		"""API - delete pipeline.

		Args:
			pipeline_id: Pipeline ID.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		project = self.gitlab.projects.get(self.repo_path, lazy=True)
		pipeline = project.pipelines.get(pipeline_id, lazy=True)
		pipeline.delete()
		print(f'GL:{self.repo_path}: Pipeline #{pipeline_id} deleted.')
		return {'status': 'OK'}

	def button_api_is_enabled(self) -> IResponse:
		"""API - check button is enabled.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		return {
			'status': 'OK',
			'value': self.repo_options is not None and self.repo_options.gl_delete_pipeline_btn}
