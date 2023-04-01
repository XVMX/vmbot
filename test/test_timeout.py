# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import time

from vmbot.helpers.exceptions import TimeoutError

from vmbot.helpers import decorators
from vmbot.helpers.decorators import timeout


@timeout(1)
def timeout_success():
    return True


@timeout(1)
def timeout_fail():
    time.sleep(3)
    return True


@timeout(1, "TestException")
def timeout_msg():
    time.sleep(3)
    return True


@unittest.skipUnless(decorators.HAS_TIMEOUT, "OS doesn't support timeout decorator")
class TestTimeout(unittest.TestCase):
    def test_timeout(self):
        self.assertRaises(TimeoutError, timeout_fail)

    def test_timeout_notimeout(self):
        self.assertTrue(timeout_success())

    def test_timeout_msg(self):
        self.assertRaisesRegexp(TimeoutError, "TestException", timeout_msg)


@mock.patch("vmbot.helpers.decorators.HAS_TIMEOUT", new=False)
class TestTimeoutFallback(unittest.TestCase):
    def test_timeout_any(self):
        # Have to be created dynamically for HAS_TIMEOUT patch to take effect
        @timeout(1)
        def local_success():
            return True

        @timeout(1)
        def local_fail():
            time.sleep(3)
            return True

        self.assertRaises(TimeoutError, local_success)
        self.assertRaises(TimeoutError, local_fail)


if __name__ == "__main__":
    unittest.main()
