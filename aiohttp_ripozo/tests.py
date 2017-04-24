"""Test suite for the adapter."""
from unittest import mock, TestCase

from .utils import get_request_mime_types_priorities


class UtilsTest(TestCase):
    """Test util functions."""

    def test_parse_mime_types(self):
        """Ensure mime types are prioritized properly."""
        req = mock.MagicMock()
        header_val = ('Accept: application/vnd.siren+json, application/json, '
                      'text/json;q=0.9, */*;q=0.1, */*;q=1.0, text/html')
        with mock.patch.object(req.headers, 'getone', lambda hname: header_val):
            prioritized_types = get_request_mime_types_priorities(req)

        expected_res = (
            (('Accept:',
              'application/vnd.siren+json',
              'application/json',
              '*/*',
              'text/html'),
             1.0),
            (('text/json',), 0.9),
            (('*/*',), 0.1)
        )

        assert prioritized_types == expected_res
