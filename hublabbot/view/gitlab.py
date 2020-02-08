"""Module with view of GitLab webhook."""
import traceback
import hmac

# jscpd:ignore-start
from pyramid.interfaces import IRequest, IResponse  # type: ignore
from pyramid.view import (view_config, notfound_view_config, exception_view_config,  # type: ignore
                          view_defaults)
from pyramid.httpexceptions import HTTPUnauthorized  # type: ignore
from pyramid.response import Response  # type: ignore
from pyramid.config import Configurator  # type: ignore
# jscpd:ignore-end

from hublabbot.const import GITLAB_ENDPOINT, GITLAB_BUTTON_API_ENDPOINT
from hublabbot.gitlab.gitlab_webhook import GitlabWebhook


@view_defaults(
	route_name=GITLAB_ENDPOINT, request_method='POST', renderer='json'
)
class GitlabPayloadView:
	"""View receiving of GitLab payload.

	By default, this view it's fired only if the request is json and method POST.
	"""

	def __init__(self, request: IRequest):
		self.request = request
		"""Pyramid's request object."""
		self.settings = self.request.registry.settings['hublabbot']
		"""`hublabbot.settings.HubLabBotSettings`."""
		self._verify_request()
		self.payload = self.request.json
		"""GitLab JSON payload."""
		self.repo_path = self.payload['project']['path_with_namespace']
		"""Path like {namespace}/{repo name} in GitLab."""
		self.gitlab_wh = GitlabWebhook(self.settings, self.repo_path)
		"""`hublabbot.gitlab.gitlab_webhook.GitlabWebhook` with your credentials."""

	# jscpd:ignore-start
	def _verify_request(self) -> None:
		signature = self.request.headers['X-Gitlab-Token']
		expected_signature = self.settings.gl_secret
		if not hmac.compare_digest(signature, expected_signature):
			raise HTTPUnauthorized
	# jscpd:ignore-end

	@view_config(header='X-Gitlab-Event:Pipeline Hook')
	def payload_pipeline_hook(self) -> IResponse:
		"""Handler for 'X-Gitlab-Event: Pipeline Hook'.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		pipeline = self.payload['object_attributes']
		if pipeline['status'] == 'running':
			return self.gitlab_wh.cancel_old_pipelines(pipeline['tag'], pipeline['ref'])
		else:
			return {'status': 'IGNORE'}

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


@view_defaults(
	route_name=GITLAB_BUTTON_API_ENDPOINT, renderer='json'
)
class GitlabButtonApiView:
	"""View receiving of userscript's API requests in GitLab."""

	def __init__(self, request: IRequest):
		self.request = request
		"""Pyramid's request object."""
		self.settings = self.request.registry.settings['hublabbot']
		"""`hublabbot.settings.HubLabBotSettings`."""
		self._verify_request()
		self.params = self.request.params
		"""Pyramid's URL params dict."""
		self.repo_path = self.params['repo_path']
		"""Path like {namespace}/{repo name} in GitLab."""
		self.gitlab_wh = GitlabWebhook(self.settings, self.repo_path)
		"""`hublabbot.gitlab.gitlab_webhook.GitlabWebhook` with your credentials."""

	# jscpd:ignore-start
	def _verify_request(self) -> None:
		signature = self.request.headers['X-Gitlab-Token']
		expected_signature = self.settings.gl_secret
		if not hmac.compare_digest(signature, expected_signature):
			raise HTTPUnauthorized
	# jscpd:ignore-end

	@view_config(request_method='DELETE', request_param='pipeline_id')
	def button_api_delete_pipeline(self) -> IResponse:
		"""Handler for API: delete pipeline.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		return self.gitlab_wh.button_api_delete_pipeline(self.params['pipeline_id'])

	@view_config(request_method='GET', request_param='is_enabled')
	def button_api_is_enabled(self) -> IResponse:
		"""Handler for API: check button is enabled.

		Returns:
			`{'status': 'OK', ...}` if action was successful,</br>
			`{'status': 'IGNORE', ...}` if action ignored,</br>
			`{'status': 'ERROR', ...}` if action failed.

		"""
		return self.gitlab_wh.button_api_is_enabled()

	# jscpd:ignore-start
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
	config.add_route(GITLAB_ENDPOINT, '/' + GITLAB_ENDPOINT)
	config.add_route(GITLAB_BUTTON_API_ENDPOINT, '/' + GITLAB_BUTTON_API_ENDPOINT)
	config.scan(__name__)
