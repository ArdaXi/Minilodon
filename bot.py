from .minilodon import Minilodon
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError

bot = Minilodon("config.json")
ydl = YoutubeDL({'quiet': True})
ydl.add_default_info_extractors()

@bot.command("update", True)
def update(nick, args):
    key = args[1]
    msg = " ".join(args[2:])
    bot.actions[key] = msg
    with open("actions.json", "w") as f:
        json.dump(self.actions, f, indent=2, separators=(',', ': '),
                  sort_keys=True)

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

if __name__ == "__main__":
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise
