"""Module with view of GitHub webhook."""
import traceback
import hashlib
import hmac

# jscpd:ignore-start
from pyramid.interfaces import IRequest, IResponse  # type: ignore
from pyramid.view import (view_config, notfound_view_config, exception_view_config,  # type: ignore
                          view_defaults)
from pyramid.httpexceptions import HTTPUnauthorized  # type: ignore
from pyramid.response import Response  # type: ignore
from pyramid.config import Configurator  # type: ignore
# jscpd:ignore-end

from hublabbot.const import GITHUB_ENDPOINT
from hublabbot.github.github_webhook import GithubWebhook
from hublabbot.gitlab.gitlab_webhook import GitlabWebhook


@view_defaults(
	route_name=GITHUB_ENDPOINT, request_method='POST', renderer='json'
)
class GithubPayloadView:
	"""View receiving of GitHub payload.

	By default, this view it's fired only if the request is json and method POST.
	"""

	def __init__(self, request: IRequest):
		self.request = request
		"""Pyramid's request object."""
		self.settings = self.request.registry.settings['hublabbot']
		"""`hublabbot.settings.HubLabBotSettings`."""
		self._verify_request()
		self.payload = self.request.json
		"""GitHub JSON payload."""
		self.repo_path = self.payload['repository']['full_name']
		"""Path like {namespace}/{repo name} in GitHub."""
		self.repo_options = self.settings.get_repo_by_github(self.repo_path)
		"""`hublabbot.settings.RepoOptions`."""
		self.github_bot_wh = GithubWebhook(self.settings, self.repo_path)
		"""`hublabbot.github.github_webhook.GithubWebhook` with bot credentials."""
		self.gitlab_wh = GitlabWebhook(self.settings, self.repo_options.gl_repo_path)
		"""`hublabbot.gitlab.gitlab_webhook.GitlabWebhook` with your credentials."""

	def _verify_request(self) -> None:
		signature = self.request.headers['X-Hub-Signature'].partition('=')[2]
		expected_signature = hmac.new(self.settings.gh_secret.encode(), self.request.body,
		                              hashlib.sha1).hexdigest()
		if not hmac.compare_digest(signature, expected_signature):
			raise HTTPUnauthorized

	def _show_gitlabci_fail(self) -> IResponse:
		if self.repo_options.gh_show_gitlab_ci_fail is None:
			return {
				'status': 'IGNORE',
				'note': f'Repo option gh_show_gitlab_ci_fail disabled for repo {self.repo_path}.'}
		if (self.payload['state'] == 'error'
		    and self.payload['description'] == 'Pipeline canceled on GitLab'):
			return {'status': 'IGNORE'}
		failed_job = self.gitlab_wh.get_failed_job(self.payload['target_url'])
		failed_job_log = self.gitlab_wh.parse_gitlabci_log(failed_job.trace())
		return self.github_bot_wh.show_gitlabci_fail(failed_job.pipeline['sha'], failed_job.stage,
		                                             failed_job.web_url, failed_job_log)

	def _delete_merged_branch_in_gl(self) -> IResponse:
		pr = self.payload['pull_request']
		if self.github_bot_wh.is_external_pr(pr):
			return self.gitlab_wh.delete_branch(f'pr-{pr["number"]}')
		return {'status': 'IGNORE'}

	@view_config(header='X-Github-Event:delete')
	def payload_delete(self) -> IResponse:
		"""Handler for 'X-Github-Event: delete'.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		if self.payload['ref_type'] != 'branch':
			return {'status': 'IGNORE'}
		return self.gitlab_wh.delete_branch(self.payload['ref'])

	@view_config(header='X-Github-Event:status')
	def payload_status(self) -> IResponse:
		"""Handler for 'X-Github-Event: status'.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		if self.payload['state'] in ('failure', 'error'):
			return self._show_gitlabci_fail()
		elif self.payload['state'] == 'pending':
			return {'status': 'RUNNING'}
		elif self.payload['state'] == 'success':
			sha = self.payload['commit']['sha']
			return self.github_bot_wh.auto_merge_pr(sha)

	@view_config(header='X-Github-Event:pull_request')
	def payload_pull_request(self) -> IResponse:
		"""Handler for 'X-Github-Event: pull_request'.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		if self.payload['action'] in ('opened', 'synchronize', 'reopened'):
			pr = self.payload['pull_request']
			return self.github_bot_wh.sync_pr_to_gitlab(pr)
		elif self.payload['action'] == 'closed':
			return self._delete_merged_branch_in_gl()
		return {'status': 'IGNORE'}

	@view_config(header='X-Github-Event:ping')
	def payload_ping(self) -> IResponse:
		"""Handler for 'X-Github-Event: ping'.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		hook_id = self.payload['hook_id']
		print(f'GH:{self.repo_path}: Pinged! Webhook created with id {hook_id}.')
		return {'status': 'OK'}

	# jscpd:ignore-start
	@notfound_view_config()
	def notfound(self) -> IResponse:
		"""Handler for not used events. Ignore its.

		Returns:
			`{'status': 'IGNORE'}`.

		"""
		return {'status': 'IGNORE'}

	@exception_view_config()
	def error(self) -> IResponse:
		"""Handler for exceptions. Sends exceptions in JSON.

		Returns:
			`{'status': 'ERROR', 'error': ...}`.

		"""
		exc = self.request.exception
		traceback.print_exception(type(exc), exc, exc.__traceback__)
		err = traceback.format_exception_only(type(exc), exc)
		resp = Response()
		resp.status_int = 500
		resp.json = {
			'status': 'ERROR',
			'error': err if len(err) > 1 else err[0]}
		return resp
	# jscpd:ignore-end


def includeme(config: Configurator) -> None:
	"""Pyramid magic function, register views."""
	config.add_route(GITHUB_ENDPOINT, '/' + GITHUB_ENDPOINT)
	config.scan(__name__)
