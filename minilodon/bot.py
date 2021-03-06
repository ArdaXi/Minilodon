from urllib import parse
from threading import Timer
import json
import logging
import time
import re
import random

from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError

from minilodon.minilodon import Minilodon

bot = Minilodon("config.json")
logger = logging.getLogger(__name__)
ydl = YoutubeDL({'quiet': False, 'logger': logger, 'noplaylist': True, 'extract_flat': 'in_playlist'})
ydl.add_default_info_extractors()
spy_function = None
spy_timer = None
roll_regex = re.compile(r"([0-9]*)d([0-9]+)")

@bot.command("update", True)
def update(nick, args):
    if len(args) < 4:
        yield "Usage: !update <category> <key> <msg>"
        return
    category = args[1].lower()
    key = args[2].lower()
    msg = " ".join(args[3:])
    if len(msg) > 254:
        yield "Warning: Entry too long, message will be wrapped."
    try:
        msg.format(victim="victim", nick="nick")
    except KeyError as error:
        yield "Failed to parse message on {}".format(str(error))
        return
    actions = parse_actions("actions.json")
    if category not in actions:
        actions[category] = {}
    actions[category][key] = msg
    with open("actions.json", "w") as actions_file:
        json.dump(actions, actions_file, indent=2, separators=(',', ': '),
                  sort_keys=True)
    load_actions()
    yield "{} added to {}.".format(key, category)

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
    category = args[1].lower()
    key = args[2].lower()
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
    return ("{} is {:d} uur, {:d} minuten en {:d} seconden idle."
            .format(nick, int(round(hours)), int(round(minutes)),
                    int(round(seconds))))

@bot.command("idle", True)
def idle(nick, args):
    if bot.alone:
        return "{} is alone in the room.".format(bot.alone)
    else:
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

@bot.command("roll")
def roll(nick, args):
    if len(args) != 2:
        return "Usage: !roll [x]dy (d20, 2d6)"
    amount = 1
    match = roll_regex.match(args[1])
    if match is None:
        return "Usage: !roll [x]dy (d20, 2d6)"
    if match.group(1) != '':
        amount = int(match.group(1))
    if amount > 10 or amount < 1:
        return "Nice try."
    die = int(match.group(2))
    if die > 100 or die < 1:
        return "That's not a real die."
    result = _die(die, amount)
    if len(result) > 150:
        result = result[:150]
    return "{0} rolled: {1}".format(nick, " ".join(result))

def _die(die, amount):
    if die == 6:
        return [chr(9855 + random.randint(1, die)) for x in range(amount)]
    else:
        return [str(random.randint(1, die)) for x in range(amount)]

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
    if result['extractor_key'] == "Generic" or 'title' not in result:
        return
    if 'duration' in result and result['duration'] is not None:
        duration = " [{0}]".format(seconds_to_time(result['duration']))
    else:
        duration = ""
    if 'view_count' in result and result['view_count'] is not None:
        views = " | {:,} views".format(result['view_count'])
    else:
        views = ""
    retval = "[{0}] {1}{2}{3}".format(result['extractor_key'], result['title'],
                                      duration, views)
    if '\r' in retval or '\n' in retval:
        return
    return retval

def seconds_to_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return "{0}:{1:02}:{2:02}".format(h, m, s)
    return "{0}:{1:02}".format(m, s)

def parse_actions(filename):
    with open(filename) as actions_file:
        return json.load(actions_file)

def load_actions():
    actions = parse_actions("actions.json")
    for category in actions:
        def _(category):
            def lookup(nick, args):
                if len(args) < 2:
                    return
                key = args[1].lower()
                if len(args) > 2:
                    victim = args[2]
                else:
                    victim = nick
                if key in actions[category]:
                    return actions[category][key].format(victim=victim,
                                                         nick=nick)
                elif key not in bot.commands:
                    return "Kon {} niet vinden in {}.".format(key, category)
            bot.commands[category] = lookup
        _(category)

def main():
    load_actions()
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise
