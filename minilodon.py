import irc.bot
import time
from threading import Thread, Event
from datetime import datetime
import json
import logging
import os

class Minilodon(irc.bot.SingleServerIRCBot):
    def __init__(self, config):
        with open(config) as f:
            config = json.load(f)
        server = config['server']
        port = config['port']
        nickname = config['nick']
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname,
                                            nickname)
        self.channel = config['mainchannel'].lower()
        self.control_channel = config['controlchannel'].lower()
        self.password = config['password'] if 'password' in config else None
        self.idletime = config['idletime'] if 'idletime' in config else 3600.0
        self.logs = {}
        self.kickers = {}
        self.commands = {}
        self.control_commands = {}
        self.logger = logging.getLogger(__name__)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        if self.password:
            self.send_priv_msg('NickServ', 'IDENTIFY ' + self.password)
        c.join(self.channel)
        c.join(self.control_channel)

    def on_pubmsg(self, c, e):
        line = "<{0}> {1}".format(e.source.nick, " ".join(e.arguments))
        self.log(e.target, line)
        channel = e.target.lower()
        if channel == self.channel:
            self.on_pubmsg_main(e)
        elif channel == self.control_channel:
            self.on_pubmsg_control(e)

    def on_pubmsg_main(self, e):
        nick = e.source.nick
        if not nick in self.kickers:
            self.add_kicker(nick)
        self.kickers[nick].reset()
        if e.arguments[0].startswith("!"):
            self.send_msg(self.do_command(e, e.arguments[0][1:]))
        msg = " ".join(e.arguments)
        if self.on_message:
            self.send_msg(self.on_message(nick, msg))

    def on_pubmsg_control(self, e):
       if e.arguments[0].startswith("!"):
           self.send_msg(self.do_control_command(e, e.arguments[0][1:]), True)

    def on_action(self, c, e):
        self.log(e.target, "{} {}".format(e.source.nick, " ".join(e.arguments)))
        if e.target.lower() == self.channel:
            e.arguments = ["/me"] + e.arguments
            self.on_pubmsg_main(e)

    def on_join(self, c, e):
        if e.source.nick == self.connection.get_nickname():
            c.privmsg(e.target, "Hi!")
            self.logs[e.target] = self.open_log_file(e.target)
        else:
            host = e.source.split('!')[1]
            nick = e.source.nick
            self.log(e.target, "{} [{}] joined {}".format(nick, host, e.target))
            if e.target != self.channel:
                return
            self.add_kicker(nick)

    def on_part(self, c, e):
        self.remove_kicker(e.source.nick)
        self.log(e.target, "{} left {}".format(e.source.nick, e.target))

    def on_kick(self, c, e):
        channel = e.target
        kicker = e.source.nick
        kickee = e.arguments[0]
        reason = " ".join(e.arguments[1:])
        self.remove_kicker(kickee)
        self.log(channel, "{} was kicked from {} by {} ({})".format(kickee, channel,
                                                                    kicker, reason))

    def open_log_file(self, channel):
        if not os.path.exists(channel):
            os.mkdir(channel)
        curdate = datetime.now()
        datestr = curdate.strftime("%y-%m-%d")
        self.day = curdate.day
        filename = "{}/{}-{}.log".format(channel, datestr, channel)
        return open(filename, 'at', 1)

    def add_kicker(self, nick):
        kicker = Kicker(self.connection, self.channel, nick, self.idletime)
        kicker.start()
        self.kickers[nick] = kicker

    def remove_kicker(self, nick):
        if nick in self.kickers:
            self.kickers[nick].cancel()
            del self.kickers[nick]

    def get_idle_times(self):
        for nick in self.kickers:
            yield (nick, self.kickers[nick].time)

    def on_nick(self, c, e):
        if e.source.nick in self.kickers:
            self.kickers[e.target] = self.kickers[e.source.nick]
            self.kickers[e.target].changenick(e.target)
            del self.kickers[e.source.nick]

    #def on_privmsg(self, c, e):
    #    self.do_command(e, e.arguments()[0])

    def do_command(self, e, cmd):
        channel = e.target
        nick = e.source.nick
        c = self.connection
        args = cmd.split(" ")
        if args[0] in self.commands:
            return self.commands[args[0]](nick, args)

    def do_control_command(self, e, cmd):
        c = self.connection
        args = cmd.split(" ")
        nick = e.source.nick
        if args[0] in self.control_commands:
            return self.control_commands[args[0]](nick, args)

    def kick(self, nick, reason):
        self.connection.kick(self.channel, nick, reason)

    def log(self, channel, msg):
        curtime = datetime.now()
        if not curtime.day == self.day:
            self.reopen_logs()
        timestr = curtime.strftime("%d-%m-%y %H:%M:%S")
        line = "{0} {1}\n".format(timestr, msg)
        self.logs[channel].write(line)

    def reopen_logs(self):
        for channel in self.logs:
            oldfile = self.logs[channel]
            self.logs[channel] = self.open_log_file(channel)
            oldfile.close()

    def send_msg(self, msg, control=False):
        if msg is None:
            return
        if not isinstance(msg, str):
            for line in msg:
                self.send_msg(line, control)
            return
        channel = self.control_channel if control else self.channel
        self.connection.privmsg(channel, msg)
        mynick = self.connection.get_nickname()
        line = "<{0}> {1}".format(mynick, msg)
        self.log(channel, line)

    def send_priv_msg(self, target, msg):
        if target.startswith("#"):
            raise Exception("That's not a private message!")
        self.connection.privmsg(target, msg)

    def send_action(self, action, control=False):
        if action is None:
            return
        self.connection.action(self.channel, action)
        line = "{} {}".format(self.connection.get_nickname(), action)
        self.log(self.channel, line)

    def message(self):
        def decorator(f):
            self.on_message = f
            return f
        return decorator

    def command(self, cmd, control=False):
        def decorator(f):
            if control:
                self.control_commands[cmd] = f
            else:
                self.commands[cmd] = f
            return f
        return decorator

class Kicker(Thread):
    def __init__(self, connection, channel, nick, idletime):
        Thread.__init__(self)
        self.connection = connection
        self.channel = channel
        self.nick = nick
        self.idletime = idletime
        self.resetter = Event()
        self.canceled = False
        self.daemon = True
        self.time = time.time()

    def run(self):
        while not self.canceled:
            self.time = time.time()
            self.resetter.wait(self.idletime)
            if not self.resetter.isSet() and not self.canceled:
                self.connection.kick(self.channel, self.nick, "Idle too long!")
                self.canceled = True
            else:
                self.resetter.clear()

    def reset(self):
        self.resetter.set()

    def cancel(self):
        self.canceled = True
        self.resetter.set()

    def changenick(self, nick):
        self.nick = nick
        self.reset()
