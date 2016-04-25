import unittest
import mock

from vmbot.fun import Chains


class TestChains(unittest.TestCase):
    defaultMess = "SenderName"
    defaultArgs = ""

    def setUp(self):
        self.chains = Chains()

    def tearDown(self):
        del self.chains

    @mock.patch("random.randint", return_value=1)
    def test_every_out(self, mockRandom):
        self.assertEqual(self.chains.bot_every(self.defaultMess, self.defaultArgs), "lion")

    @mock.patch("random.randint", return_value=2)
    def test_every_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_every(self.defaultMess, self.defaultArgs))

    def test_every_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_every(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_lion_out(self, mockRandom):
        self.assertEqual(self.chains.bot_lion(self.defaultMess, self.defaultArgs), "except")

    @mock.patch("random.randint", return_value=2)
    def test_lion_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_lion(self.defaultMess, self.defaultArgs))

    def test_lion_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_lion(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_except_out(self, mockRandom):
        self.assertEqual(self.chains.bot_except(self.defaultMess, self.defaultArgs), "for")

    @mock.patch("random.randint", return_value=2)
    def test_except_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_except(self.defaultMess, self.defaultArgs))

    def test_except_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_except(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_for_out(self, mockRandom):
        self.assertEqual(self.chains.bot_for(self.defaultMess, self.defaultArgs), "at")

    @mock.patch("random.randint", return_value=2)
    def test_for_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_for(self.defaultMess, self.defaultArgs))

    def test_for_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_for(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_at_out(self, mockRandom):
        self.assertEqual(self.chains.bot_at(self.defaultMess, self.defaultArgs), "most")

    @mock.patch("random.randint", return_value=2)
    def test_at_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_at(self.defaultMess, self.defaultArgs))

    def test_at_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_at(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_most_out(self, mockRandom):
        self.assertEqual(self.chains.bot_most(self.defaultMess, self.defaultArgs), "one")

    @mock.patch("random.randint", return_value=2)
    def test_most_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_most(self.defaultMess, self.defaultArgs))

    def test_most_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_most(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_one_out(self, mockRandom):
        self.assertEqual(self.chains.bot_one(self.defaultMess, self.defaultArgs), ":bravo:")

    @mock.patch("random.randint", return_value=2)
    def test_one_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_one(self.defaultMess, self.defaultArgs))

    def test_one_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_one(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_z_out(self, mockRandom):
        self.assertEqual(self.chains.bot_z(self.defaultMess, self.defaultArgs), "0")

    @mock.patch("random.randint", return_value=2)
    def test_z_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_z(self.defaultMess, self.defaultArgs))

    def test_z_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_z(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_0_out(self, mockRandom):
        self.assertEqual(self.chains.bot_0(self.defaultMess, self.defaultArgs), "r")

    @mock.patch("random.randint", return_value=2)
    def test_0_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_0(self.defaultMess, self.defaultArgs))

    def test_0_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_0(self.defaultMess, testArg))

    @mock.patch("random.randint", return_value=1)
    def test_r_out(self, mockRandom):
        self.assertEqual(self.chains.bot_r(self.defaultMess, self.defaultArgs), "z")

    @mock.patch("random.randint", return_value=2)
    def test_r_noout(self, mockRandom):
        self.assertIsNone(self.chains.bot_r(self.defaultMess, self.defaultArgs))

    def test_r_args(self):
        testArg = "TestArg"
        self.assertIsNone(self.chains.bot_r(self.defaultMess, testArg))


if __name__ == "__main__":
    unittest.main()
