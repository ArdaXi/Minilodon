import itertools
import unittest
import time
from unittest.mock import Mock, MagicMock, patch

from freezegun import freeze_time

def _command(name, control=False):
    return lambda f: f

def _message():
    return lambda f: f

mockMinilodon = Mock(command=_command, message=_message)
mockYDL = Mock()

patcher = patch('minilodon.minilodon.Minilodon', Mock(return_value=mockMinilodon))
patcher2 = patch('youtube_dl.YoutubeDL', Mock(return_value=mockYDL))
patcher.start()
patcher2.start()
import minilodon.bot as bot
patcher.stop()
patcher2.stop()

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

    def test_updateme_noargs(self):
        result = bot.updateme('nick', ['updateme'])
        self.assertEqual(result[:6], 'Usage:')

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
    def test_toggle_spy(self, _stop_spy):
        bot.spy_function = Mock()
        bot.spy_timer = Mock()
        bot.spy('nick', ['spy'])
        bot.spy_timer.cancel.assert_called_once_with()
        _stop_spy.assert_called_once_with()

class ListTest(unittest.TestCase):
    def test_no_args(self):
        result = bot.list_all('nick', ['list'])
        self.assertEqual(result[:6], 'Usage:')

    @patch('minilodon.bot.parse_actions')
    def test_no_category(self, _parse_actions):
        _parse_actions.return_value = {}
        result = bot.list_all('nick', ['list', 'category'])
        self.assertEqual(result, 'category niet gevonden.')

    @patch('minilodon.bot.parse_actions')
    def test_list(self, _parse_actions):
        _parse_actions.return_value = {'category': {'key': 'value'}}
        result = bot.list_all('nick', ['list', 'category'])
        bot.bot.send_priv_msg.assert_called_with('nick',
                                                 'Alle category: key')
        self.assertEqual(result, 'Zie prive voor een lijst van alle opties.')

class RollTest(unittest.TestCase):
    def test_no_args(self):
        result = bot.roll('nick', ['roll'])
        self.assertEqual(result[:6], 'Usage:')

    def test_invalid(self):
        result = bot.roll('nick', ['roll', 'dice'])
        self.assertEqual(result[:6], 'Usage:')

    def test_toomuch(self):
        result = bot.roll('nick', ['roll', '9001d6'])
        self.assertEqual(result, 'Nice try.')

    def test_toobig(self):
        result = bot.roll('nick', ['roll', 'd9001'])
        self.assertEqual(result, "That's not a real die.")

    @patch('random.randint', return_value=4)
    def test_d6(self, _randint):
        result = bot.roll('nick', ['roll', 'd6'])
        self.assertEqual(result, 'nick rolled: ⚃')
        _randint.assert_called_once_with(1, 6)

    @patch('random.randint', return_value=4)
    def test_2d6(self, _randint):
        result = bot.roll('nick', ['roll', '2d6'])
        self.assertEqual(result, 'nick rolled: ⚃ ⚃')
        _randint.assert_called_with(1, 6)

    @patch('random.randint', return_value=16)
    def test_2d20(self, _randint):
        result = bot.roll('nick', ['roll', '2d20'])
        self.assertEqual(result, 'nick rolled: 16 16')
        _randint.assert_called_with(1, 20)

class MessageTest(unittest.TestCase):
    @patch('minilodon.bot.video')
    def test_video(self, _video):
        bot.spy_function = None
        list(bot.on_message('nick', 'http://example.com'))
        _video.assert_called_once_with('http://example.com')

    @patch('minilodon.bot.video')
    def test_novideo(self, _video):
        bot.spy_function = None
        list(bot.on_message('nick', 'gopher://example.com'))
        self.assertFalse(_video.called)

    def test_spy(self):
        bot.spy_function = Mock()
        list(bot.on_message('nick', 'Hello World!'))
        bot.spy_function.assert_called_once_with('nick', 'Hello World!')
        bot.spy_function = None

class VideoTest(unittest.TestCase):
    def test_error(self):
        mockYDL.extract_info.side_effect = bot.DownloadError('')
        result = bot.video('url')
        self.assertEqual(result, None)
        mockYDL.extract_info.side_effect = None

    def test_generic(self):
        mockYDL.extract_info.return_value = {'extractor_key': 'Generic',
                                             'title': 'title'}
        result = bot.video('url')
        self.assertEqual(result, None)
        mockYDL.extract_info.return_value = None

    def test_no_views(self):
        mockYDL.extract_info.return_value = {'extractor_key': 'extractor',
                                             'title': 'title'}
        result = bot.video('url')
        self.assertEqual(result, '[extractor] title')
        mockYDL.extract_info.return_value = None

    def test_with_views(self):
        mockYDL.extract_info.return_value = {'extractor_key': 'extractor',
                                             'title': 'title',
                                             'view_count': 1000}
        result = bot.video('url')
        self.assertEqual(result, '[extractor] title | 1,000 views')
        mockYDL.extract_info.return_value = None

    def test_with_duration(self):
        mockYDL.extract_info.return_value = {'extractor_key': 'extractor',
                                             'title': 'title',
                                             'duration': 124}
        result = bot.video('url')
        self.assertEqual(result, '[extractor] title [2:04]')

    def test_with_hour_duraction(self):
        mockYDL.extract_info.return_value = {'extractor_key': 'extractor',
                                             'title': 'title',
                                             'duration': 3661}
        result = bot.video('url')
        self.assertEqual(result, '[extractor] title [1:01:01]')

    def test_with_views_and_duration(self):
        mockYDL.extract_info.return_value = {'extractor_key': 'extractor',
                                             'title': 'title',
                                             'view_count': 1024,
                                             'duration': 124}
        result = bot.video('url')
        self.assertEqual(result, '[extractor] title [2:04] | 1,024 views')

class ActionsTest(unittest.TestCase):
    @patch('builtins.open')
    @patch('json.load')
    def test_parse(self, _load, _open):
        bot.parse_actions('file.json')
        _open.assert_called_once_with('file.json')
        _load.assert_called_once()

    @patch('minilodon.bot.parse_actions')
    def test_load(self, _parse_actions):
        _parse_actions.return_value = {'category': {'key': '{victim} {nick}'}}
        bot.bot.commands = {}
        bot.load_actions()
        self.assertIn('category', bot.bot.commands)
        lookup = bot.bot.commands['category']
        result = lookup('nick', ['category'])
        self.assertIsNone(result)
        result = lookup('nick', ['category', 'key'])
        self.assertEqual(result, 'nick nick')
        result = lookup('nick', ['category', 'key', 'victim'])
        self.assertEqual(result, 'victim nick')
        result = lookup('nick', ['category', 'false'])
        self.assertEqual(result, 'Kon false niet vinden in category.')
