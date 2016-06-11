# coding: utf-8

import unittest
import mock

import os
import xml.etree.ElementTree as ET

import requests

from vmbot.helpers.files import CACHE_DB
from vmbot.helpers.exceptions import APIError

from vmbot.helpers import api


def flawed_response(*args, **kwargs):
    """Return a requests.Response with 404 status code."""
    res = requests.Response()
    res.status_code = 404
    res._content = b"ASCII text"
    res.encoding = "ascii"
    return res


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            os.remove(CACHE_DB)
        except OSError:
            pass

    @classmethod
    def tearDownClass(cls):
        return cls.setUpClass()

    def test_get_typeName(self):
        # typeID: 34 Tritanium
        self.assertEqual(api.get_typeName(34), "Tritanium")

    def test_get_typeName_invaliditem(self):
        self.assertEqual(api.get_typeName(-1), "{Failed to load}")

    def test_get_solarSystemData(self):
        # solarSystemID: 30000142 Jita
        self.assertDictEqual(
            api.get_solarSystemData(30000142),
            {'solarSystemID': 30000142, 'solarSystemName': "Jita",
             'constellationID': 20000020, 'constellationName': "Kimotoro",
             'regionID': 10000002, 'regionName': "The Forge"}
        )

    def test_get_solarSystemData_invalidsystem(self):
        self.assertDictEqual(
            api.get_solarSystemData(-1),
            {'solarSystemID': 0, 'solarSystemName': "{Failed to load}",
             'constellationID': 0, 'constellationName': "{Failed to load}",
             'regionID': 0, 'regionName': "{Failed to load}"}
        )

    def test_get_tickers(self):
        # corporationID: 1164409536 [OTHER]
        # allianceID: 159826257 <OTHER>
        self.assertTupleEqual(api.get_tickers(1164409536, 159826257), ("OTHER", "OTHER"))

    def test_get_tickers_corponly(self):
        # corporationID: 98007161 [FCFTW] (member of <SSC>)
        self.assertTupleEqual(api.get_tickers(98007161, None), ("FCFTW", "SSC"))

    def test_get_tickers_allianceonly(self):
        # allianceID: 99005065 <HKRAB>
        self.assertTupleEqual(api.get_tickers(None, 99005065), (None, "HKRAB"))

    def test_get_tickers_invalidid(self):
        self.assertTupleEqual(api.get_tickers(-1, -1), ("{Failed to load}", "{Failed to load}"))

    def test_get_tickers_none(self):
        self.assertTupleEqual(api.get_tickers(None, None), (None, None))

    def test_get_crest_endpoint(self):
        test_url = "https://crest-tq.eveonline.com/"

        def del_cache(*args, **kwargs):
            """Delete Cache-Control header from requests.Response."""
            requests_patcher.stop()
            r = requests.get(*args, **kwargs)
            requests_patcher.start()

            r.headers.pop('Cache-Control', None)
            return r

        # Test without Cache-Control header
        requests_patcher = mock.patch("requests.get", side_effect=del_cache)
        requests_patcher.start()

        res_nocache = api.get_crest_endpoint(test_url)
        self.assertIsInstance(res_nocache, dict)

        requests_patcher.stop()

        # Test with cache
        res_cache = api.get_crest_endpoint(test_url)
        self.assertIsInstance(res_cache, dict)

        # Test cached response
        self.assertDictEqual(api.get_crest_endpoint(test_url), res_cache)

    @mock.patch("requests.get", side_effect=requests.exceptions.RequestException("TestException"))
    def test_get_crest_endpoint_RequestException(self, mock_requests):
        self.assertRaisesRegexp(APIError, "Error while connecting to CREST: TestException",
                                api.get_crest_endpoint, "TestURL")

    @mock.patch("requests.get", side_effect=flawed_response)
    def test_get_crest_endpoint_flawedresponse(self, mock_requests):
        self.assertRaisesRegexp(APIError, "CREST returned error code 404",
                                api.get_crest_endpoint, "TestURL")

    def test_post_xml_endpoint(self):
        test_url = "https://api.eveonline.com/server/ServerStatus.xml.aspx"

        # Test with cache
        res_cache = api.post_xml_endpoint(test_url)
        self.assertIsInstance(res_cache, ET.Element)

        # Test cached response
        self.assertEqual(ET.tostring(api.post_xml_endpoint(test_url)), ET.tostring(res_cache))

    @mock.patch("requests.post", side_effect=requests.exceptions.RequestException("TestException"))
    def test_post_xml_endpoint_RequestException(self, mock_requests):
        self.assertRaisesRegexp(APIError, "Error while connecting to XML-API: TestException",
                                api.post_xml_endpoint, "TestURL")

    @mock.patch("requests.post", side_effect=flawed_response)
    def test_post_xml_endpoint_flawedresponse(self, mock_requests):
        self.assertRaisesRegexp(APIError, "XML-API returned error code 404",
                                api.post_xml_endpoint, "TestURL")


if __name__ == "__main__":
    unittest.main()
