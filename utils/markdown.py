import re
import html as html_mod

BOLD        = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
ITALIC_A    = re.compile(r"\*(.+?)\*", re.DOTALL)
ITALIC_U    = re.compile(r"_(.+?)_", re.DOTALL)
UNDERLINE   = re.compile(r"__(.+?)__", re.DOTALL)
STRIKE      = re.compile(r"~~(.+?)~~", re.DOTALL)
SPOILER     = re.compile(r"\|\|(.+?)\|\|", re.DOTALL)
CODE_BLOCK  = re.compile(r"```(?:\w+\n)?(.*?)```", re.DOTALL)
INLINE_CODE = re.compile(r"`([^`]+)`")
MENTION_U   = re.compile(r"&lt;@!?(\d+)&gt;")
MENTION_R   = re.compile(r"&lt;@&amp;(\d+)&gt;")
MENTION_C   = re.compile(r"&lt;#(\d+)&gt;")
EMOJI_CUSTOM= re.compile(r"&lt;a?:(\w+):(\d+)&gt;")
HEADER_3    = re.compile(r"^### (.+)$", re.MULTILINE)
HEADER_2    = re.compile(r"^## (.+)$", re.MULTILINE)
HEADER_1    = re.compile(r"^# (.+)$", re.MULTILINE)
BLOCKQUOTE  = re.compile(r"^&gt; (.+)$", re.MULTILINE)
LINK        = re.compile(r"\[(.+?)\]\((https?://\S+?)\)")
URL_BARE    = re.compile(r'(?<!["\'=>])(https?://[^\s<>"\']+)', re.IGNORECASE)


def parse(text: str) -> str:
    text = html_mod.escape(text)

    text = CODE_BLOCK.sub(lambda m: f'<pre><code>{m.group(1).strip()}</code></pre>', text)
    text = INLINE_CODE.sub(lambda m: f'<code>{m.group(1)}</code>', text)

    text = HEADER_1.sub(lambda m: f'<h1 class="md-h1">{m.group(1)}</h1>', text)
    text = HEADER_2.sub(lambda m: f'<h2 class="md-h2">{m.group(1)}</h2>', text)
    text = HEADER_3.sub(lambda m: f'<h3 class="md-h3">{m.group(1)}</h3>', text)
    text = BLOCKQUOTE.sub(lambda m: f'<blockquote class="md-bq">{m.group(1)}</blockquote>', text)

    text = UNDERLINE.sub(lambda m: f'<u>{m.group(1)}</u>', text)
    text = BOLD.sub(lambda m: f'<strong>{m.group(1)}</strong>', text)
    text = ITALIC_A.sub(lambda m: f'<em>{m.group(1)}</em>', text)
    text = ITALIC_U.sub(lambda m: f'<em>{m.group(1)}</em>', text)
    text = STRIKE.sub(lambda m: f'<s>{m.group(1)}</s>', text)
    text = SPOILER.sub(lambda m: f'<span class="spoiler" onclick="this.classList.toggle(\'revealed\')">{m.group(1)}</span>', text)

    text = LINK.sub(lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>', text)
    text = URL_BARE.sub(lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>', text)

    text = MENTION_U.sub(r'<span class="mention">@\1</span>', text)
    text = MENTION_R.sub(r'<span class="mention">@\1</span>', text)
    text = MENTION_C.sub(r'<span class="mention">#\1</span>', text)
    text = EMOJI_CUSTOM.sub(
        lambda m: f'<img class="emoji" src="https://cdn.discordapp.com/emojis/{m.group(2)}.webp" alt=":{m.group(1)}:" title=":{m.group(1)}:">',
        text,
    )

    text = text.replace("\n", "<br>")
    return text
