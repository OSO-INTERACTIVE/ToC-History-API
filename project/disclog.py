import time
from datetime import datetime
from typing import Literal

from discord_webhook import DiscordEmbed, DiscordWebhook

import config


def getColor(type: str | None) -> Literal[0xFF1D19] | Literal[0xFFEC44] | Literal[0x18A805] | Literal[0x5242FF]:
    if type == "error":
        return 0xFF1D19
    if type == "warn":
        return 0xFFEC44
    if type == "info":
        return 0x18A805

    return 0x5242FF


def buildEmbed(content: list[tuple[str, str]], type: str) -> DiscordEmbed | Literal[False]:
    try:
        embed = DiscordEmbed(title=type.upper(), color=getColor(type))
        embed.set_footer(text=f"{config.server_name}")
        embed.set_timestamp(timestamp=datetime.utcnow().timestamp())
        for pair in content:
            embed.add_embed_field(name=pair[0], value=pair[1], inline=False)
        return embed

    except Exception as e:
        print(e)
        return False


def postLog(message: Exception, type: str, stack: str) -> Literal[True] | None:
    if config.discord_hook_key != "":
        content = [("stack", stack), ("trace", str(message))]
        embed = buildEmbed(content, type)
        return postHook(embed)

    print(f"{datetime.utcnow()} - {stack} - {str(message)}")


def postGeneric(content: list[tuple[str, str]], type: str) -> Literal[True] | None:
    if config.discord_hook_key != "":
        embed = buildEmbed(content, type)
        return postHook(embed)

    print(f"{datetime.utcnow()} - {type} - {str(content)}")


def postHook(embed: DiscordEmbed) -> Literal[True] | None:
    x = True
    while x:
        try:
            webhook = DiscordWebhook(
                url=config.discord_hook_key,
                timeout=20,
                username="Train Logger",
                avatar_url="https://cdn.discordapp.com/attachments/834806287980167208/946415829405294682/logo80x80.png",
            )

            if embed.title == "ERROR":
                webhook.content = f"<@&{config.role_to_ping}>"

            webhook.add_embed(embed)

            response = webhook.execute()
            ans = response.content.decode("utf-8")

            if "You are being rate limited." in ans:
                time.sleep(30)
            else:
                return True
        except Exception as e:
            time.sleep(30)
            print(e)
