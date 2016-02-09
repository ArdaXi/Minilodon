import itertools
import unittest
from unittest.mock import Mock, patch

import irc

def _command(name, control=False):
    return lambda f: f

def _message():
    return lambda f: f

mockMinilodon = Mock(command=_command, message=_message)

patcher = patch('minilodon.minilodon.Minilodon', Mock(return_value=mockMinilodon))
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

    @patch('minilodon.bot.update')
    def test_updateme(self, _update):
        bot.updateme('nick', ['updateme', 'key', 'category', 'hello', 'world'])
        _update.assert_called_with('nick', ['updateme', 'key', 'category',
                                            '/me', 'hello', 'world'])

class DeleteTest(unittest.TestCase):
    def test_no_args(self):
        result = bot.delete('nick', [])
        self.assertEqual(result[:6], 'Usage:')

    @patch('minilodon.bot.parse_actions')
    def test_no_category(self, _parse_actions):
        _parse_actions.return_value = {}
        result = bot.delete('nick', ['delete', 'category', 'key'])
        self.assertEqual(result, 'Category category not found!')

    @patch('minilodon.bot.parse_actions')
    def test_no_key(self, _parse_actions):
        _parse_actions.return_value = {'category': {}}
        result = bot.delete('nick', ['delete', 'category', 'key'])
        self.assertEqual(result, 'Key key not found in category')

    @patch('minilodon.bot.load_actions')
    @patch('minilodon.bot.parse_actions')
    @patch('json.dump')
    @patch('builtins.open')
    def test_delete(self, _open, _dump, _parse_actions, _load_actions):
        _parse_actions.return_value = {'category': {'key': 'value'}}
        result = bot.delete('nick', ['delete', 'category', 'key'])
        self.assertTrue(_dump.called)
        actions = _dump.call_args[0][0]
        self.assertEqual(actions, {'category': {}})
        _load_actions.assert_called_once_with()
        self.assertEqual(result, 'key removed from category.')

class SayTest(unittest.TestCase):
    def test_no_args(self):
        result = bot.say('nick', ['say'])
        self.assertEqual(result[:6], 'Usage:')

    def test_say(self):
        result = bot.say('nick', ['say', 'hello', 'world'])
        bot.bot.send_msg.assert_called_once_with('hello world')
        self.assertEqual(result, None)
