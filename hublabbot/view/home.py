"""Module with view of home page."""
from string import Template

from pyramid.interfaces import IRequest, IResponse  # type: ignore
from pyramid.config import Configurator  # type: ignore
from pyramid.view import view_config  # type: ignore
from pyramid.response import Response  # type: ignore

import hublabbot
from hublabbot.const import HOME_ROUTE


@view_config(route_name=HOME_ROUTE)
def favicon_view(request: IRequest) -> IResponse:
	"""View of home page."""
	settings = request.registry.settings['hublabbot']
	index_th = (settings.assets_path / 'index.templ.html').read_text()
	index_templ = Template(index_th)
	index_html = index_templ.substitute(
		github_bot_avatar=settings.gh_bot_avatar_url,
		github_bot_name=settings.gh_bot_login,
		github_bot_profile=settings.gh_bot_profile_url,
		github_bot_version=hublabbot.__version__)
	return Response(index_html)


def includeme(config: Configurator) -> None:
	"""Pyramid magic function, register views."""
	config.add_route(HOME_ROUTE, '/')
	config.scan(__name__)
