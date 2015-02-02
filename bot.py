from .minilodon import Minilodon
import json
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError

bot = Minilodon("config.json")
ydl = YoutubeDL({'quiet': True})
ydl.add_default_info_extractors()

actions = {}

@bot.command("update", True)
def update(nick, args):
    key = args[1]
    msg = " ".join(args[2:])
    actions[key] = msg
    with open("actions.json", "w") as f:
        json.dump(self.actions, f, indent=2, separators=(',', ': '),
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
        def lookup(nick, args):
            key = args[1]
            if key in actions[category]:
                bot.send_action(actions[category][key])
            else:
                bot.send_msg("Not found.")
        bot.commands[category] = lookup

if __name__ == "__main__":
    load_actions()
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise
