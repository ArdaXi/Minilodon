from minilodon import Minilodon
import json
from urllib import parse
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError
import logging
import time
from threading import Timer

bot = Minilodon("config.json")
ydl = YoutubeDL({'quiet': True})
ydl.add_default_info_extractors()
logger = logging.getLogger(__name__)
spy_function = None
spy_timer = None

@bot.command("update", True)
def update(nick, args):
    if len(args) < 4:
        bot.send_msg("Usage: !update <category> <key> <msg>", True)
        return
    actions = parse_actions("actions.json")
    category = args[1]
    key = args[2]
    msg = " ".join(args[3:])
    if category not in actions:
        actions[category] = {}
    actions[category][key] = msg
    with open("actions.json", "w") as f:
        json.dump(actions, f, indent=2, separators=(',', ': '),
                  sort_keys=True)
    load_actions()
    bot.send_msg("{} added to {}.".format(key, category), True)

@bot.command("idle", True)
def idle(nick, args):
    curtime = time.time()
    for result in bot.get_idle_times():
        nick = result[0]
        time = result[1]
        delta = curtime - time
        hours, remainder = divmod(delta, 3600)
        minutes, seconds = divmod(remainder, 60)
        msg = "{} is {} uur, {} minuten en {} seconden idle.".format(nick,
                                                                     hours,
                                                                     minutes,
                                                                     seconds)
        bot.send_msg(msg, True)

def stop_spy():
    spy_function = None
    spy_timer = None
    bot.send_msg("Spy functie gestopt.", True)

@bot.command("spy", True)
def spy(nick, args):
    if spy_function:
        spy_timer.cancel()
        stop_spy()
        return
    def spier(nick, msg):
        line = "{}: {}".format(nick, msg)
        bot.send_msg(line, True)
    spy_function = spier
    bot.send_msg("Room {} wordt 15 minuten bespioneerd.".format(bot.channel), True)
    spy_timer = Timer(900.0, stop_spy)

@bot.command("list")
def list_all(nick, args):
    if len(args) != 2:
        bot.send_msg("Usage: !list <category>")
    actions = parse_actions("actions.json")
    category = args[1]
    if category not in actions:
        bot.send_msg("{} niet gevonden.".format(category))
    msg = "Alle {}: {}".format(category, ", ".join(actions[category].items()))
    bot.send_priv_msg(nick, msg)
    bot.send_msg("Zie prive voor een lijst van alle opties.")

@bot.message()
def on_message(nick, msg):
    if spy_function:
        spy_function(nick, msg)
    if parse.urlsplit(msg).scheme.startswith("http"):
        video(msg)

def video(msg):
    try:
        result = ydl.extract_info(msg, download=False)
    except DownloadError:
        return
    if 'view_count' in result and result['view_count'] is not None:
        views = "| {:,} views".format(result['view_count'])
    else:
        views = ""
    msg = "[{0}] {1} {2}".format(result['extractor_key'], result['title'],
                                 views)
    bot.send_msg(msg)

def parse_actions(filename):
    with open(filename) as f:
        return json.load(f)

def load_actions():
    actions = parse_actions("actions.json")
    for category in actions:
        def _(category):
            def lookup(nick, args):
                if len(args) < 2:
                    return
                key = args[1]
                if len(args) > 2:
                    victim = args[2]
                else:
                    victim = nick
                if key in actions[category]:
                    bot.send_action(actions[category][key].format(victim=victim, nick=nick))
                else:
                    bot.send_msg("Didn't find {} in {}.".format(key, category))
            bot.commands[category] = lookup
        _(category)

if __name__ == "__main__":
    load_actions()
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise
