import unittest
from unittest.mock import Mock
from threading import Event

import irc

from ..kicker import Kicker
from ..minilodon import Minilodon

class KickerTest(unittest.TestCase):
    def setUp(self):
        self.bot = Mock(spec=Minilodon)
        self.bot.connection = Mock()
        self.channel = '#test'
        self.nick = 'nick'
        self.idletime = 10.0
        self.resetter = Mock(spec=Event)
        self.kicker = Kicker(self.bot, self.channel, self.nick, self.idletime)
        self.kicker.resetter = self.resetter

    def test_run_once(self):
        self.resetter.isSet.return_value = False
        self.kicker.run()
        self.assertEqual(self.bot.connection.kick.call_count, 1)
        self.assertEqual(self.bot.connection.kick.call_args[0][0], self.channel)
        self.assertEqual(self.bot.connection.kick.call_args[0][1], self.nick)
        self.assertEqual(self.bot.send_msg.call_count, 1)
        self.assertEqual(self.bot.send_msg.call_args[0][1], True)
        self.bot.reset_mock()

    def test_run_twice(self):
        self.resetter.isSet.side_effect = [True, False]
        self.kicker.run()
        self.resetter.clear.assert_called_once_with()
        self.bot.reset_mock()

    def test_cancel(self):
        def wait(time):
            self.kicker.cancel()
        self.resetter.isSet.side_effect = lambda: self.resetter.set.called
        self.resetter.wait.side_effect = wait
        self.kicker.run()
        assert(not self.bot.connection.kick.called)
        assert(self.resetter.clear.called)
