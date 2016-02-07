from minilodon import Minilodon
import json
from urllib import parse
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError
import logging
import time
from threading import Timer

bot = Minilodon("config.json")
logger = logging.getLogger(__name__)
ydl = YoutubeDL({'quiet': False, 'logger': logger})
ydl.add_default_info_extractors()
spy_function = None
spy_timer = None

@bot.command("update", True)
def update(nick, args):
    if len(args) < 4:
        return "Usage: !update <category> <key> <msg>"
    category = args[1]
    key = args[2]
    msg = " ".join(args[3:])
    if len(msg) > 254:
        return "Entry too long, max 254 characters."
    try:
        msg.format(victim="victim", nick="nick")
    except KeyError as e:
        return "Failed to parse message on {}".format(str(e))
    actions = parse_actions("actions.json")
    if category not in actions:
        actions[category] = {}
    actions[category][key] = msg
    with open("actions.json", "w") as f:
        json.dump(actions, f, indent=2, separators=(',', ': '),
                  sort_keys=True)
    load_actions()
    return "{} added to {}.".format(key, category)

@bot.command("updateme", True)
def updateme(nick, args):
    if len(args) < 4:
        return "Usage: !updateme <category> <key> <msg>"
    args = args[:3] + ["/me"] + args[3:]
    return update(nick, args)

@bot.command("delete", True)
def delete(nick, args):
    if len(args) != 3:
        return "Usage: !delete <category> <key>"
    actions = parse_actions("actions.json")
    category = args[1]
    key = args[2]
    if category not in actions:
        return "Category {} not found!".format(category)
    if key not in actions[category]:
        return "Key {} not found in {}".format(key, category)
    del actions[category][key]
    with open("actions.json", "w") as f:
        json.dump(actions, f, indent=2, separators=(',', ': '),
                  sort_keys=True)
    load_actions()
    return "{} removed from {}.".format(key, category)

@bot.command("say", True)
def say(nick, args):
    if len(args) < 2:
        return "Usage: !say <msg>"
    bot.send_msg(" ".join(args[1:]))

@bot.command("join", True)
def join(nick, args):
    if len(args) != 2:
        return "Usage: !join <channel>"
    bot.join(args[1])

@bot.command("part", True)
def part(nick, args):
    if len(args) != 2:
        return "Usage: !part <channel>"
    bot.part(args[1])

def _idle_time_to_string(data):
    curtime = time.time()
    nick = data[0]
    idletime = data[1]
    delta = curtime - idletime
    hours, remainder = divmod(delta, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{} is {:d} uur, {:d} minuten en {:d} seconden idle.".format(nick,
      int(round(hours)), int(round(minutes)), int(round(seconds)))

@bot.command("idle", True)
def idle(nick, args):
    return map(_idle_time_to_string, bot.get_idle_times())

def stop_spy():
    global spy_function
    global spy_timer
    spy_function = None
    spy_timer = None
    return "Spy functie gestopt."

@bot.command("spy", True)
def spy(nick, args):
    global spy_function
    global spy_timer
    if spy_function:
        spy_timer.cancel()
        return stop_spy()
    def spier(nick, msg):
        line = "<{}> {}".format(nick, msg)
        bot.send_msg(line, True)
    spy_function = spier
    spy_timer = Timer(900.0, stop_spy)
    return "Room {} wordt 15 minuten bespioneerd.".format(bot.channel)

@bot.command("list")
def list_all(nick, args):
    if len(args) != 2:
        return "Usage: !list <category>"
    actions = parse_actions("actions.json")
    category = args[1]
    if category not in actions:
        return "{} niet gevonden.".format(category)
    msg = "Alle {}: {}".format(category, ", ".join(actions[category].keys()))
    bot.send_priv_msg(nick, msg)
    return "Zie prive voor een lijst van alle opties."

@bot.message()
def on_message(nick, msg):
    if spy_function:
        spy_function(nick, msg)
    if parse.urlsplit(msg).scheme.startswith("http"):
        yield video(msg)

def video(msg):
    try:
        result = ydl.extract_info(msg, download=False)
    except DownloadError:
        return
    if 'view_count' in result and result['view_count'] is not None:
        views = "| {:,} views".format(result['view_count'])
    else:
        views = ""
    return "[{0}] {1} {2}".format(result['extractor_key'], result['title'],
                                  views)

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
                    return actions[category][key].format(victim=victim, nick=nick)
                elif key not in bot.commands:
                    return "Didn't find {} in {}.".format(key, category)
            bot.commands[category] = lookup
        _(category)

if __name__ == "__main__":
    load_actions()
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise
