from . import minilodon

if __name__ == "__main__":
    bot = Minilodon("config.json")

    try:
        bot.start()
    except KeyboardInterrupt:
        bot.die()
        raise
