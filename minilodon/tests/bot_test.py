import itertools
import unittest
from unittest.mock import Mock, patch

import irc

class mockMinilodon():
    def __init__(self, config):
        pass

    def command(self, name, control=False):
        return lambda f: f

    def message(self):
        return lambda f: f

patcher = patch('minilodon.minilodon.Minilodon', mockMinilodon)
patcher.start()
import minilodon.bot as bot
patcher.stop()

class UpdateTest(unittest.TestCase):
    def test_no_args(self):
        result = list(bot.update('nick', []))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][:6], 'Usage:')

    def test_three_args(self):
        result = list(bot.update('nick', ['update', 'category', 'key']))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][:6], 'Usage:')

    def test_invalid_key(self):
        result = list(bot.update('nick', ['update', 'category',
                                          'key', '{who}']))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "Failed to parse message on 'who'")

    @patch('minilodon.bot.load_actions')
    @patch('minilodon.bot.parse_actions')
    @patch('json.dump')
    @patch('builtins.open')
    def test_update(self, _open, _dump, _parse_actions, _load_actions):
        _parse_actions.return_value = {}
        result = list(bot.update('nick', ['update', 'category', 'key',
                                          'hello', 'world']))
        self.assertTrue(_dump.called)
        actions = _dump.call_args[0][0]
        self.assertEqual(actions, {'category': {'key': 'hello world'}})
        _load_actions.assert_called_once_with()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 'key added to category.')
    
    @patch('minilodon.bot.load_actions')
    @patch('minilodon.bot.parse_actions')
    @patch('json.dump')
    @patch('builtins.open')
    def test_long_update(self, _open, _dump, _parse_actions, _load_actions):
        _parse_actions.return_value = {}
        teststr = list(itertools.repeat('hello', 50))
        result = list(bot.update('nick', ['update', 'category',
                                          'key'] + teststr))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'Warning: Entry too long, message will be wrapped.')
        self.assertEqual(result[1], 'key added to category.')
