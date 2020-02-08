"""Module with view of favicon."""
from pyramid.interfaces import IRequest, IResponse  # type: ignore
from pyramid.config import Configurator  # type: ignore
from pyramid.view import view_config  # type: ignore
from pyramid.response import FileResponse  # type: ignore

from hublabbot.const import FAVICON_ROUTE


@view_config(route_name=FAVICON_ROUTE)
def favicon_view(request: IRequest) -> IResponse:
	"""View of favicon."""
	settings = request.registry.settings['hublabbot']
	favicon_png = settings.assets_path / 'favicon.png'
	return FileResponse(favicon_png, request)


def includeme(config: Configurator) -> None:
	"""Pyramid magic function, register views."""
	config.add_route(FAVICON_ROUTE, '/' + FAVICON_ROUTE)
	config.scan(__name__)
