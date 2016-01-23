# Minilodon

This is a simple chatbot that kicks anyone who hasn't spoken in over an hour
and has a bunch of other features. It is configured via a config file that
looks like this:

## config.json

    {
      "server": "irc.example.com",
      "port": 6667,
      "nick": "Minilodon",
      "password": "rycbar123",
      "mainchannel": "#Minilodon",
      "controlchannel": "#Minilodon-admin"
    }

Anyone in the config channel is assumed to have admin privileges, please
ensure proper access control is in place.

## Running:

Currently, the bot can be started by simply invoking `bot.py`.

## Features:

- Kicks anyone after an hour of inactivity.
- Has a simple key-value lookup for any key prefaced with !
- Keys can be updated from the control channel with `!update <category> <key> <value>`
- Links will be ran through YoutubeDL, if found will produce title, views.
- All messages will be logged immediately to a file `<channel>.log`

## Extensibility:

It's simple to add more commands for the bot to handle more commands. To do
so, define a new function with the `@bot.command(command, control)` decorator.
`command` is a string set to what command to handle. `control` is a boolean
defaulting to false, if set to true the command will run in the control
channel rather than the main one.

Functions can use the `bot.send_msg(message, control)` and
`bot.send_action(message)` functions to send output back to the channels.

## TODO:

- Configurable kick timer
- More avenues of lookup such as wiki or wordpress
- Look into changing kick timer at runtime
- Add delete command
