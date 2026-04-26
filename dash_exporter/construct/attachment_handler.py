import discord
from abc import ABC, abstractmethod


class AttachmentHandler(ABC):
    @abstractmethod
    async def process_asset(self, attachment: discord.Attachment) -> discord.Attachment:
        raise NotImplementedError


class AttachmentToLocalFileHostHandler(AttachmentHandler):
    def __init__(self, base_path: str, url_base: str):
        self.base_path = base_path.rstrip("/")
        self.url_base  = url_base.rstrip("/")

    async def process_asset(self, attachment: discord.Attachment) -> discord.Attachment:
        import aiohttp, os
        dest = f"{self.base_path}/{attachment.filename}"
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    with open(dest, "wb") as f:
                        f.write(await resp.read())
        new_url = f"{self.url_base}/{attachment.filename}"
        attachment.url       = new_url
        attachment.proxy_url = new_url
        return attachment


class AttachmentToDiscordChannelHandler(AttachmentHandler):
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel

    async def process_asset(self, attachment: discord.Attachment) -> discord.Attachment:
        import aiohttp, io
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    file = discord.File(io.BytesIO(data), filename=attachment.filename)
                    msg  = await self.channel.send(file=file)
                    if msg.attachments:
                        new_url = msg.attachments[0].url
                        attachment.url       = new_url
                        attachment.proxy_url = new_url
        return attachment
