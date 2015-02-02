import irc.bot
import time
from threading import Thread, Event
from datetime import datetime
import json
import urlparse
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError

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
        self.load_actions()
        self.logs = {}
        self.kickers = {}
        self.ydl = YoutubeDL({'quiet': True})
        self.ydl.add_default_info_extractors()

    def load_actions(self):
        with open("actions.json") as f:
            self.actions = json.load(f)
        
    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")
        
    def on_welcome(self, c, e):
        c.join(self.channel)
    
    def on_pubmsg(self, c, e):
        self.log(e)
        if c == self.channel:
            self.on_pubmsg_main(e)
        elif c == self.control_channel:
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
        if urlparse.urlsplit(msg).scheme.startswith("http"):
            self.video(c, msg)

    def on_pubmsg_control(self, e):
       if e.arguments[0].startswith("!"):
           self.do_control_command(e, e.arguments[0][1:])
        
    def on_join(self, c, e):
        if e.source.nick == self.connection.get_nickname():
            c.privmsg(e.target, "Hi!")
            self.logs[e.target] = open(e.target + ".log", 'a')
        else:
            nick = e.source.nick
            self.add_kicker(nick)

    def add_kicker(self, nick):
        kicker = Kicker(self.connection, self.channel, nick)
        kicker.start()
        self.kickers[nick] = kicker
        
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
        actions = self.actions
        args = cmd.split(" ")
        if args[0] in actions and args[1] in actions[args[0]]:
            c.action(channel, actions[args[0]][args[1]])
        else:
            c.notice(channel, "Not found: " + cmd)

    def do_control_command(self, e, cmd):
        args = cmd.split(" ")
        if args[0] == "update":
            self.actions[args[1]] = " ".join(args[2:])
            with open("actions.json", "w") as f:
                json.dump(self.actions, f, indent=2, separators=(',', ': '),
                          sort_keys=True)
            
    def kick(self, nick, reason):
        self.connection.kick(self.channel, nick, reason)
        
    def log(self, event):
        curtime = datetime.now().strftime("%d-%m-%y %H:%M:%S")
        line = "{0} <{1}> {2}\n".format(curtime, event.source.nick,
                                        " ".join(event.arguments))
        self.logs[event.target].write(line)

    def video(self, c, url):
        try:
            result = self.ydl.extract_info(url, download=False)
        except DownloadError:
            return
        if 'view_count' in result:
            views = "| {:,} views".format(result['view_count'])
        else:
            views = ""
        msg = "[{0}] {1} {2}".format(result['extractor_key'], result['title'],
                                     views)
        c.privmsg(self.channel, msg)

class Kicker(Thread):
    def __init__(self, connection, channel, nick):
        Thread.__init__(self)
        self.connection = connection
        self.channel = channel
        self.nick = nick
        self.resetter = Event()
        self.canceled = False
        self.daemon = True
        
    def run(self):
        while not self.canceled:
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
    
def main():
    bot = Minilodon("config.json")
    
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise

if __name__ == "__main__":
    main()
