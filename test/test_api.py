import unittest
import mock

import os
import xml.etree.ElementTree as ET

import requests

from vmbot.helpers.files import CACHE_DB
from vmbot.helpers.exceptions import APIError

from vmbot.helpers import api


def flawed_response(*args, **kwargs):
    """Return a requests.Response with 404 status code"""
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

    def test_getTypeName(self):
        # typeID: 34 Tritanium
        self.assertEqual(api.getTypeName(34), "Tritanium")

    def test_getTypeName_invaliditem(self):
        self.assertEqual(api.getTypeName(-1), "{Failed to load}")

    def test_getSolarSystemData(self):
        # solarSystemID: 30000142 Jita
        self.assertDictEqual(
            api.getSolarSystemData(30000142),
            {'solarSystemID': 30000142, 'solarSystemName': "Jita",
             'constellationID': 20000020, 'constellationName': "Kimotoro",
             'regionID': 10000002, 'regionName': "The Forge"}
        )

    def test_getSolarSystemData_invalidsystem(self):
        self.assertDictEqual(
            api.getSolarSystemData(-1),
            {'solarSystemID': 0, 'solarSystemName': "{Failed to load}",
             'constellationID': 0, 'constellationName': "{Failed to load}",
             'regionID': 0, 'regionName': "{Failed to load}"}
        )

    def test_getTickers(self):
        # corporationID: 1164409536 [OTHER]
        # allianceID: 159826257 <OTHER>
        self.assertTupleEqual(api.getTickers(1164409536, 159826257), ("OTHER", "OTHER"))

    def test_getTickers_corponly(self):
        # corporationID: 98007161 [FCFTW] (member of <SSC>)
        self.assertTupleEqual(api.getTickers(98007161, None), ("FCFTW", "SSC"))

    def test_getTickers_allianceonly(self):
        # allianceID: 99005065 <HKRAB>
        self.assertTupleEqual(api.getTickers(None, 99005065), (None, "HKRAB"))

    def test_getTickers_invalidid(self):
        self.assertTupleEqual(api.getTickers(-1, -1), ("{Failed to load}", "{Failed to load}"))

    def test_getTickers_none(self):
        self.assertTupleEqual(api.getTickers(None, None), (None, None))

    def test_getCRESTEndpoint(self):
        test_url = "https://crest-tq.eveonline.com/"

        def del_cache(*args, **kwargs):
            """Delete Cache-Control header from requests.Response"""
            requests_patcher.stop()
            r = requests.get(*args, **kwargs)
            requests_patcher.start()

            r.headers.pop('Cache-Control', None)
            return r

        # Test without Cache-Control header
        requests_patcher = mock.patch("requests.get", side_effect=del_cache)
        requests_patcher.start()

        res_nocache = api.getCRESTEndpoint(test_url)
        self.assertIsInstance(res_nocache, dict)

        requests_patcher.stop()

        # Test with cache
        res_cache = api.getCRESTEndpoint(test_url)
        self.assertIsInstance(res_cache, dict)

        # Test cached response
        self.assertDictEqual(api.getCRESTEndpoint(test_url), res_cache)

    @mock.patch("requests.get", side_effect=requests.exceptions.RequestException("TestException"))
    def test_getCRESTEndpoint_RequestException(self, mock_requests):
        self.assertRaisesRegexp(APIError, "Error while connecting to CREST: TestException",
                                api.getCRESTEndpoint, "TestURL")

    @mock.patch("requests.get", side_effect=flawed_response)
    def test_getCRESTEndpoint_flawedresponse(self, mock_requests):
        self.assertRaisesRegexp(APIError, "CREST returned error code 404",
                                api.getCRESTEndpoint, "TestURL")

    def test_postXMLEndpoint(self):
        test_url = "https://api.eveonline.com/server/ServerStatus.xml.aspx"

        # Test with cache
        res_cache = api.postXMLEndpoint(test_url)
        self.assertIsInstance(res_cache, ET.Element)

        # Test cached response
        self.assertEqual(ET.tostring(api.postXMLEndpoint(test_url)), ET.tostring(res_cache))

    @mock.patch("requests.post", side_effect=requests.exceptions.RequestException("TestException"))
    def test_postXMLEndpoint_RequestException(self, mock_requests):
        self.assertRaisesRegexp(APIError, "Error while connecting to XML-API: TestException",
                                api.postXMLEndpoint, "TestURL")

    @mock.patch("requests.post", side_effect=flawed_response)
    def test_postXMLEndpoint_flawedresponse(self, mock_requests):
        self.assertRaisesRegexp(APIError, "XML-API returned error code 404",
                                api.postXMLEndpoint, "TestURL")


if __name__ == "__main__":
    unittest.main()
