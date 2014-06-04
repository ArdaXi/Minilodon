import irc.bot
import time
from threading import Thread, Event
from datetime import datetime
import json
import urlparse
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError

class Minilodon(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.logs = {}
        self.kickers = {}
        self.ydl = YoutubeDL({'quiet': True})
        self.ydl.add_default_info_extractors()
        
    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")
        
    def on_welcome(self, c, e):
        c.join(self.channel)
    
    def on_pubmsg(self, c, e):
        self.log(e)
        nick = e.source.nick
        if not nick in self.kickers:
            self.add_kicker(nick)
        self.kickers[nick].reset()
        if e.arguments[0].startswith("!"):
            self.do_command(e, e.arguments[0])
            return
        msg = " ".join(e.arguments)
        if urlparse.urlsplit(msg).scheme.startswith("http"):
            self.video(c, msg)
        
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
        if cmd == "!food":
            c.privmsg(channel, "Go make your own damn food!")
        else:
            c.notice(channel, "Not understood: " + cmd)
            
    def kick(self, nick, reason):
        self.connection.kick(self.channel, nick, reason)
        
    def log(self, event):
        curtime = datetime.now().strftime("%d-%m-%y %H:%M:%S")
        line = "{0} <{1}> {2}\n".format(curtime, event.source.nick, " ".join(event.arguments))
        self.logs[event.target].write(line)

    def video(self, c, url):
        try:
            result = self.ydl.extract_info(url, download=False)
        except DownloadError:
            return
        if 'view_count' in result:
            views = "- {:,} views".format(result['view_count'])
        else:
            views = ""
        msg = "[{0}] {1} {2}".format(result['extractor_key'], result['title'], views)
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
    with open("config.json") as f:
        config = json.load(f)
    server = config['server']
    port = config['port']
    channel = config['mainchannel']
    nickname = config['nick']

    bot = Minilodon(channel, nickname, server, port)
    
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise

if __name__ == "__main__":
    main()
