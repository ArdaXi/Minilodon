import unittest
from unittest.mock import Mock, patch

from irc.client import Event, NickMask

from minilodon.minilodon import Minilodon

CONFIG = {
    'server': 'server',
    'port': 'port',
    'nick': 'nick',
    'mainchannel': '#channel',
    'controlchannel': '#controlchannel',
    'password': 'password',
    'idletime': 3600.0
}

class MinilodonTest(unittest.TestCase):
    @patch('irc.bot.SingleServerIRCBot.__init__')
    @patch('json.load')
    @patch('builtins.open')
    def setUp(self, _open, _load, _bot_init):
        _load.return_value = CONFIG
        self.bot = Minilodon('config.json')
        self.connection = Mock()
        self.connection.get_nickname.return_value = 'nick'
        self.bot.connection = self.connection
        mask = NickMask.from_params('nick', 'user', 'host')
        self.event = Event(type=None, source=mask, target='target',
                           arguments=['arg1', 'arg2'])

    def test_nick_in_use(self):
        self.bot.on_nicknameinuse(self.connection, {})
        self.connection.nick.assert_called_once_with('nick_')

    def test_disconnect(self):
        with self.assertRaises(Exception) as cm:
            self.bot.on_disconnect(self.connection, self.event)
        error = cm.exception
        self.assertEqual(str(error), 'Disconnected by nick!user@host (arg1 arg2)')

    def test_welcome_with_password(self):
        self.bot.send_priv_msg = Mock()
        self.bot.on_welcome(self.connection, self.event)
        self.connection.mode.assert_called_once_with('nick', '-g')
        self.bot.send_priv_msg.assert_called_once_with('NickServ',
                                                       'IDENTIFY password')
        self.assertFalse(self.connection.join.called)

    def test_welcome_no_password(self):
        self.bot.password = None
        self.bot.on_welcome(self.connection, self.event)
        self.connection.mode.assert_called_once_with('nick', '-g')
        self.assertEqual(self.connection.join.call_count, 2)
        self.connection.join.assert_any_call('#controlchannel')
        self.connection.join.assert_called_with('#channel')

    def test_privnotice_identify(self):
        self.bot.on_privnotice(self.connection, self.event)
        self.assertFalse(self.connection.join.called)
        source = NickMask.from_params('NickServ', 'user', 'host')
        event = Event(type=None, source=source, target='target',
                      arguments=['Password accepted - you are now recognized.'])
        self.bot.on_privnotice(self.connection, event)
        self.assertEqual(self.connection.join.call_count, 2)
        self.connection.join.assert_any_call('#controlchannel')
        self.connection.join.assert_called_with('#channel')

    def test_pubmsg(self):
        self.bot.log = Mock()
        self.bot.on_pubmsg(self.connection, self.event)
        self.bot.log.assert_called_once_with('target', '<nick> arg1 arg2')

    def test_action(self):
        self.bot.log = Mock()
        self.bot.on_pubmsg_main = Mock()
        self.event.target = '#channel'
        self.bot.on_action(self.connection, self.event)
        self.bot.log.assert_called_once_with('#channel', 'nick arg1 arg2')
        self.bot.on_pubmsg_main.assert_called_once_with(self.event)

    def test_banned(self):
        self.bot.extrachannels = ['arg1']
        self.bot.send_msg = Mock()
        self.bot.on_bannedfromchan(self.connection, self.event)
        self.bot.send_msg.assert_called_once_with('Failed to join channel arg1', True)
        self.assertEqual(self.bot.extrachannels, [])

    def test_part_self(self):
        self.bot.send_msg = Mock()
        log = Mock()
        self.bot.logs = {'target': log}
        self.bot.on_part(self.connection, self.event)
        self.bot.send_msg.assert_called_once_with('Left target', True)
        log.close.assert_called_once_with()
        self.assertEqual(self.bot.logs, {})

    def test_part_other(self):
        mask = NickMask.from_params('victim', 'user', 'host')
        self.event.source = mask
        self.bot.on_leave = Mock()
        self.bot.log = Mock()
        self.bot.on_part(self.connection, self.event)
        self.bot.on_leave.assert_called_once_with('victim')
        self.bot.log.assert_called_once_with('target', 'victim left target')

    def test_quit(self):
        self.event.target = '#channel'
        self.bot.on_leave = Mock()
        self.bot.log = Mock()
        self.bot.on_quit(self.connection, self.event)
        self.bot.on_leave.assert_called_once_with('nick')
        self.bot.log.assert_called_with('#channel', 'nick quit')
