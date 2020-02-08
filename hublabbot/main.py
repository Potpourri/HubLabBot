"""Module for entry point of HubLabBot."""
from typing import List
import sys
import atexit
from pathlib import PurePath
from threading import Timer
from wsgiref.simple_server import make_server

import pkg_resources
from pyramid.config import Configurator  # type: ignore

from hublabbot.settings import HubLabBotSettings
import hublabbot.github.webhook as gh_webhook
import hublabbot.github.label as gh_label
import hublabbot.github.collaborator as gh_collaborator
import hublabbot.gitlab.webhook as gl_webhook


def _configure_repos(settings: HubLabBotSettings) -> None:
	for repo_options in settings.repos:
		gh_webhook.configure(settings.gh_token, settings.gh_secret, settings.base_url, repo_options)
		gh_label.configure(settings.gh_token, repo_options)
		gh_collaborator.configure(settings.gh_token, settings.gh_bot_token, repo_options)
		gl_webhook.configure(settings.gl_base_url, settings.gl_token, settings.gl_secret,
		                     settings.base_url, repo_options)


def main(args: List[str] = []) -> None:
	"""Entry point of HubLabBot."""
	settings_path = args[0] if len(args) >= 1 else 'hublabbot.json'
	assets_path = pkg_resources.resource_filename('hublabbot', 'assets')
	atexit.register(pkg_resources.cleanup_resources)
	settings = HubLabBotSettings(PurePath(settings_path), PurePath(assets_path))
	with Configurator(settings={'hublabbot': settings}) as config:
		config.include('hublabbot.view.github')
		config.include('hublabbot.view.gitlab')
		config.include('hublabbot.view.home')
		config.include('hublabbot.view.favicon')
		app = config.make_wsgi_app()
	# Configure webhooks after server started
	timer = Timer(1, lambda: _configure_repos(settings))
	timer.start()
	server = make_server('0.0.0.0', settings.port, app)
	print(f'Start server on {settings.base_url}')
	server.serve_forever()


if __name__ == '__main__':
	main(sys.argv[1:])
