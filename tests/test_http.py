import unittest
from unittest import mock

import requests

from tracker import http


class HttpTests(unittest.TestCase):
    def test_retry_after_header_is_respected(self):
        limited = requests.Response()
        limited.status_code = 429
        limited.url = "https://example.com"
        limited.headers["Retry-After"] = "30"
        success = requests.Response()
        success.status_code = 200
        success.url = "https://example.com"

        with mock.patch.object(http._session, "get", side_effect=[limited, success]), \
                mock.patch.object(http.time, "sleep") as sleep:
            result = http.get("https://example.com", retries=1, backoff=2)

        self.assertIs(result, success)
        sleep.assert_called_once_with(30.0)

    def test_retry_after_http_date_is_respected(self):
        response = requests.Response()
        response.headers["Retry-After"] = "Wed, 21 Oct 2099 07:28:00 GMT"
        delay = http._retry_delay(response, attempt=0, backoff=2)

        self.assertGreaterEqual(delay, 59)


if __name__ == "__main__":
    unittest.main()
