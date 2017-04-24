"""Adapter for ripozo dispatcher supporting ``aiohttp.web``."""
import logging

from functools import wraps
from inspect import iscoroutine
from json.decoder import JSONDecodeError

from aiohttp.web import Response

from ripozo.dispatch_base import DispatcherBase
from ripozo.exceptions import RestException
from ripozo.utilities import join_url_parts
from ripozo.resources.request import RequestContainer

from .utils import get_request_mime_types_priorities

_logger = logging.getLogger(__name__)


def exception_handler(dispatcher, accepted_mimetypes, exc):
    """Handle exceptions in the project.

    This catches any RestException (from ripozo.exceptions)
    and calls the format_exception class method on the adapter
    class.  It will appropriately set the status_code, response,
    and content type for the exception.

    :param FlaskDispatcher dispatcher: A FlaskDispatcher instance
        used to format the exception
    :param list accepted_mimetypes: A list of the accepted mimetypes
        for the client.
    :param Exception exc: The exception that was raised.
    :return: A flask Response object.
    :rtype: flask.Response
    """
    if isinstance(exc, RestException):
        adapter_klass = dispatcher.get_adapter_for_type(accepted_mimetypes)
        response, content_type, status_code = adapter_klass.format_exception(exc)
        return Response(status=status_code, content_type=content_type,
                        body=response)
    raise exc


class AIODispatcher(DispatcherBase):
    """The actual dispatcher responsible for integrating ripozo w/ aiohttp."""

    def __init__(self, app, url_prefix='', error_handler=exception_handler,
                 **kwargs):
        """Initialize the adapter.

        The app can be an aiohttp.web.Application instance.

        :param aiohttp.web.Application app: The flask app that is responsible for
            handling the web application.
        :param unicode url_prefix: The url prefix will be prepended to
            every route that is registered on this dispatcher.  It is
            helpful if, for example, you want to expose your api
            on the '/api' path.
        :param function error_handler: A function that takes a dispatcher,
            accepted_mimetypes, and exception that handles error responses.
            It should return a aiohttp.web.Response instance.
        """
        self.app = app
        if url_prefix and not url_prefix.startswith('/'):
            url_prefix = '/{0}'.format(url_prefix)
        self._base_url = url_prefix
        self.error_handler = error_handler
        super(AIODispatcher, self).__init__(**kwargs)

    @property
    def base_url(self):
        """Return the base url."""
        return self._base_url

    def register_route(self, endpoint, endpoint_func=None, route=None, methods=None, expect_handler=None, **options):
        """Register the endpoints on the aiohttp application.

        It does so by using the add_route on the app.router. It wraps the
        endpoint_func with the ``dec`` which returns an updated coroutine.
        This function appropriately sets the RequestContainer object
        before passing it to the apimethod.

        :param unicode endpoint: The name of the endpoint.  This is typically
            used in aiohttp for reversing urls
        :param method endpoint_func: The actual function or coroutine that is
            going to be called. This is generally going to be a @apimethod
            decorated, ResourceBase subclass method.
        :param str route: The actual route that is going to be used.
        :param list methods: The http verbs that can be used with this endpoint
        :param coroutine expect_handler: The additional option to pass to the add_route
        """
        route = join_url_parts(self.base_url, route)

        for method in methods:
            self.app.router.add_route(
                method, route, dec(self, endpoint_func),
                name=endpoint, expect_handler=expect_handler
            )


def dec(dispatcher, request_handler):
    """Decorator that wraps @apimethod decorated coroutine or function."""
    @wraps(request_handler)
    async def request_handler_wrapper(request):
        """Wrapper for @apimethod decorated coroutine or function."""
        try:
            body_args = await request.json()
        except JSONDecodeError:
            try:
                body_args = await request.post()
            except Exception as e:
                _logger.exception(e)
                raise

        ripozo_request = RequestContainer(url_params=request.match_info,
                                          query_args=request.query,
                                          body_args=body_args,
                                          headers=request.headers,
                                          method=request.method)

        accepted_mimetypes = tuple(map(
            lambda m: m[0],
            get_request_mime_types_priorities(request)
        ))

        resp = request_handler(request)
        if iscoroutine(resp):
            resp = await resp

        try:
            adapter = dispatcher.dispatch(
                wraps(request_handler)(lambda request: resp),
                accepted_mimetypes, ripozo_request
            )
        except Exception as e:
            _logger.exception(e)
            return dispatcher.error_handler(dispatcher, accepted_mimetypes, e)

        return Response(
            status=adapter.status_code, headers=adapter.extra_headers,
            body=adapter.formatted_body
        )
    return request_handler_wrapper
