import itertools
import unittest
import time
from unittest.mock import Mock, patch

from freezegun import freeze_time

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

class JoinTest(unittest.TestCase):
    def test_no_args(self):
        result = bot.join('nick', ['join'])
        self.assertEqual(result[:6], 'Usage:')

    def test_join(self):
        result = bot.join('nick', ['join', '#test'])
        bot.bot.join.assert_called_once_with('#test')
        self.assertEqual(result, None)

    def test_part_no_args(self):
        result = bot.part('nick', ['part'])
        self.assertEqual(result[:6], 'Usage:')

    def test_part(self):
        result = bot.part('nick', ['part', '#test'])
        bot.bot.part.assert_called_once_with('#test')
        self.assertEqual(result, None)

class IdleTest(unittest.TestCase):
    def setUp(self):
        bot.bot.alone = False

    def test_idle_alone(self):
        bot.bot.alone = 'victim'
        result = bot.idle('nick', ['idle'])
        self.assertEqual(result, 'victim is alone in the room.')
        bot.bot.alone = False

    @freeze_time('01-01-01 12:00:00')
    def test_idle(self):
        data = 'nick', time.time() - 3661
        bot.bot.get_idle_times.return_value = [data]
        result = list(bot.idle('nick', []))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 'nick is 1 uur, 1 minuten en 1 seconden idle.')
        bot.bot.get_idle_times.reset_mock()

class SpyTest(unittest.TestCase):
    def test_stop_spy(self):
        bot.spy_function = 'f'
        bot.spy_timer = 't'
        result = bot.stop_spy()
        self.assertEqual(bot.spy_function, None)
        self.assertEqual(bot.spy_timer, None)
        self.assertEqual(result, 'Spy functie gestopt.')

    @patch('threading.Timer')
    def test_spy(self, _timer):
        bot.bot.channel = '#test'
        bot.spy_function = None
        bot.spy_timer = None
        result = bot.spy('nick', ['spy'])
        bot.spy_function('victim', 'Hello World!')
        bot.bot.send_msg.assert_called_with('<victim> Hello World!', True)
        self.assertEqual(result, 'Room #test wordt 15 minuten bespioneerd.')
        bot.spy_function = None
        bot.spy_timer = None

    @patch('minilodon.bot.stop_spy')
    def toggle_spy(self, _stop_spy):
        bot.spy_function = Mock()
        bot.spy_timer = Mock()
        bot.spy('nick', ['spy'])
        bot.spy_timer.cancel.assert_called_once_with()
        _stop_spy.assert_called_once_with()
