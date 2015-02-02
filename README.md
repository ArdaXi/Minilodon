# Minilodon

This is a simple chatbot that kicks anyone who hasn't spoken in over an hour
and has a bunch of other features. It is configured via a config file that
looks like this:

## config.json

    {
      "server": "irc.example.com",
      "port": 6667,
      "nick": "Minilodon",
      "mainchannel": "#Minilodon",
      "configchannel": "#Minilodon-admin"
    }

Anyone in the config channel is assumed to have admin privileges, please
ensure proper access control is in place.

Features:
- Kicks anyone after an hour of inactivity.
- Has a simple key-value lookup for any key prefaced with !
- Keys can be updated from the control channel with `!update <key> <value>`
- Links will be ran through YoutubeDL, if found will produce title, views.
- All messages will be logged immediately to a file `<channel>.log`

TODO:

- Configurable kick timer
- More avenues of lookup such as wiki or wordpress
- Look into changing kick timer at runtime
