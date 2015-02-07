from minilodon import Minilodon
import json
import urlparse
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError
import logging
import time

bot = Minilodon("config.json")
ydl = YoutubeDL({'quiet': True})
ydl.add_default_info_extractors()
logger = logging.getLogger(__name__)

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
    if urlparse.urlsplit(msg).scheme.startswith("http"):
        video(msg)

def video(msg):
    try:
        result = ydl.extract_info(msg, download=False)
    except DownloadError:
        return
    if 'view_count' in result:
        views = "| {:,} views".format(result['view_count'])
    else:
        views = ""
    msg = "[{0}] {1} {2}".format(result['extractor_key'], result['title'],
                                 views)
    bot.send_msg(msg)

def parse_actions(filename):
    with open(filename):
        return json.load(f)

def load_actions():
    actions = parse_actions("actions.json")
    for category in actions:
        def _(category):
            def lookup(nick, args):
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
