"""Utils for processing HTTP."""
import re
from itertools import groupby

# for explanation of "media-range", etc. see Sections 5.3.{1,2} of RFC 7231
# borrowed from github.com/pallets/werkzeug/blob/master/werkzeug/http.py#L43
_accept_re = re.compile(
    r'''(                       # media-range capturing-parenthesis
          [^\s;,]+              # type/subtype
          (?:[ \t]*;[ \t]*      # ";"
            (?:                 # parameter non-capturing-parenthesis
              [^\s;,q][^\s;,]*  # token that doesn't start with "q"
            |                   # or
              q[^\s;,=][^\s;,]* # token that is more than just "q"
            )
          )*                    # zero or more parameters
        )                       # end of media-range
        (?:[ \t]*;[ \t]*q=      # weight is a "q" parameter
          (\d*(?:\.\d+)?)       # qvalue capturing-parentheses
          [^,]*                 # "extension" accept params: who cares?
        )?                      # accept params are optional
    ''', re.VERBOSE)
"""Regexp for parsing HTTP Accept headers with content type priorities."""


def get_request_mime_types_priorities(request):
    """Return a priority-based list of accepted HTTP content type responses."""
    accept_parts = request.headers.getone('Accept')
    mime_priorities = sorted(
        map(
            lambda match: (
                match.group(1),
                max(min(float(match.group(2) or 1), 1), 0)
            ),
            _accept_re.finditer(accept_parts)
        ),
        key=lambda el: el[1], reverse=True
    )

    grouped_mime_priorities = (
        (tuple(map(lambda t: t[0], g)), k)
        for k, g in groupby(mime_priorities, key=lambda el: el[1])
    )

    return tuple(grouped_mime_priorities)


__all__ = ('get_request_mime_types_priorities', )
