# coding: utf-8

import unittest
import mock

from vmbot.fun import Chains


class TestChains(unittest.TestCase):
    default_mess = ""
    default_args = ""

    def setUp(self):
        self.chains = Chains()

    def tearDown(self):
        del self.chains

    @mock.patch("random.randint", return_value=1)
    def test_every_out(self, mock_random):
        self.assertEqual(self.chains.bot_every(self.default_mess, self.default_args), "lion")

    @mock.patch("random.randint", return_value=2)
    def test_every_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_every(self.default_mess, self.default_args))

    def test_every_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_every(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_lion_out(self, mock_random):
        self.assertEqual(self.chains.bot_lion(self.default_mess, self.default_args), "except")

    @mock.patch("random.randint", return_value=2)
    def test_lion_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_lion(self.default_mess, self.default_args))

    def test_lion_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_lion(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_except_out(self, mock_random):
        self.assertEqual(self.chains.bot_except(self.default_mess, self.default_args), "for")

    @mock.patch("random.randint", return_value=2)
    def test_except_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_except(self.default_mess, self.default_args))

    def test_except_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_except(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_for_out(self, mock_random):
        self.assertEqual(self.chains.bot_for(self.default_mess, self.default_args), "at")

    @mock.patch("random.randint", return_value=2)
    def test_for_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_for(self.default_mess, self.default_args))

    def test_for_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_for(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_at_out(self, mock_random):
        self.assertEqual(self.chains.bot_at(self.default_mess, self.default_args), "most")

    @mock.patch("random.randint", return_value=2)
    def test_at_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_at(self.default_mess, self.default_args))

    def test_at_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_at(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_most_out(self, mock_random):
        self.assertEqual(self.chains.bot_most(self.default_mess, self.default_args), "one")

    @mock.patch("random.randint", return_value=2)
    def test_most_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_most(self.default_mess, self.default_args))

    def test_most_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_most(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_one_out(self, mock_random):
        self.assertEqual(self.chains.bot_one(self.default_mess, self.default_args), ":bravo:")

    @mock.patch("random.randint", return_value=2)
    def test_one_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_one(self.default_mess, self.default_args))

    def test_one_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_one(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_z_out(self, mock_random):
        self.assertEqual(self.chains.bot_z(self.default_mess, self.default_args), "0")

    @mock.patch("random.randint", return_value=2)
    def test_z_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_z(self.default_mess, self.default_args))

    def test_z_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_z(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_0_out(self, mock_random):
        self.assertEqual(self.chains.bot_0(self.default_mess, self.default_args), "r")

    @mock.patch("random.randint", return_value=2)
    def test_0_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_0(self.default_mess, self.default_args))

    def test_0_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_0(self.default_mess, test_arg))

    @mock.patch("random.randint", return_value=1)
    def test_r_out(self, mock_random):
        self.assertEqual(self.chains.bot_r(self.default_mess, self.default_args), "z")

    @mock.patch("random.randint", return_value=2)
    def test_r_noout(self, mock_random):
        self.assertIsNone(self.chains.bot_r(self.default_mess, self.default_args))

    def test_r_args(self):
        test_arg = "TestArg"
        self.assertIsNone(self.chains.bot_r(self.default_mess, test_arg))


if __name__ == "__main__":
    unittest.main()
