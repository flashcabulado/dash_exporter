from __future__ import annotations
import html as html_mod
import discord

from ..utils.markdown import parse
from ..utils.time import fmt_time, fmt_date, fmt_full, same_day
from .attachment_handler import AttachmentHandler


IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "bmp", "svg"}
VIDEO_EXT = {"mp4", "webm", "mov", "avi"}
AUDIO_EXT = {"mp3", "ogg", "wav", "flac"}


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _avatar(user) -> str:
    try:
        return str(user.display_avatar.with_size(64).url)
    except Exception:
        return "https://cdn.discordapp.com/embed/avatars/0.png"


class Transcript:
    def __init__(
        self,
        channel,
        messages: list[discord.Message],
        tz_info: str,
        guild,
        military_time: bool,
        fancy_times: bool,
        bot,
        attachment_handler: AttachmentHandler | None,
    ):
        self.channel          = channel
        self.messages         = messages
        self.tz_info          = tz_info
        self.guild            = guild
        self.military_time    = military_time
        self.fancy_times      = fancy_times
        self.bot              = bot
        self.attachment_handler = attachment_handler

    async def build(self) -> str:
        body = await self._render_messages()
        return self._wrap(body)

    async def _render_messages(self) -> str:
        parts: list[str] = []
        prev_msg: discord.Message | None = None
        prev_author_id: int | None = None

        for msg in self.messages:
            if self.fancy_times and (prev_msg is None or not same_day(prev_msg.created_at, msg.created_at, self.tz_info)):
                parts.append(self._date_divider(msg.created_at))

            grouped = (
                prev_msg is not None
                and prev_author_id == msg.author.id
                and not msg.type != discord.MessageType.default
                and (msg.created_at - prev_msg.created_at).seconds < 420
                and same_day(prev_msg.created_at, msg.created_at, self.tz_info)
            )

            parts.append(await self._render_message(msg, grouped))
            prev_msg      = msg
            prev_author_id = msg.author.id

        return "\n".join(parts)

    async def _render_message(self, msg: discord.Message, grouped: bool) -> str:
        ts_full = fmt_full(msg.created_at, self.military_time, self.tz_info)
        ts_time = fmt_time(msg.created_at, self.military_time, self.tz_info)

        if grouped:
            header = f'<span class="msg-ts-inline" title="{ts_full}">{ts_time}</span>'
            top    = f'<div class="msg-row grouped"><div class="ts-gutter">{header}</div><div class="msg-body">'
        else:
            avatar   = _avatar(msg.author)
            name_cls = "author-bot" if msg.author.bot else "author-user"
            badge    = '<span class="badge-bot">APP</span>' if msg.author.bot else ""
            name     = html_mod.escape(msg.author.display_name)
            top      = (
                f'<div class="msg-row">'
                f'<img class="avatar" src="{avatar}" alt="">'
                f'<div class="msg-body">'
                f'<div class="msg-header">'
                f'<span class="{name_cls}">{name}</span>{badge}'
                f'<span class="msg-ts" title="{ts_full}">{ts_full}</span>'
                f'</div>'
            )

        content  = self._render_content(msg)
        refs     = self._render_reference(msg)
        attaches = await self._render_attachments(msg)
        embeds   = self._render_embeds(msg)
        reactions= self._render_reactions(msg)
        comps    = self._render_components(msg)

        return f'{top}{refs}{content}{attaches}{embeds}{comps}{reactions}</div></div>'

    def _render_content(self, msg: discord.Message) -> str:
        if msg.type == discord.MessageType.pins_add:
            return f'<div class="msg-system">📌 {html_mod.escape(msg.author.display_name)} fixou uma mensagem.</div>'
        if msg.type == discord.MessageType.new_member:
            return f'<div class="msg-system">👋 {html_mod.escape(msg.author.display_name)} entrou no servidor.</div>'

        if not msg.content:
            return ""
        return f'<div class="msg-content">{parse(msg.content)}</div>'

    def _render_reference(self, msg: discord.Message) -> str:
        ref = msg.reference
        if not ref or not ref.resolved:
            return ""
        resolved = ref.resolved
        if isinstance(resolved, discord.Message):
            author  = html_mod.escape(resolved.author.display_name)
            preview = html_mod.escape((resolved.content or "[anexo]")[:80])
            avatar  = _avatar(resolved.author)
            return (
                f'<div class="reply-bar">'
                f'<img class="reply-avatar" src="{avatar}" alt="">'
                f'<span class="reply-author">{author}</span>'
                f'<span class="reply-preview">{preview}</span>'
                f'</div>'
            )
        return ""

    async def _render_attachments(self, msg: discord.Message) -> str:
        if not msg.attachments:
            return ""
        parts = []
        for att in msg.attachments:
            if self.attachment_handler:
                try:
                    att = await self.attachment_handler.process_asset(att)
                except Exception:
                    pass
            ext = _ext(att.filename)
            url = att.url
            name = html_mod.escape(att.filename)
            if ext in IMAGE_EXT:
                parts.append(f'<a href="{url}" target="_blank"><img class="att-img" src="{url}" alt="{name}" loading="lazy"></a>')
            elif ext in VIDEO_EXT:
                parts.append(f'<video class="att-video" controls src="{url}"></video>')
            elif ext in AUDIO_EXT:
                parts.append(f'<audio class="att-audio" controls src="{url}"></audio>')
            else:
                size = f"{att.size // 1024} KB" if att.size else ""
                parts.append(
                    f'<div class="att-file">'
                    f'<span class="att-icon">📎</span>'
                    f'<div class="att-info"><a href="{url}" target="_blank" class="att-name">{name}</a>'
                    f'<span class="att-size">{size}</span></div>'
                    f'</div>'
                )
        return f'<div class="attachments">{"".join(parts)}</div>'

    def _render_embeds(self, msg: discord.Message) -> str:
        if not msg.embeds:
            return ""
        parts = []
        for emb in msg.embeds:
            color = f"#{emb.colour.value:06x}" if emb.colour and emb.colour.value else "#4f545c"
            title = f'<div class="emb-title">{parse(emb.title)}</div>' if emb.title else ""
            desc  = f'<div class="emb-desc">{parse(emb.description)}</div>' if emb.description else ""
            thumb = (
                f'<img class="emb-thumb" src="{emb.thumbnail.url}" alt="" loading="lazy">'
                if emb.thumbnail else ""
            )
            image = (
                f'<img class="emb-img" src="{emb.image.url}" alt="" loading="lazy">'
                if emb.image else ""
            )
            auth  = ""
            if emb.author:
                a_icon = f'<img class="emb-auth-icon" src="{emb.author.icon_url}" alt="">' if emb.author.icon_url else ""
                auth   = f'<div class="emb-author">{a_icon}<span>{html_mod.escape(emb.author.name or "")}</span></div>'
            fields = ""
            if emb.fields:
                field_parts = []
                for field in emb.fields:
                    inline_cls = "field-inline" if field.inline else "field-block"
                    field_parts.append(
                        f'<div class="emb-field {inline_cls}">'
                        f'<div class="field-name">{parse(field.name)}</div>'
                        f'<div class="field-value">{parse(field.value)}</div>'
                        f'</div>'
                    )
                fields = f'<div class="emb-fields">{"".join(field_parts)}</div>'
            footer = ""
            if emb.footer:
                f_icon = f'<img class="emb-foot-icon" src="{emb.footer.icon_url}" alt="">' if emb.footer.icon_url else ""
                footer = f'<div class="emb-footer">{f_icon}<span>{html_mod.escape(emb.footer.text or "")}</span></div>'

            parts.append(
                f'<div class="embed" style="border-left-color:{color}">'
                f'{auth}{title}{desc}{thumb}{fields}{image}{footer}'
                f'</div>'
            )
        return f'<div class="embeds">{"".join(parts)}</div>'

    def _render_reactions(self, msg: discord.Message) -> str:
        if not msg.reactions:
            return ""
        parts = []
        for r in msg.reactions:
            emoji = html_mod.escape(str(r.emoji))
            parts.append(f'<span class="reaction"><span class="r-emoji">{emoji}</span><span class="r-count">{r.count}</span></span>')
        return f'<div class="reactions">{"".join(parts)}</div>'

    def _render_components(self, msg: discord.Message) -> str:
        if not msg.components:
            return ""
        parts = []
        for row in msg.components:
            if isinstance(row, discord.ActionRow):
                row_parts = []
                for comp in row.children:
                    row_parts.append(self._render_component(comp))
                parts.append(f'<div class="comp-row">{"".join(row_parts)}</div>')
            else:
                parts.append(self._render_component(row))
        return f'<div class="components">{"".join(parts)}</div>'

    def _render_component(self, comp) -> str:
        if isinstance(comp, discord.Button):
            label = html_mod.escape(comp.label or "")
            emoji = html_mod.escape(str(comp.emoji)) if comp.emoji else ""
            style_map = {
                discord.ButtonStyle.primary:   "btn-primary",
                discord.ButtonStyle.secondary: "btn-secondary",
                discord.ButtonStyle.success:   "btn-success",
                discord.ButtonStyle.danger:    "btn-danger",
                discord.ButtonStyle.link:      "btn-link",
            }
            cls = style_map.get(comp.style, "btn-secondary")
            disabled = ' disabled' if comp.disabled else ''
            href = f' href="{comp.url}"' if comp.url else ""
            tag  = "a" if comp.url else "button"
            return f'<{tag} class="comp-btn {cls}"{href}{disabled}>{emoji}{label}</{tag}>'

        if isinstance(comp, (discord.Select, discord.UserSelect, discord.RoleSelect, discord.MentionableSelect, discord.ChannelSelect)):
            ph = html_mod.escape(comp.placeholder or "Selecione uma opção")
            opts = ""
            if hasattr(comp, "options"):
                for o in comp.options:
                    em = html_mod.escape(str(o.emoji)) + " " if o.emoji else ""
                    opts += f'<option>{em}{html_mod.escape(o.label)}</option>'
            return f'<select class="comp-select" disabled><option>{ph}</option>{opts}</select>'

        if isinstance(comp, discord.TextInput):
            val = html_mod.escape(comp.value or comp.placeholder or "")
            return f'<div class="comp-input"><label>{html_mod.escape(comp.label)}</label><div class="input-val">{val}</div></div>'

        return f'<div class="comp-unknown">[componente]</div>'

    def _date_divider(self, dt) -> str:
        label = fmt_date(dt, self.tz_info)
        return f'<div class="date-divider"><span>{label}</span></div>'

    def _channel_type_icon(self) -> str:
        ct = getattr(self.channel, "type", None)
        icons = {
            discord.ChannelType.text:           "#",
            discord.ChannelType.voice:          "🔊",
            discord.ChannelType.news:           "📢",
            discord.ChannelType.forum:          "💬",
            discord.ChannelType.private_thread: "🔒",
            discord.ChannelType.public_thread:  "💬",
            discord.ChannelType.news_thread:    "📢",
        }
        return icons.get(ct, "#")

    def _wrap(self, body: str) -> str:
        guild_name   = html_mod.escape(self.guild.name if self.guild else "Servidor")
        guild_icon   = str(self.guild.icon.url) if self.guild and self.guild.icon else ""
        ch_name      = html_mod.escape(getattr(self.channel, "name", "canal"))
        ch_icon      = self._channel_type_icon()
        total        = len(self.messages)

        guild_icon_tag = (
            f'<img class="guild-icon" src="{guild_icon}" alt="">'
            if guild_icon else
            f'<div class="guild-icon-placeholder">{guild_name[0]}</div>'
        )

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Transcrição — {ch_name}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:        #111214;
      --bg2:       #1e1f22;
      --bg3:       #2b2d31;
      --bg-hover:  #1a1b1e;
      --text:      #dbdee1;
      --text-muted:#949ba4;
      --text-dim:  #4e5058;
      --accent:    #12F800;
      --link:      #00a8fc;
      --mention:   #5865f2;
      --sidebar-w: 240px;
    }}

    body {{ background: var(--bg); font-family: 'gg sans','Noto Sans','Helvetica Neue',Arial,sans-serif; color: var(--text); min-height: 100vh; line-height: 1.375; }}

    /* ── SIDEBAR ── */
    .sidebar {{
      position: fixed; top: 0; left: 0;
      width: var(--sidebar-w); height: 100vh;
      background: var(--bg2);
      border-right: 1px solid var(--bg3);
      display: flex; flex-direction: column;
      overflow-y: auto; z-index: 10;
    }}
    .guild-header {{
      display: flex; align-items: center; gap: 10px;
      padding: 16px; border-bottom: 1px solid var(--bg3);
    }}
    .guild-icon {{ width: 40px; height: 40px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }}
    .guild-icon-placeholder {{
      width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
      background: var(--accent); color: #000;
      display: flex; align-items: center; justify-content: center;
      font-weight: 700; font-size: 16px;
    }}
    .guild-name {{ font-size: 14px; font-weight: 700; color: #f2f3f5; word-break: break-word; }}
    .sidebar-ch {{
      padding: 8px 16px; display: flex; align-items: center; gap: 6px;
      font-size: 13px; font-weight: 600; color: var(--text-muted);
      border-radius: 4px; margin: 4px 8px;
      background: var(--bg-hover);
    }}
    .sidebar-ch .ch-icon {{ color: var(--text-dim); font-size: 15px; }}
    .sidebar-stats {{
      padding: 12px 16px; font-size: 11px; color: var(--text-dim);
      text-transform: uppercase; letter-spacing: .5px;
      border-top: 1px solid var(--bg3); margin-top: auto;
    }}
    .sidebar-stats span {{ color: var(--accent); font-weight: 700; }}

    /* ── MAIN ── */
    .main {{ margin-left: var(--sidebar-w); display: flex; flex-direction: column; min-height: 100vh; }}
    .channel-bar {{
      position: sticky; top: 0; z-index: 5;
      background: var(--bg); border-bottom: 1px solid var(--bg3);
      display: flex; align-items: center; gap: 10px;
      padding: 12px 24px; backdrop-filter: blur(4px);
    }}
    .channel-bar .ch-icon {{ font-size: 20px; color: var(--text-dim); }}
    .channel-bar .ch-name {{ font-size: 16px; font-weight: 700; color: #f2f3f5; }}
    .channel-bar .ch-count {{ font-size: 12px; color: var(--text-dim); margin-left: auto; }}

    .messages {{ padding: 16px 24px; flex: 1; }}

    /* ── DATE DIVIDER ── */
    .date-divider {{
      display: flex; align-items: center; gap: 12px;
      margin: 20px 0 8px; color: var(--text-dim); font-size: 12px; font-weight: 600;
    }}
    .date-divider::before, .date-divider::after {{
      content: ''; flex: 1; height: 1px; background: var(--bg3);
    }}

    /* ── MESSAGES ── */
    .msg-row {{
      display: flex; gap: 14px; padding: 2px 0;
      border-radius: 4px; transition: background .1s;
      padding: 2px 4px;
    }}
    .msg-row:hover {{ background: var(--bg-hover); }}
    .msg-row.grouped {{ align-items: flex-start; }}
    .ts-gutter {{ width: 40px; flex-shrink: 0; text-align: right; padding-top: 3px; }}
    .msg-ts-inline {{ font-size: 10px; color: var(--text-dim); display: none; }}
    .msg-row.grouped:hover .msg-ts-inline {{ display: inline; }}
    .avatar {{ width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; background: var(--bg3); object-fit: cover; margin-top: 2px; }}
    .msg-body {{ flex: 1; min-width: 0; }}
    .msg-header {{ display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; margin-bottom: 2px; }}
    .author-user {{ font-size: 15px; font-weight: 600; color: #f2f3f5; }}
    .author-bot  {{ font-size: 15px; font-weight: 600; color: var(--accent); }}
    .badge-bot {{
      background: #5865f2; color: #fff;
      font-size: 9px; font-weight: 700;
      padding: 1px 5px; border-radius: 3px;
      text-transform: uppercase; letter-spacing: .3px; vertical-align: middle;
    }}
    .msg-ts {{ font-size: 11px; color: var(--text-dim); }}
    .msg-content {{ font-size: 14px; line-height: 1.55; word-break: break-word; white-space: pre-wrap; }}
    .msg-system {{ font-size: 13px; color: var(--text-dim); font-style: italic; padding: 4px 0; }}

    /* ── MARKDOWN ── */
    code {{ background: #111; border-radius: 3px; padding: 2px 5px; font-family: monospace; font-size: 85%; color: #e06c75; }}
    pre {{ background: #0d0d0d; border-radius: 6px; padding: 12px; overflow-x: auto; margin: 6px 0; }}
    pre code {{ background: none; padding: 0; color: #abb2bf; }}
    .md-h1 {{ font-size: 22px; font-weight: 700; color: #f2f3f5; margin: 8px 0 4px; border-bottom: 1px solid var(--bg3); padding-bottom: 4px; }}
    .md-h2 {{ font-size: 18px; font-weight: 700; color: #f2f3f5; margin: 6px 0 3px; }}
    .md-h3 {{ font-size: 15px; font-weight: 700; color: #f2f3f5; margin: 4px 0 2px; }}
    .md-bq {{ border-left: 3px solid var(--bg3); padding: 4px 10px; margin: 4px 0; color: var(--text-muted); }}
    .spoiler {{ background: var(--bg3); color: transparent; border-radius: 3px; cursor: pointer; padding: 0 3px; transition: .2s; }}
    .spoiler.revealed {{ color: inherit; }}
    .mention {{ background: rgba(88,101,242,.2); color: #7289ff; border-radius: 3px; padding: 0 3px; font-weight: 500; }}
    a {{ color: var(--link); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .emoji {{ height: 1.25em; width: 1.25em; vertical-align: middle; object-fit: contain; }}

    /* ── REPLY ── */
    .reply-bar {{
      display: flex; align-items: center; gap: 6px;
      font-size: 12px; color: var(--text-dim); margin-bottom: 4px;
      padding-left: 4px; border-left: 2px solid var(--bg3);
    }}
    .reply-avatar {{ width: 16px; height: 16px; border-radius: 50%; }}
    .reply-author {{ color: var(--text-muted); font-weight: 600; }}
    .reply-preview {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300px; }}

    /* ── ATTACHMENTS ── */
    .attachments {{ margin-top: 6px; display: flex; flex-direction: column; gap: 6px; }}
    .att-img {{ max-width: 400px; max-height: 300px; border-radius: 6px; display: block; border: 1px solid var(--bg3); }}
    .att-video, .att-audio {{ max-width: 400px; border-radius: 6px; display: block; }}
    .att-file {{
      display: flex; align-items: center; gap: 10px;
      background: var(--bg2); border: 1px solid var(--bg3);
      border-radius: 6px; padding: 10px 14px; max-width: 380px;
    }}
    .att-icon {{ font-size: 22px; }}
    .att-info {{ display: flex; flex-direction: column; }}
    .att-name {{ color: var(--link); font-size: 13px; font-weight: 500; }}
    .att-size {{ color: var(--text-dim); font-size: 11px; }}

    /* ── EMBEDS ── */
    .embeds {{ margin-top: 6px; display: flex; flex-direction: column; gap: 6px; }}
    .embed {{
      background: var(--bg2); border-left: 4px solid #4f545c;
      border-radius: 0 6px 6px 0; padding: 12px 14px;
      max-width: 520px; display: grid; gap: 4px;
    }}
    .emb-author {{ display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: #f2f3f5; }}
    .emb-auth-icon {{ width: 20px; height: 20px; border-radius: 50%; }}
    .emb-title {{ font-size: 15px; font-weight: 700; color: #f2f3f5; }}
    .emb-desc {{ font-size: 13px; color: var(--text); line-height: 1.5; }}
    .emb-thumb {{ width: 80px; height: 80px; object-fit: cover; border-radius: 4px; float: right; margin-left: 12px; }}
    .emb-img {{ max-width: 100%; border-radius: 4px; margin-top: 6px; }}
    .emb-fields {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }}
    .field-inline {{ min-width: 130px; flex: 1; }}
    .field-block {{ width: 100%; }}
    .field-name {{ font-size: 12px; font-weight: 700; color: #f2f3f5; margin-bottom: 2px; }}
    .field-value {{ font-size: 13px; color: var(--text); }}
    .emb-footer {{ display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-dim); margin-top: 6px; }}
    .emb-foot-icon {{ width: 16px; height: 16px; border-radius: 50%; }}

    /* ── REACTIONS ── */
    .reactions {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }}
    .reaction {{
      display: flex; align-items: center; gap: 4px;
      background: rgba(88,101,242,.15); border: 1px solid rgba(88,101,242,.3);
      border-radius: 6px; padding: 2px 7px; font-size: 13px;
    }}
    .r-emoji {{ font-size: 15px; }}
    .r-count {{ font-size: 12px; color: #7289ff; font-weight: 600; }}

    /* ── COMPONENTS V1 + V2 ── */
    .components {{ margin-top: 6px; display: flex; flex-direction: column; gap: 4px; }}
    .comp-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .comp-btn {{
      display: inline-flex; align-items: center; gap: 5px;
      border-radius: 4px; padding: 4px 14px;
      font-size: 13px; font-weight: 500; cursor: default;
      border: none; text-decoration: none;
    }}
    .btn-primary   {{ background: #5865f2; color: #fff; }}
    .btn-secondary {{ background: var(--bg3); color: var(--text); }}
    .btn-success   {{ background: #23a55a; color: #fff; }}
    .btn-danger    {{ background: #f23f43; color: #fff; }}
    .btn-link      {{ background: transparent; color: var(--link); text-decoration: underline; }}
    .comp-btn[disabled] {{ opacity: .5; }}
    .comp-select {{
      background: var(--bg3); color: var(--text);
      border: 1px solid #1a1b1e; border-radius: 4px;
      padding: 6px 10px; font-size: 13px; min-width: 200px; cursor: default;
    }}
    .comp-input {{ display: flex; flex-direction: column; gap: 4px; font-size: 13px; }}
    .comp-input label {{ font-weight: 600; color: #f2f3f5; }}
    .input-val {{
      background: var(--bg3); border-radius: 4px;
      padding: 6px 10px; color: var(--text); min-height: 36px;
    }}
    .comp-unknown {{ color: var(--text-dim); font-style: italic; font-size: 12px; }}

    /* ── FOOTER ── */
    .export-footer {{
      padding: 20px 24px; border-top: 1px solid var(--bg3);
      text-align: center; font-size: 12px; color: var(--text-dim);
    }}
    .export-footer strong {{ color: var(--accent); }}

    @media (max-width: 680px) {{
      .sidebar {{ display: none; }}
      .main {{ margin-left: 0; }}
      .messages {{ padding: 12px 14px; }}
    }}
  </style>
</head>
<body>

<aside class="sidebar">
  <div class="guild-header">
    {guild_icon_tag}
    <span class="guild-name">{guild_name}</span>
  </div>
  <div class="sidebar-ch">
    <span class="ch-icon">{ch_icon}</span>
    <span>{ch_name}</span>
  </div>
  <div class="sidebar-stats">
    <span>{total}</span> mensagens exportadas
  </div>
</aside>

<div class="main">
  <div class="channel-bar">
    <span class="ch-icon">{ch_icon}</span>
    <span class="ch-name">{ch_name}</span>
    <span class="ch-count">{total} mensagens</span>
  </div>
  <div class="messages">
    {body}
  </div>
  <div class="export-footer">
    Transcrição gerada por <strong>Dash Studio</strong> · Sistema de Tickets
  </div>
</div>

</body>
</html>"""
