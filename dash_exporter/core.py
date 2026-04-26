import io
import datetime
import discord
from discord.ext import commands

from .construct.transcript  import Transcript
from .construct.attachment_handler import AttachmentHandler


async def export(
    channel: discord.abc.Messageable,
    limit: int | None = None,
    tz_info: str = "UTC",
    guild: discord.Guild | None = None,
    military_time: bool = True,
    fancy_times: bool = True,
    before: datetime.datetime | None = None,
    after: datetime.datetime | None = None,
    bot: commands.Bot | discord.Client | None = None,
    attachment_handler: AttachmentHandler | None = None,
    raise_exceptions: bool = False,
) -> str | None:
    try:
        messages = [
            m async for m in channel.history(
                limit=limit,
                before=before,
                after=after,
                oldest_first=True,
            )
        ]
        return await _build(channel, messages, tz_info, guild, military_time, fancy_times, bot, attachment_handler)
    except Exception as e:
        if raise_exceptions:
            raise
        print(f"[dash_exporter] export error: {e}")
        return None


async def raw_export(
    channel: discord.abc.Messageable,
    messages: list[discord.Message],
    tz_info: str = "UTC",
    military_time: bool = True,
    fancy_times: bool = True,
    bot: commands.Bot | discord.Client | None = None,
    attachment_handler: AttachmentHandler | None = None,
    raise_exceptions: bool = False,
) -> str | None:
    try:
        return await _build(channel, messages, tz_info, None, military_time, fancy_times, bot, attachment_handler)
    except Exception as e:
        if raise_exceptions:
            raise
        print(f"[dash_exporter] raw_export error: {e}")
        return None


async def quick_export(
    channel: discord.abc.Messageable,
    bot: commands.Bot | discord.Client | None = None,
    raise_exceptions: bool = False,
) -> discord.Message | None:
    transcript = await export(channel, bot=bot, raise_exceptions=raise_exceptions)
    if transcript is None:
        return None

    name = getattr(channel, "name", "transcript")
    file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{name}.html")
    return await channel.send(file=file)


async def _build(
    channel,
    messages: list[discord.Message],
    tz_info: str,
    guild,
    military_time: bool,
    fancy_times: bool,
    bot,
    attachment_handler,
) -> str:
    t = Transcript(
        channel=channel,
        messages=messages,
        tz_info=tz_info,
        guild=guild or getattr(channel, "guild", None),
        military_time=military_time,
        fancy_times=fancy_times,
        bot=bot,
        attachment_handler=attachment_handler,
    )
    return await t.build()
