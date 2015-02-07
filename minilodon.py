import irc.bot
import time
from threading import Thread, Event
from datetime import datetime
import json
import logging

class Minilodon(irc.bot.SingleServerIRCBot):
    def __init__(self, config):
        with open(config) as f:
            config = json.load(f)
        server = config['server']
        port = config['port']
        nickname = config['nick']
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname,
                                            nickname)
        self.channel = config['mainchannel']
        self.control_channel = config['controlchannel']
        self.logs = {}
        self.kickers = {}
        self.commands = {}
        self.control_commands = {}
        self.logger = logging.getLogger(__name__)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")
        
    def on_welcome(self, c, e):
        c.join(self.channel)
        c.join(self.control_channel)
    
    def on_pubmsg(self, c, e):
        self.log(e)
        if e.target == self.channel:
            self.on_pubmsg_main(e)
        elif e.target == self.control_channel:
            self.on_pubmsg_control(e)

    def on_pubmsg_main(self, e):
        nick = e.source.nick
        if not nick in self.kickers:
            self.add_kicker(nick)
        self.kickers[nick].reset()
        if e.arguments[0].startswith("!"):
            self.do_command(e, e.arguments[0][1:])
            return
        msg = " ".join(e.arguments)
        if self.on_message:
            self.on_message(nick, msg)

    def on_pubmsg_control(self, e):
       if e.arguments[0].startswith("!"):
           self.do_control_command(e, e.arguments[0][1:])
           self.do_command(e, e.arguments[0][1:])
        
    def on_join(self, c, e):
        if e.source.nick == self.connection.get_nickname():
            c.privmsg(e.target, "Hi!")
            self.logs[e.target] = open(e.target + ".log", 'a')
        else:
            if e.target != self.channel:
                return
            nick = e.source.nick
            self.add_kicker(nick)

    def add_kicker(self, nick):
        kicker = Kicker(self.connection, self.channel, nick)
        kicker.start()
        self.kickers[nick] = kicker

    def get_idle_times(self):
        for nick in self.kickers:
            yield (nick, self.kickers[nick].time)
        
    def on_nick(self, c, e):
        self.kickers[e.target] = kickers[e.source]
        self.kickers[e.target].changenick(e.target)
        del self.kickers[e.source]
        
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
        
    def log(self, event):
        curtime = datetime.now().strftime("%d-%m-%y %H:%M:%S")
        line = "{0} <{1}> {2}\n".format(curtime, event.source.nick,
                                        " ".join(event.arguments))
        self.logs[event.target].write(line)

    def send_msg(self, msg, control=False):
        channel = self.control_channel if control else self.channel
        self.connection.privmsg(channel, msg)

    def send_priv_msg(self, target, msg):
        if target.startswith("#"):
            raise Exception("That's not a private message!")
        self.connection.privmsg(target, msg)

    def send_action(self, action):
        self.connection.action(self.channel, action)

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
    def __init__(self, connection, channel, nick):
        Thread.__init__(self)
        self.connection = connection
        self.channel = channel
        self.nick = nick
        self.resetter = Event()
        self.canceled = False
        self.daemon = True
        self.time = time.time()
        
    def run(self):
        while not self.canceled:
            self.time = time.time()
            self.resetter.wait(3600.0)
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
