# coding: utf-8

from __future__ import absolute_import, division, unicode_literals, print_function

import unittest
import mock

import re

from vmbot.helpers.files import HANDEY_QUOTES
from vmbot.fun import (EBALL_ANSWERS, FISHISMS, PIMPISMS, ARELEISMS, NICKISMS,
                       KAIRKISMS, DARIUSISMS, SCOTTISMS, JOKERISMS, PUBBIESMACK)

from vmbot.fun import Say


class TestSay(unittest.TestCase):
    default_mess = "SenderName"
    default_args = ""

    def setUp(self):
        self.say = Say()
        # Mock self.get_sender_username(mess) to return mess
        self.say.get_sender_username = mock.MagicMock(name="get_sender_username",
                                                      side_effect=lambda arg: arg)

    def tearDown(self):
        del self.say

    def test_pubbiesmack(self):
        self.assertIn(self.say.pubbiesmack(self.default_mess),
                      [line.format(nick=self.default_mess) for line in PUBBIESMACK])

    def test_fishsay(self):
        self.assertIn(self.say.fishsay(self.default_mess, self.default_args), FISHISMS)

    def test_pimpsay_noargs(self):
        self.assertIn(self.say.pimpsay(self.default_mess, self.default_args), PIMPISMS)

    def test_pimpsay_args(self):
        test_arg = "TestArg"
        self.assertIn(self.say.pimpsay(self.default_mess, test_arg),
                      [test_arg + ' ' + line for line in PIMPISMS])

    def test_arelesay(self):
        self.assertIn(self.say.arelesay(self.default_mess, self.default_args),
                      ["https://youtu.be/{}".format(line) for line in ARELEISMS])

    def test_nicksay(self):
        res = self.say.nicksay(self.default_mess, self.default_args)

        if not any(re.match(line.format("0{2,}"), res) for line in NICKISMS):
            self.fail("nicksay didn't return a valid nickism")

    def test_chasesay_noargs(self):
        self.assertEqual(self.say.chasesay(self.default_mess, self.default_args),
                         "{}, would you PLEASE".format(self.default_mess))

    def test_chasesay_args(self):
        test_arg = "TestArg"
        self.assertEqual(self.say.chasesay(self.default_mess, test_arg),
                         "{}, would you PLEASE".format(test_arg))

    def test_kairksay_noargs(self):
        self.assertIn(self.say.kairksay(self.default_mess, self.default_args),
                      ["{}, {} -Kairk".format(self.default_mess, line) for line in KAIRKISMS])

    def test_kairksay_args(self):
        test_arg = "TestArg"
        self.assertIn(self.say.kairksay(self.default_mess, test_arg),
                      ["{}, {} -Kairk".format(test_arg, line) for line in KAIRKISMS])

    def test_dariussay_noargs(self):
        self.assertIn(self.say.dariussay(self.default_mess, self.default_args),
                      ["{}, {}".format(self.default_mess, line) for line in DARIUSISMS])

    def test_dariussay_args(self):
        test_arg = "TestArg"
        self.assertIn(self.say.dariussay(self.default_mess, test_arg),
                      ["{}, {}".format(test_arg, line) for line in DARIUSISMS])

    def test_scottsay_noargs(self):
        self.assertIn(self.say.scottsay(self.default_mess, self.default_args), SCOTTISMS)

    def test_scottsay_args(self):
        test_arg = "TestArg"
        self.assertIn(self.say.scottsay(self.default_mess, test_arg),
                      ["{}, {}".format(test_arg, line) for line in SCOTTISMS])

    def test_eksay_noargs(self):
        self.assertEqual(self.say.eksay(self.default_mess, self.default_args),
                         ":rip: {}".format(self.default_mess))

    def test_eksay_args(self):
        test_arg = "TestArg"
        self.assertEqual(self.say.eksay(self.default_mess, test_arg), ":rip: {}".format(test_arg))

    def test_jokersay_noargs(self):
        self.assertIn(self.say.jokersay(self.default_mess, self.default_args), JOKERISMS)

    def test_jokersay_args(self):
        test_arg = "TestArg"
        self.assertIn(self.say.jokersay(self.default_mess, test_arg),
                      [test_arg + ' ' + line for line in JOKERISMS])

    def test_handysay(self):
        with open(HANDEY_QUOTES, 'r') as says_file:
            says = says_file.read()

        self.assertIn(self.say.handysay(self.default_mess, self.default_args), says)

    def test_8ball_noargs(self):
        self.assertEqual(self.say.bot_8ball(self.default_mess, self.default_args),
                         "Please provide a question to answer")

    def test_8ball_args(self):
        test_arg = "TestArg"
        self.assertIn(self.say.bot_8ball(self.default_mess, test_arg), EBALL_ANSWERS)

    def test_sayhi_noargs(self):
        self.assertEqual(self.say.sayhi(self.default_mess, self.default_args),
                         "Hi {}!".format(self.default_mess))

    def test_sayhi_args(self):
        test_arg = "TestArg"
        self.assertEqual(self.say.sayhi(self.default_mess, test_arg),
                         "Hi {}!".format(test_arg))


if __name__ == "__main__":
    unittest.main()
