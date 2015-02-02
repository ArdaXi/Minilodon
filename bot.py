from . import minilodon

bot = Minilodon("config.json")

@bot.command("update", True)
def update(c, nick, args):
    key = args[1]
    msg = " ".join(args[2:])
    bot.actions[key] = msg
    with open("actions.json", "w") as f:
        json.dump(self.actions, f, indent=2, separators=(',', ': '),
                  sort_keys=True)

if __name__ == "__main__":
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise
