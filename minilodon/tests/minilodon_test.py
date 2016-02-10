import itertools
import unittest
from unittest.mock import Mock, MagicMock, patch

from irc.client import Event, NickMask
from freezegun import freeze_time

from minilodon.minilodon import Minilodon
from minilodon.kicker import Kicker

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

    def test_pubmsg_main(self):
        self.bot.log = Mock()
        self.bot.kickers = {}
        self.bot.add_kicker = Mock()
        self.bot.send_msg = Mock()
        self.bot.do_command = Mock(return_value='msg')
        on_message = Mock(return_value='msg2')
        self.bot.on_message = [on_message]
        self.event.target = '#channel'
        self.event.arguments = ['!command arg1']
        self.bot.on_pubmsg(self.connection, self.event)
        self.bot.add_kicker.assert_called_once_with('nick')
        self.bot.do_command.assert_called_once_with(self.event, 'command arg1')
        on_message.assert_called_once_with('nick', '!command arg1')
        self.bot.send_msg.assert_called_with('msg2')
        self.bot.send_msg.assert_any_call('msg')

    def test_pubmsg_main2(self):
        self.bot.log = Mock()
        kicker = Mock()
        self.bot.kickers = {'nick': kicker}
        self.bot.on_message = None
        self.event.target = '#channel'
        self.bot.on_pubmsg(self.connection, self.event)
        kicker.reset.assert_called_once_with()

    def test_pubmsg_control(self):
        self.bot.log = Mock()
        self.event.target = '#controlchannel'
        self.event.arguments = ['!command arg1']
        self.bot.send_msg = Mock()
        self.bot.do_control_command = Mock(return_value='msg1')
        self.bot.do_command = Mock(return_value='msg2')
        self.bot.on_pubmsg(self.connection, self.event)
        self.bot.do_command.assert_called_once_with(self.event, 'command arg1')
        self.bot.do_control_command.assert_called_once_with(self.event, 'command arg1')
        self.bot.send_msg.assert_any_call('msg1', True)
        self.bot.send_msg.assert_any_call('msg2', True)

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

    def test_kick_self_main(self):
        self.event.target = '#channel'
        self.event.arguments = ['nick', 'rea', 'son']
        with self.assertRaises(Exception) as cm:
            self.bot.on_kick(self.connection, self.event)
        error = cm.exception
        self.assertEqual(str(error), 'Kicked from #channel by nick (rea son)')

    def test_kick_self_other(self):
        self.event.arguments = ['nick', 'rea', 'son']
        self.bot.send_msg = Mock()
        log = Mock()
        self.bot.logs = {'target': log}
        self.bot.extrachannels = ['target']
        self.bot.on_kick(self.connection, self.event)
        self.bot.send_msg.assert_called_once_with('Kicked from target by nick (rea son)', True)
        log.close.assert_called_once_with()
        self.assertEqual(self.bot.logs, {})
        self.assertEqual(self.bot.extrachannels, [])

    def test_kick_other(self):
        self.event.target = '#channel'
        self.event.arguments = ['victim', 'rea', 'son']
        self.bot.on_leave = Mock()
        self.bot.log = Mock()
        self.bot.on_kick(self.connection, self.event)
        self.bot.on_leave.assert_called_with('victim')
        self.bot.log.assert_called_with('#channel', 'victim was kicked from #channel by nick (rea son)')

    def test_join_main(self):
        self.bot.extrachannels = []
        self.bot.join('#channel')
        self.assertEqual(self.bot.extrachannels, [])
        self.assertFalse(self.connection.join.called)

    def test_join_existing(self):
        self.bot.extrachannels = ['#target']
        self.bot.join('#target')
        self.assertEqual(self.bot.extrachannels, ['#target'])
        self.assertFalse(self.connection.join.called)

    def test_join(self):
        self.bot.extrachannels = []
        self.bot.join('#target')
        self.assertEqual(self.bot.extrachannels, ['#target'])
        self.connection.join.assert_called_once_with('#target')

    def test_part_invalid(self):
        self.bot.extrachannels = []
        self.bot.send_msg = Mock()
        self.bot.part('#target')
        self.bot.send_msg.assert_called_once_with('Channel #target never joined via !join', True)
        self.assertFalse(self.connection.part.called)

    def test_part(self):
        self.bot.extrachannels = ['#target']
        self.bot.part('#target')
        self.assertEqual(self.bot.extrachannels, [])
        self.connection.part.assert_called_once_with('#target')

    @patch('minilodon.kicker.Kicker')
    def test_add_kicker_self(self, _kicker):
        self.bot.add_kicker('nick')
        self.assertFalse(_kicker.called)

    @patch('minilodon.kicker.Kicker')
    def test_add_kicker_existing(self, _kicker):
        self.bot.kickers = {'victim': 'sentinel'}
        self.bot.add_kicker('victim')
        self.assertFalse(_kicker.called)

    def test_get_idle_times(self):
        kicker = Mock(nick='victim', time=1)
        self.bot.kickers = {'victim': kicker}
        result = list(self.bot.get_idle_times())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ('victim', 1))

    def test_nick(self):
        kicker = Mock()
        self.bot.kickers = {'nick': kicker}
        self.bot.on_nick(self.connection, self.event)
        kicker.changenick.assert_called_once_with('target')
        self.assertEqual(self.bot.kickers, {'target': kicker})

    def test_privmsg(self):
        self.event.arguments = ['!command', 'arg']
        self.bot.do_command = Mock()
        self.bot.do_command.return_value = 'result'
        self.bot.send_priv_msg = Mock()
        self.bot.on_privmsg(self.connection, self.event)
        self.bot.do_command.assert_called_once_with(self.event, 'command')
        self.bot.send_priv_msg.assert_called_once_with('nick', 'result')

    def test_command(self):
        command = Mock()
        self.bot.commands = {'command': command}
        result = self.bot.do_command(self.event, 'command arg1')
        command.assert_called_once_with('nick', ['command', 'arg1'])

    def test_control_command(self):
        command = Mock()
        self.bot.control_commands = {'command': command}
        result = self.bot.do_control_command(self.event, 'command arg1')
        command.assert_called_once_with('nick', ['command', 'arg1'])

    def test_kick(self):
        self.bot.kick('victim', 'reason')
        self.connection.kick.assert_called_once_with('#channel', 'victim', 'reason')

    def test_log_unjoined(self):
        self.bot.logger = Mock()
        self.bot.log('#TargeT', 'msg')
        self.bot.logger.warning.assert_called_once()

    @freeze_time('01-01-01 12:00')
    def test_log(self):
        logfile = Mock(day=0)
        self.bot.logs = {'#channel': logfile}
        self.bot.reopen_logs = Mock()
        self.bot.log('#channel', 'msg')
        self.bot.reopen_logs.assert_called_once_with()
        logfile.write.assert_called_once_with('01-01-01 12:00:00 msg\n')

    @patch('minilodon.util.open_log_file')
    def test_reopen(self, _open_log_file):
        oldfile = Mock()
        newfile = Mock()
        self.bot.logs = {'#channel': oldfile}
        _open_log_file.return_value = newfile
        self.bot.reopen_logs()
        _open_log_file.assert_called_once_with('#channel')
        oldfile.close.assert_called_once_with()
        self.assertEqual(self.bot.logs, {'#channel': newfile})

    def test_send_msg_list(self):
        send_msg = self.bot.send_msg
        self.bot.send_msg = Mock()
        send_msg(['a', 'b'])
        self.bot.send_msg.assert_any_call('a', False)
        self.bot.send_msg.assert_called_with('b', False)

    @patch('minilodon.util.wrap_msg')
    def test_send_msg_wrap(self, _wrap_msg):
        _wrap_msg.return_value = 'wrapped'
        send_msg = self.bot.send_msg
        self.bot.send_msg = Mock()
        longstr = ' '.join(itertools.repeat("Hello World!", 20))
        send_msg(longstr)
        _wrap_msg.assert_called_once_with(longstr)
        self.bot.send_msg.assert_called_once_with('wrapped', False)

    def test_send_msg_action(self):
        self.bot.send_action = Mock()
        self.bot.send_msg('/me tests')
        self.bot.send_action.assert_called_once_with('tests', False)

    def test_send_msg(self):
        self.bot.log = Mock()
        self.bot.send_msg('Hello World!')
        self.connection.privmsg.assert_called_once_with('#channel', 'Hello World!')
        self.bot.log.assert_called_once_with('#channel', '<nick> Hello World!')

    def test_send_priv_msg_list(self):
        send_priv_msg = self.bot.send_priv_msg
        self.bot.send_priv_msg = Mock()
        send_priv_msg('target', ['a', 'b'])
        self.bot.send_priv_msg.assert_called_with('target', 'b')
        self.bot.send_priv_msg.assert_any_call('target', 'a')

    @patch('minilodon.util.wrap_msg')
    def test_send_priv_msg_wrap(self, _wrap_msg):
        _wrap_msg.return_value = 'wrapped'
        send_priv_msg = self.bot.send_priv_msg
        self.bot.send_priv_msg = Mock()
        longstr = ' '.join(itertools.repeat("Hello World!", 20))
        send_priv_msg('target', longstr)
        _wrap_msg.assert_called_once_with(longstr)
        self.bot.send_priv_msg.assert_called_once_with('target', 'wrapped')

    def test_send_priv_msg_action(self):
        self.bot.send_priv_action = Mock()
        self.bot.send_priv_msg('target', '/me tests')
        self.bot.send_priv_action.assert_called_once_with('target', 'tests')

    def test_send_priv_msg(self):
        self.bot.send_priv_msg('target', 'Hello World!')
        self.connection.privmsg.assert_called_once_with('target', 'Hello World!')

    def test_send_action(self):
        self.bot.log = Mock()
        self.bot.send_action('tests')
        self.connection.action.assert_called_once_with('#channel', 'tests')
        self.bot.log.assert_called_once_with('#channel', 'nick tests')

    def test_send_priv_action(self):
        self.bot.send_priv_action('target', 'tests')
        self.connection.action.assert_called_once_with('target', 'tests')

    def test_decorator_message(self):
        self.bot.on_message = []
        decorator = self.bot.message()
        function = Mock()
        result = decorator(function)
        self.assertEqual(self.bot.on_message, [function])
        self.assertEqual(function, result)

    def test_decorator_command(self):
        self.bot.commands = {}
        decorator = self.bot.command('command')
        function = Mock()
        result = decorator(function)
        self.assertEqual(self.bot.commands, {'command': function})
        self.assertEqual(function, result)

    def test_decorator_control_command(self):
        self.bot.control_commands = {}
        decorator = self.bot.command('command', True)
        function = Mock()
        result = decorator(function)
        self.assertEqual(self.bot.control_commands, {'command': function})
        self.assertEqual(function, result)
