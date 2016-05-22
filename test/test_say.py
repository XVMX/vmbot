import unittest
import mock

import re

from vmbot.fun import Say


class TestSay(unittest.TestCase):
    defaultMess = "SenderName"
    defaultArgs = ""

    def setUp(self):
        self.say = Say()
        # Mock self.get_sender_username(mess) to return mess
        self.say.get_sender_username = mock.MagicMock(name="get_sender_username",
                                                      side_effect=lambda arg: arg)

    def tearDown(self):
        del self.say

    def test_fishsay(self):
        self.assertIn(self.say.fishsay(self.defaultMess, self.defaultArgs), Say.fishisms)

    def test_pimpsay_noargs(self):
        self.assertIn(self.say.pimpsay(self.defaultMess, self.defaultArgs), Say.pimpisms)

    def test_pimpsay_args(self):
        testArg = "TestArg"
        self.assertIn(self.say.pimpsay(self.defaultMess, testArg),
                      ["{} {}".format(testArg, line) for line in Say.pimpisms])

    def test_arelesay(self):
        self.assertIn(self.say.arelesay(self.defaultMess, self.defaultArgs),
                      ["https://youtu.be/{}".format(line) for line in Say.areleisms])

    def test_nicksay(self):
        res = self.say.nicksay(self.defaultMess, self.defaultArgs)

        if not any([re.match(line.format("0{2,}"), res) for line in Say.nickisms]):
            self.fail("nicksay didn't return a valid nickism")

    def test_chasesay_noargs(self):
        self.assertEqual(self.say.chasesay(self.defaultMess, self.defaultArgs),
                         "{}, would you PLEASE".format(self.defaultMess))

    def test_chasesay_args(self):
        testArg = "TestArg"
        self.assertEqual(self.say.chasesay(self.defaultMess, testArg),
                         "{}, would you PLEASE".format(testArg))

    def test_kairksay_noargs(self):
        self.assertIn(self.say.kairksay(self.defaultMess, self.defaultArgs),
                      ["{}, {} -Kairk".format(self.defaultMess, line) for line in Say.kairkisms])

    def test_kairksay_args(self):
        testArg = "TestArg"
        self.assertIn(self.say.kairksay(self.defaultMess, testArg),
                      ["{}, {} -Kairk".format(testArg, line) for line in Say.kairkisms])

    def test_dariussay_noargs(self):
        self.assertIn(self.say.dariussay(self.defaultMess, self.defaultArgs),
                      ["{}, {}".format(self.defaultMess, line) for line in Say.dariusisms])

    def test_dariussay_args(self):
        testArg = "TestArg"
        self.assertIn(self.say.dariussay(self.defaultMess, testArg),
                      ["{}, {}".format(testArg, line) for line in Say.dariusisms])

    def test_scottsay_noargs(self):
        self.assertIn(self.say.scottsay(self.defaultMess, self.defaultArgs), Say.scottisms)

    def test_scottsay_args(self):
        testArg = "TestArg"
        self.assertIn(self.say.scottsay(self.defaultMess, testArg),
                      ["{}, {}".format(testArg, line) for line in Say.scottisms])

    def test_eksay_noargs(self):
        self.assertEqual(self.say.eksay(self.defaultMess, self.defaultArgs),
                         ":rip: {}".format(self.defaultMess))

    def test_eksay_args(self):
        testArg = "TestArg"
        self.assertEqual(self.say.eksay(self.defaultMess, testArg), ":rip: {}".format(testArg))

    def test_jokersay_noargs(self):
        self.assertIn(self.say.jokersay(self.defaultMess, self.defaultArgs), Say.jokerisms)

    def test_jokersay_args(self):
        testArg = "TestArg"
        self.assertIn(self.say.jokersay(self.defaultMess, testArg),
                      ["{} {}".format(testArg, line) for line in Say.jokerisms])

    def test_8ball_noargs(self):
        self.assertEqual(self.say.bot_8ball(self.defaultMess, self.defaultArgs),
                         "You will need to provide a question for me to answer")

    def test_8ball_args(self):
        testArg = "TestArg"
        self.assertIn(self.say.bot_8ball(self.defaultMess, testArg), Say.eball_answers)

    def test_sayhi_noargs(self):
        self.assertEqual(self.say.sayhi(self.defaultMess, self.defaultArgs),
                         "Hi {}!".format(self.defaultMess))

    def test_sayhi_args(self):
        testArg = "TestArg"
        self.assertEqual(self.say.sayhi(self.defaultMess, testArg),
                         "Hi {}!".format(testArg))


if __name__ == "__main__":
    unittest.main()
