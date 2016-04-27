import unittest
import mock

import xml.etree.ElementTree as ET

import requests

from vmbot.helpers.exceptions import APIError

from vmbot.helpers import api


class TestAPI(unittest.TestCase):
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
        # corporationID: 2052404106 [XVMX]
        # allianceID: 1354830081 <CONDI>
        self.assertTupleEqual(api.getTickers(2052404106, 1354830081), ("XVMX", "CONDI"))

    def test_getTickers_corponly(self):
        # corporationID: 2052404106 [XVMX] (member of <CONDI>)
        self.assertTupleEqual(api.getTickers(2052404106, None), ("XVMX", "CONDI"))

    def test_getTickers_allianceonly(self):
        # allianceID: 1354830081 <CONDI>
        self.assertTupleEqual(api.getTickers(None, 1354830081), (None, "CONDI"))

    def test_getTickers_invalidid(self):
        self.assertTupleEqual(api.getTickers(-1, -1), ("{Failed to load}", "{Failed to load}"))

    def test_getTickers_noids(self):
        self.assertTupleEqual(api.getTickers(None, None), (None, None))

    def test_getCRESTEndpoint(self):
        testURL = "https://crest-tq.eveonline.com/"

        requestsPatcher = mock.patch("requests.get")

        # Returns requests.Response without Cache-Control header
        def del_cache(*args, **kwargs):
            requestsPatcher.stop()
            r = requests.get(*args, **kwargs)
            mockRequests = requestsPatcher.start()
            mockRequests.side_effect = del_cache

            if "Cache-Control" in r.headers:
                del r.headers['Cache-Control']
            return r

        mockRequests = requestsPatcher.start()
        mockRequests.side_effect = del_cache

        # Test without cache
        res_nocache = api.getCRESTEndpoint(testURL)
        self.assertIsInstance(res_nocache, dict)
        requestsPatcher.stop()

        # Test with cache
        res_cache = api.getCRESTEndpoint(testURL)
        self.assertIsInstance(res_cache, dict)
        # Test cached response
        self.assertDictEqual(api.getCRESTEndpoint(testURL), res_cache)

    @mock.patch("requests.get", side_effect=requests.exceptions.RequestException("TestException"))
    def test_getCRESTEndpoint_RequestException(self, mockRequests):
        self.assertRaisesRegexp(APIError, "Error while connecting to CREST: TestException",
                                api.getCRESTEndpoint, "TestURL")

    def test_getCRESTEndpoint_flawedResponse(self):
        def flawed_response(*args, **kwargs):
            class Object(object):
                pass

            obj = Object()
            obj.text = "This is not a valid HTML document"
            obj.status_code = 404
            return obj

        # Returns non-200 status
        requestsPatcher = mock.patch("requests.get", side_effect=flawed_response)
        mockRequests = requestsPatcher.start()

        self.assertRaisesRegexp(APIError, "CREST returned error code 404",
                                api.getCRESTEndpoint, "TestURL")

        requestsPatcher.stop()

    def test_postXMLEndpoint(self):
        testURL = "https://api.eveonline.com/server/ServerStatus.xml.aspx"

        res_cache = api.postXMLEndpoint(testURL)
        self.assertIsInstance(res_cache, ET.Element)
        # Test cached response
        self.assertEqual(ET.tostring(api.postXMLEndpoint(testURL)), ET.tostring(res_cache))

    @mock.patch("requests.post", side_effect=requests.exceptions.RequestException("TestException"))
    def test_postXMLEndpoint_RequestException(self, mockRequests):
        self.assertRaisesRegexp(APIError, "Error while connecting to XML-API: TestException",
                                api.postXMLEndpoint, "TestURL")

    def test_postXMLEndpoint_flawedResponse(self):
        def flawed_response(*args, **kwargs):
            class Object(object):
                pass

            obj = Object()
            obj.text = "This is not a valid HTML document"
            obj.status_code = 404
            return obj

        # Returns non-200 status
        requestsPatcher = mock.patch("requests.post", side_effect=flawed_response)
        mockRequests = requestsPatcher.start()

        self.assertRaisesRegexp(APIError, "XML-API returned error code 404",
                                api.postXMLEndpoint, "TestURL")

        requestsPatcher.stop()


if __name__ == "__main__":
    unittest.main()
