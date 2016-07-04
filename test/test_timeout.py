# coding: utf-8

import unittest

import time
import signal

from vmbot.helpers.exceptions import TimeoutError

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


@unittest.skipUnless(hasattr(signal, "alarm"), "OS doesn't support SIGALRM")
class TestTimeout(unittest.TestCase):
    def test_timeout(self):
        self.assertRaises(TimeoutError, timeout_fail)

    def test_timeout_notimeout(self):
        self.assertTrue(timeout_success())

    def test_timeout_msg(self):
        self.assertRaisesRegexp(TimeoutError, "TestException", timeout_msg)


if __name__ == "__main__":
    unittest.main()
