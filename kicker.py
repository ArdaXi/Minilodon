from threading import Thread, Event

class Kicker(Thread):
    def __init__(self, bot, channel, nick, idletime):
        Thread.__init__(self)
        self.bot = bot
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
                self.bot.connection.kick(self.channel, self.nick, "Idle too long!")
                self.bot.send_msg("Kicked {} due to inactivity.".format(self.nick), True)
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
