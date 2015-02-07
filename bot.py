from minilodon import Minilodon
import json
import urlparse
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError
import logging

bot = Minilodon("config.json")
ydl = YoutubeDL({'quiet': True})
ydl.add_default_info_extractors()
logger = logging.getLogger(__name__)

actions = {}

@bot.command("update", True)
def update(nick, args):
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

@bot.message()
def on_message(nick, msg):
    if urlparse.urlsplit(msg).scheme.startswith("http"):
        video(msg)

def video(msg):
    try:
        result = ydl.extract_info(url, download=False)
    except DownloadError:
        return
    if 'view_count' in result:
        views = "| {:,} views".format(result['view_count'])
    else:
        views = ""
    msg = "[{0}] {1} {2}".format(result['extractor_key'], result['title'],
                                 views)
    bot.send_msg(msg)

def load_actions():
    with open("actions.json") as f:
        actions = json.load(f)
    for category in actions:
        def _(category):
            def lookup(nick, args):
                key = args[1]
                if key in actions[category]:
                    bot.send_action(actions[category][key])
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
