# Matrix Bot

This is a Matrix bot forked from
[anoadragon453/matrix-reminder-bot](https://github.com/anoadragon453/matrix-reminder-bot)

Currently it is a Magic: The Gathering card image bot.

```
!mtg card Scute Mob
```

Uploads the picture of the card named `Scute Mob`. Card images are cached in the
`/data` volume of the container.

## Setup

Create a Matrix user for the bot, on any homeserver. Copy `sample.config.yaml`
to `config.yaml` (config.yaml is excluded from git in `.gitignore`). Change
settings in your `config.yaml`, including the bot user credentials.

## Build container

```bash
podman build -t enigmacurry/matrix-bot -f docker/Dockerfile . 
```

## Run container

```bash
podman run --rm -it -v matrix-bot-data:/data -v ./config.yaml:/data/config.yaml enigmacurry/matrix-bot
```

Invite the bot to whatever channel you want.
