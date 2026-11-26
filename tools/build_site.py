"""Builds the static website in web/ (clipcutter.in). Shared header/footer, one function per page.

  python3 tools/build_site.py
"""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SITE = "https://clipcutter.in"
REL = "https://github.com/pandeymynk/clipcutter/releases/latest"
REPO = "https://github.com/pandeymynk/clipcutter"
YT = "https://www.youtube.com/channel/UC2say3EqnwX8rt2Wl0jIXGg"
VIDEO = "https://www.youtube.com/watch?v=IZMwiKB4aTA"
ISSUES = "https://github.com/pandeymynk/clipcutter/issues"

WIN = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 5.5 10.5 4.4v7.1H3zm0 13 7.5 1.1v-7H3zm8.5 1.3L21 21v-8.4h-9.5zm0-15.6v7.4H21V3z"/></svg>'
MAC = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.4 12.6c0-2.4 2-3.6 2.1-3.7-1.1-1.7-2.9-1.9-3.5-1.9-1.5-.2-2.9.9-3.7.9-.8 0-1.9-.9-3.2-.8-1.6 0-3.1 1-4 2.4-1.7 3-.4 7.4 1.2 9.8.8 1.2 1.8 2.5 3 2.4 1.2 0 1.7-.8 3.1-.8s1.9.8 3.2.8c1.3 0 2.1-1.2 2.9-2.4.9-1.3 1.3-2.6 1.3-2.7 0 0-2.4-.9-2.4-4M14 5.6c.7-.8 1.1-1.9 1-3-1 0-2.1.7-2.8 1.5-.6.7-1.2 1.8-1 2.9 1.1.1 2.1-.6 2.8-1.4"/></svg>'
AND = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.6 9.48l1.84-3.18a.38.38 0 0 0-.66-.38l-1.86 3.22a11.4 11.4 0 0 0-9.84 0L5.22 5.92a.38.38 0 1 0-.66.38L6.4 9.48A10.8 10.8 0 0 0 1 18h22a10.8 10.8 0 0 0-5.4-8.52M7 15.25a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5m10 0a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5"/></svg>'
DL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0 0-5-5m5 5 5-5M4 21h16"/></svg>'


def icon(path):
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'


def head(title, desc, path="", image="img/video-thumb.jpg"):
    url = f"{SITE}/{path}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:site_name" content="ClipCutter">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{SITE}/{image}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#07080c">
<link rel="icon" type="image/png" href="img/favicon.png">
<link rel="apple-touch-icon" href="img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/site.css?v=5">
</head>
<body>
"""


def nav(active=""):
    items = [("index.html#demo", "How it works", "how"), ("index.html#features", "Features", "features"),
             ("index.html#campaigns", "Campaigns", "campaigns"), ("download.html", "Download", "download"),
             ("index.html#faq", "FAQ", "faq")]
    links = "".join(f'<a href="{h}"{" class=on" if k == active else ""}>{t}</a>' for h, t, k in items)
    return f"""<header class="nav">
  <div class="wrap">
    <a class="logo" href="index.html"><img src="img/icon.png" alt="">ClipCutter</a>
    <nav class="menu">{links}</nav>
    <a class="btn sm primary" href="download.html">{DL}Download free</a>
    <button class="burger" aria-label="Menu">{icon('<path d="M4 7h16M4 12h16M4 17h16"/>')}</button>
  </div>
</header>
"""


FOOT = f"""<footer>
  <div class="wrap">
    <div class="fgrid">
      <div>
        <a class="logo" href="index.html"><img src="img/icon.png" alt="">ClipCutter</a>
        <p>Free clipping app for Windows, Mac and Android. Turn long streams into vertical clips with a hook and captions.</p>
      </div>
      <div><h4>Product</h4><a href="download.html">Download</a><a href="index.html#demo">How it works</a><a href="index.html#features">Features</a><a href="index.html#faq">FAQ</a></div>
      <div><h4>Company</h4><a href="contact.html">Contact</a><a href="{YT}" target="_blank" rel="noopener">YouTube</a><a href="{REPO}" target="_blank" rel="noopener">GitHub</a></div>
      <div><h4>Legal</h4><a href="privacy.html">Privacy policy</a><a href="terms.html">Terms of use</a></div>
    </div>
    <div class="fbot"><span>© <span data-year>2026</span> ClipCutter</span><span>Not affiliated with Rockstar Games, YouTube, Twitch, Kick or any campaign platform.</span></div>
  </div>
</footer>
<script src="assets/site.js?v=5" defer></script>
</body>
</html>
"""


def plat_cards():
    return f"""<div class="os3">
  <div class="plat rv d1" data-os="win"><div class="pi">{WIN}</div><b>Windows</b><span>Windows 10 / 11 · 64-bit</span>
    <a class="btn primary" href="{REL}" target="_blank" rel="noopener">{DL}Download .exe</a>
    <small>If "Windows protected your PC" appears: More info → Run anyway.</small></div>
  <div class="plat rv d2" data-os="mac"><div class="pi">{MAC}</div><b>macOS</b><span>Apple chip · M1, M2, M3, M4</span>
    <a class="btn primary" href="{REL}" target="_blank" rel="noopener">{DL}Download .dmg</a>
    <small>Drag to Applications, then right-click → Open the first time.</small></div>
  <div class="plat rv d3" data-os="android"><div class="pi">{AND}</div><b>Android<i>Beta</i></b><span>Android 10+ · runs fully offline</span>
    <a class="btn primary" href="{REL}" target="_blank" rel="noopener">{DL}Download .apk</a>
    <small>Allow "Install unknown apps" for your browser when asked.</small></div>
</div>"""


FAQ = [
    ("Is ClipCutter really free?", "Yes. It runs on your own device, so there are no server costs to pass on to you: no subscription, no credits and no watermark."),
    ("Do I need coding skills or an API key?", "No. Install it and paste a link. Clips, captions and hooks work out of the box. A free AI key (NVIDIA, Groq, OpenRouter or Gemini) is optional, only if you want AI-written hooks."),
    ("Which devices does it run on?", "Windows 10/11 (64-bit), Macs with an Apple chip (M1–M4), and Android 10+ phones (beta). 8 GB RAM is enough on a computer; on Android, 6 GB or more works best."),
    ("How long does a clip take?", "Most of the time goes into downloading the video. A 1h 43m GTA 6 stream took about 15 minutes on a normal laptop, and each clip rendered in under 30 seconds. Phones are slower."),
    ("Does it work for Hindi streams?", "Yes. It understands Hindi and English hype words, and Hindi captions can be shown in Hinglish (Roman letters)."),
    ("Can I edit a clip?", "Yes. Change the hook text or fix any caption word, and the clip re-renders in a few seconds. Title and post caption are editable too."),
    ("Will I earn money with it?", "ClipCutter makes the clips. Earnings come from clipping campaigns and depend on views, the campaign's rate and its rules. There's no guarantee, and fake views get accounts banned."),
    ("Can I clip any video?", "Only clip content you have permission to use, such as a campaign's own footage or a streamer who allows clipping."),
]


def faq_html():
    return "".join(f'<details class="rv"><summary>{q}</summary><p>{a}</p></details>' for q, a in FAQ)


# ---------------------------------------------------------------- pages
def index():
    caps = "".join(f"<span>{w}</span> " for w in "nobody expected this in GTA 6".split())
    marquee_items = "".join(f'<span><img src="img/brands/{b}.svg" alt="">{n}</span>' for b, n in
                            [("youtube", "YouTube"), ("twitch", "Twitch"), ("kick", "Kick"), ("tiktok", "TikTok"),
                             ("instagram", "Instagram Reels"), ("youtube", "YouTube Shorts"), ("github", "Open source")])
    import json
    term = json.dumps([["cmd", "$ git clone github.com/someone/free-ai-clipper"], ["cmd", "$ pip install -r requirements.txt"],
                       ["", "ERROR: Failed building wheel for torch"], ["cmd", "$ python main.py stream.mp4"],
                       ["", "KeyError: 'OPENAI_API_KEY'"]])
    ok = json.dumps([["cmd", "> Paste link · 3 clips · Make clips"], ["ok", "✓ Downloaded · found 9 moments"],
                     ["ok", "✓ clip_01.mp4  virality 75"], ["ok", "✓ 3 clips ready"]])
    return head("ClipCutter: free AI clipping app for GTA 6 streams",
                "Free app for Windows, Mac and Android. Paste a stream link and get vertical 9:16 clips with a hook and word-by-word captions. No code, no API keys.") + nav() + f"""
<main>
<div class="hero">
  <div class="aurora"><i></i><i></i><i></i></div><div class="grid-bg"></div>
  <div class="wrap">
    <span class="pill rv"><b>NEW</b>GTA 6 is out. Clip it for free.</span>
    <h1 class="rv d1">Turn any <span class="rot"><span class="grad">GTA 6 stream</span><span class="grad">Twitch VOD</span><span class="grad">podcast</span><span class="grad">YouTube video</span></span>into viral clips.</h1>
    <p class="lead rv d2">Paste a link. ClipCutter finds the best moments and makes vertical clips with a hook and word-by-word captions. It runs on your own device. No code, no API keys, ₹0.</p>
    <div class="ctas rv d3">
      <a class="btn primary" href="download.html">{DL}Download free</a>
      <a class="btn ghost" href="#demo">{icon('<path d="M8 5v14l11-7z"/>')}See it work</a>
    </div>
    <div class="plats rv d4"><span>Available on</span><b>{WIN}Windows</b><b>{MAC}macOS</b><b>{AND}Android</b></div>
    <div class="stage">
      <div class="window">
        <div class="bar"><i></i><i></i><i></i><span><em>ClipCutter</em></span></div>
        <video data-auto muted loop playsinline preload="metadata" poster="media/demo-make.jpg" src="media/demo-make.mp4"></video>
      </div>
      <div class="phone"><video data-auto muted loop playsinline preload="metadata" src="media/clip.mp4"></video></div>
      <div class="chip c1"><span class="ic">✓</span><span><b>3 clips ready</b>from a 1h 43m stream</span></div>
      <div class="chip c2"><span class="ic">75</span><span><b>Virality score</b>picked automatically</span></div>
    </div>
  </div>
</div>

<div class="mlabel">Clip from · post to</div>
<div class="marquee"><div class="track">{marquee_items}{marquee_items}</div></div>

<section>
  <div class="wrap center">
    <span class="eyebrow rv">Why we built it</span>
    <h2 class="rv d1">"Free clipping" usually means<br>a GitHub repo.</h2>
    <p class="sub rv d2">Then come the terminal, Python, CUDA and API keys, and if you're not technical, it breaks. So we built a real app.</p>
    <div class="compare" style="text-align:left">
      <div class="col bad rv d1">
        <h3>The usual "free" way</h3>
        <ul><li><i>✕</i>Clone a repo, install Python packages</li><li><i>✕</i>Set up ffmpeg, CUDA and an AI API key</li>
        <li><i>✕</i>Run terminal commands for every video</li><li><i>✕</i>Or pay: subscriptions, credits, limits</li></ul>
        <div class="term" data-type='{term}'></div>
      </div>
      <div class="col good rv d2">
        <h3><img src="img/icon.png" alt="" width="26" height="26" style="border-radius:7px">ClipCutter</h3>
        <ul><li><i>✓</i>Download, double-click, install. That's it.</li><li><i>✓</i>No coding, no API keys, nothing to set up</li>
        <li><i>✓</i>Paste a link and click "Make clips"</li><li><i>✓</i>₹0. No subscription, no credits, no watermark</li></ul>
        <div class="term" data-type='{ok}'></div>
      </div>
    </div>
  </div>
</section>

<section id="demo" class="alt">
  <div class="wrap">
    <span class="eyebrow rv">How it works</span>
    <h2 class="rv d1">Watch it work. Real recordings,<br>no mock-ups.</h2>
    <p class="sub rv d2">Recorded on a normal Windows laptop, from a fresh install to finished GTA 6 clips.</p>
    <div class="demo">
      <div class="tabs rv">
        <button class="tab" data-src="media/demo-install.mp4" data-poster="media/demo-install.jpg" data-label="Real recording · install">
          <b><span>1</span>Install once</b><p>Download from GitHub, click "Run anyway" on the Windows warning, and the app opens in your browser.</p><i class="prog"></i></button>
        <button class="tab" data-src="media/demo-make.mp4" data-poster="media/demo-make.jpg" data-label="Real recording · making clips (sped up)">
          <b><span>2</span>Paste a link, make clips</b><p>Paste a GTA 6 stream, pick 3 clips. It downloads, finds the hype moments and renders each clip with a hook and captions.</p><i class="prog"></i></button>
        <button class="tab" data-src="media/demo-campaigns.mp4" data-poster="media/demo-campaigns.jpg" data-label="Real recording · Content Rewards">
          <b><span>3</span>Join a campaign, post</b><p>Pick a GTA campaign on Content Rewards or Vyro, post your clips, and submit them for paid views.</p><i class="prog"></i></button>
      </div>
      <div class="screen rv d2">
        <div class="bar"><i></i><i></i><i></i><span><em>clipcutter · localhost</em></span></div>
        <video muted playsinline preload="metadata"></video>
        <span class="label">Real screen recording</span>
      </div>
    </div>
  </div>
</section>

<section id="features">
  <div class="wrap">
    <span class="eyebrow rv">Features</span>
    <h2 class="rv d1">Everything a clip needs to perform.</h2>
    <div class="bento">
      <div class="feat w3 rv"><div class="ic">{icon('<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>')}</div><h3>Hook first</h3>
        <p>Every clip opens on its peak moment, zoomed in, with big hook text and a bass hit, so viewers don't scroll past.</p>
        <div class="viz"><div class="hookdemo"><i class="pk"></i><i></i><i></i><i></i><i></i></div><div style="margin-top:8px">peak moment → setup → payoff</div></div></div>
      <div class="feat w3 rv d1"><div class="ic">{icon('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8M8 13h5"/>')}</div><h3>Word-by-word captions</h3>
        <p>Captions pop in time with the voice. Hindi audio can be shown in Hinglish.</p>
        <div class="viz"><div class="capdemo">{caps}</div></div></div>
      <div class="feat rv"><div class="ic">{icon('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>')}</div><h3>Finds the best moments</h3>
        <p>Loudness, scene cuts, chat spikes and hype words, then each clip snaps to full sentences.</p>
        <div class="viz"><div class="wave">{"".join(f'<i class="{"hi" if k in (6,7,8,15,16) else ""}" style="height:{[30,45,38,52,40,60,85,95,80,50,42,36,48,40,58,92,88,46,38,30][k]}%;animation-delay:-{k*0.08:.2f}s"></i>' for k in range(20))}</div></div></div>
      <div class="feat rv d1"><div class="ic">{icon('<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>')}</div><h3>Vertical 9:16</h3>
        <p>Blur, crop or split-facecam layout, ready for Shorts, Reels and TikTok.</p></div>
      <div class="feat rv d2"><div class="ic">{icon('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>')}</div><h3>Edit any clip</h3>
        <p>Change the hook or fix caption words. The clip re-renders in seconds.</p></div>
      <div class="feat w3 rv"><div class="ic">{icon('<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/>')}</div><h3>Title, caption, hashtags</h3>
        <p>Written for every clip, plus campaign presets that add the right label, logo, CTA and exact post caption.</p></div>
      <div class="feat w3 rv d1"><div class="ic">{icon('<rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>')}</div><h3>Private by design</h3>
        <p>Everything runs on your own device. Your videos are never uploaded to us. There's no account to make.</p></div>
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap reel">
    <div>
      <span class="eyebrow rv">See the result</span>
      <h2 class="rv d1">Made for the feed.</h2>
      <p class="sub rv d2">Our own Short about ClipCutter, made the same way: hook in the first second, captions on every word, vertical from the start.</p>
      <div class="points">
        <div class="rv d1"><i>✓</i><span><b>Hook in the first second</b>, the moment people stop scrolling.</span></div>
        <div class="rv d2"><i>✓</i><span><b>Captions that follow the voice</b>, so it works on mute.</span></div>
        <div class="rv d3"><i>✓</i><span><b>Ready to post</b> with title, caption and hashtags.</span></div>
      </div>
      <div class="ctas rv d4" style="justify-content:flex-start;margin-top:34px"><a class="btn glow" href="download.html">{DL}Get ClipCutter free</a></div>
    </div>
    <div class="reelphone rv d2">
      <video data-auto muted loop playsinline preload="metadata" poster="media/reel-poster.jpg" src="media/reel.mp4"></video>
      <button class="snd" aria-label="Sound" data-off='{icon('<path d="M11 5 6 9H2v6h4l5 4z"/><path d="m23 9-6 6M17 9l6 6"/>')}' data-on='{icon('<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14"/>')}'>{icon('<path d="M11 5 6 9H2v6h4l5 4z"/><path d="m23 9-6 6M17 9l6 6"/>')}</button>
    </div>
  </div>
</section>

<section style="padding-top:60px;padding-bottom:60px">
  <div class="wrap stats">
    <div class="stat rv"><b data-count="0" data-pre="₹">₹0</b><span>to use, forever</span></div>
    <div class="stat rv d1"><b data-count="3">3</b><span>platforms: Windows, Mac, Android</span></div>
    <div class="stat rv d2"><b data-count="30" data-pre="&lt;" data-suf="s">30s</b><span>to render a clip</span></div>
    <div class="stat rv d3"><b data-count="0">0</b><span>lines of code to write</span></div>
  </div>
</section>

<section id="campaigns">
  <div class="wrap">
    <div class="split">
      <div>
        <span class="eyebrow rv">Where to earn</span>
        <h2 class="rv d1">Clipping campaigns pay per view.</h2>
        <p class="sub rv d2">Streamers and brands pay clippers for the views their clips get. Pick a campaign, read its rules, then post clips made with ClipCutter.</p>
      </div>
      <div class="screen rv d2"><div class="bar"><i></i><i></i><i></i><span><em>contentrewards.com</em></span></div>
        <video data-auto muted loop playsinline preload="metadata" poster="media/demo-campaigns.jpg" src="media/demo-campaigns.mp4"></video></div>
    </div>
    <div class="camps">
      <a class="camp rv" href="https://contentrewards.com" target="_blank" rel="noopener"><b>Content Rewards</b><span>The biggest marketplace. Search "GTA".</span><em>contentrewards.com →</em></a>
      <a class="camp rv d1" href="https://vyro.com" target="_blank" rel="noopener"><b>Vyro</b><span>Clipping platform used by MrBeast.</span><em>vyro.com →</em></a>
      <div class="camp rv d2"><b>ClipLaunch · Clipping Nation</b><span>Agencies running campaigns on Discord.</span></div>
      <div class="camp rv d3"><b>Streamer Discords</b><span>Many streamers pay clippers directly.</span></div>
    </div>
    <p class="note">Rates and budgets change. Check each campaign's rules before you join. Earnings aren't guaranteed.</p>
  </div>
</section>

<section id="download" class="alt">
  <div class="wrap center">
    <span class="eyebrow rv">Download</span>
    <h2 class="rv d1">Get ClipCutter. It's free.</h2>
    <p class="sub rv d2">One installer, everything included. Pick your device.</p>
    {plat_cards()}
    <p class="note">Not code-signed yet, so your device shows a warning the first time. <a href="download.html" style="color:var(--acc2)">Install guide →</a></p>
  </div>
</section>

<section id="faq">
  <div class="wrap">
    <h2 class="center rv">Questions</h2>
    <div class="faq">{faq_html()}</div>
  </div>
</section>

<section style="padding-top:20px">
  <div class="wrap">
    <div class="band rv">
      <div class="aurora"><i></i><i></i><i></i></div>
      <h2 style="margin-top:0">Your first clip is 15 minutes away.</h2>
      <p class="sub" style="margin:0 auto 30px">Install once. Join a campaign. Start clipping.</p>
      <div class="ctas"><a class="btn primary" href="download.html">{DL}Download free</a><a class="btn ghost" href="{VIDEO}" target="_blank" rel="noopener">Watch the setup video</a></div>
    </div>
  </div>
</section>
</main>
""" + FOOT


def download():
    return head("Download ClipCutter for Windows, Mac and Android",
                "Download ClipCutter free for Windows 10/11, macOS (Apple chip) and Android. Install guide, system requirements and fixes for first-run warnings.",
                "download") + nav("download") + f"""
<main>
<div class="hero" style="padding-bottom:40px">
  <div class="aurora"><i></i><i></i><i></i></div><div class="grid-bg"></div>
  <div class="wrap">
    <span class="pill rv"><b>FREE</b>Latest version from GitHub</span>
    <h1 class="rv d1" style="font-size:clamp(40px,6vw,72px)">Download <span class="grad">ClipCutter</span></h1>
    <p class="lead rv d2">One installer with everything included: the video engine, speech-to-text and fonts. Nothing else to set up.</p>
    {plat_cards()}
  </div>
</div>

<section style="padding-top:40px">
  <div class="wrap">
    <span class="eyebrow rv">Install guide</span>
    <h2 class="rv d1">Install in under a minute.</h2>
    <div class="split" style="margin-top:30px;align-items:start">
      <div class="screen rv"><div class="bar"><i></i><i></i><i></i><span><em>Windows install · real recording</em></span></div>
        <video data-auto muted loop playsinline preload="metadata" poster="media/demo-install.jpg" src="media/demo-install.mp4"></video></div>
      <div class="rv d1">
        <div class="box"><b style="font-size:18px">{WIN} Windows</b>
          <ol class="steps"><li>Download <code>ClipCutter-…-windows-x64-setup.exe</code> and open it.</li>
          <li>A blue "Windows protected your PC" box appears because the app isn't code-signed yet. Click <b>More info</b>, then <b>Run anyway</b>.</li>
          <li>Click Next → Install → Finish. ClipCutter opens in your browser.</li></ol></div>
      </div>
    </div>
    <div class="split" style="margin-top:22px;align-items:start">
      <div class="box rv"><b style="font-size:18px">{MAC} macOS</b>
        <ol class="steps"><li>Download the <code>.dmg</code> and open it.</li><li>Drag ClipCutter into Applications.</li>
        <li>The first time, right-click ClipCutter → <b>Open</b> → <b>Open</b>. After that, open it normally.</li></ol></div>
      <div class="box rv d1"><b style="font-size:18px">{AND} Android (beta)</b>
        <ol class="steps"><li>Download the <code>.apk</code> on your phone.</li><li>When asked, allow <b>Install unknown apps</b> for your browser.</li>
        <li>Open ClipCutter, paste a link and tap Make clips. Keep the phone charging for long streams.</li></ol></div>
    </div>
  </div>
</section>

<section class="alt">
  <div class="wrap">
    <span class="eyebrow rv">Requirements</span>
    <h2 class="rv d1">What you need.</h2>
    <div class="req">
      <div class="rv"><b>Windows</b>Windows 10 or 11, 64-bit<br>8 GB RAM<br>5 GB free disk space</div>
      <div class="rv d1"><b>macOS</b>macOS 12 or newer<br>Apple chip (M1–M4)<br>5 GB free disk space</div>
      <div class="rv d2"><b>Android</b>Android 10 or newer, 64-bit<br>6 GB RAM recommended<br>3 GB free storage</div>
    </div>
    <p class="note">Intel Macs aren't supported. Long streams download in full first, so keep enough free space.</p>
  </div>
</section>

<section>
  <div class="wrap">
    <h2 class="center rv">Troubleshooting</h2>
    <div class="faq">
      <details class="rv"><summary>Downloads fail or say "HTTP 403"</summary><p>Sites like YouTube change often. Click <b>↻ Update downloader</b> at the bottom of the ClipCutter page, then try again.</p></details>
      <details class="rv"><summary>"No space left on device"</summary><p>The whole video is downloaded once before clipping. Free a few GB, or clip shorter videos.</p></details>
      <details class="rv"><summary>It's stuck on the speech model</summary><p>The first time a video has no captions, ClipCutter downloads a speech model (about 1.6 GB on a computer). It only happens once.</p></details>
      <details class="rv"><summary>Still stuck?</summary><p>Open an issue on <a href="{ISSUES}" target="_blank" rel="noopener" style="color:var(--acc2)">GitHub</a> or comment on the YouTube video and we'll help.</p></details>
    </div>
  </div>
</section>
</main>
""" + FOOT


def legal(title, path, updated, body):
    return head(f"{title} · ClipCutter", f"{title} for ClipCutter and clipcutter.in.", path) + nav() + f"""
<main class="page"><div class="wrap"><div class="doc">
<span class="eyebrow">Legal</span>
<h1>{title}</h1>
<p class="upd">Last updated {updated}</p>
{body}
</div></div></main>
""" + FOOT


def privacy():
    return legal("Privacy policy", "privacy", "27 November 2026", f"""
<p>ClipCutter is built to keep your data on your own device. This policy explains what that means for the app and for this website.</p>
<h2>The ClipCutter app</h2>
<ul>
<li><b>Your videos stay on your device.</b> Downloads, transcripts and finished clips are saved on your computer or phone. We don't upload them anywhere.</li>
<li><b>No account, no tracking.</b> The app has no sign-up and doesn't send analytics or usage data to us.</li>
<li><b>What the app connects to:</b> the video sites you paste links from (to download the video and its captions), Hugging Face (to download the speech model once), and PyPI (to update the video downloader when you click "Update downloader").</li>
<li><b>Optional AI key.</b> If you add an AI key (NVIDIA, Groq, OpenRouter, Gemini or another provider), it's stored only on your device, and the clip's transcript text is sent to that provider to write the hook. That provider's own privacy policy applies. Without a key, nothing is sent.</li>
</ul>
<h2>This website</h2>
<ul>
<li>clipcutter.in doesn't use cookies, analytics or ads, and has no forms.</li>
<li>Our host, Vercel, keeps standard server logs (such as IP address and pages requested) for security and reliability.</li>
<li>Fonts load from Google Fonts. Download buttons go to GitHub, and video links go to YouTube; their own privacy policies apply there.</li>
</ul>
<h2>Children</h2>
<p>ClipCutter isn't directed at children under 13.</p>
<h2>Changes</h2>
<p>If this policy changes, we'll update this page and the date above.</p>
<h2>Contact</h2>
<p>Questions about privacy? See the <a href="contact.html">contact page</a>.</p>
""")


def terms():
    return legal("Terms of use", "terms", "27 November 2026", f"""
<p>By downloading or using ClipCutter or this website, you agree to these terms.</p>
<h2>The software</h2>
<p>ClipCutter is provided free of charge, "as is", without warranties of any kind. We aren't liable for any loss or damage from using it, including lost data, failed clips or rejected campaign submissions. The source code is available on <a href="{REPO}" target="_blank" rel="noopener">GitHub</a>.</p>
<h2>Your content and permissions</h2>
<ul>
<li>You're responsible for the videos you clip and post. Only clip content you own or have permission to use, such as a campaign's own footage or a streamer who allows clipping.</li>
<li>Follow the terms of the sites you download from and post to, and the rules of any campaign you join.</li>
<li>Don't use ClipCutter to infringe copyright, mislead viewers or buy fake views.</li>
</ul>
<h2>No earnings promise</h2>
<p>ClipCutter makes clips. It doesn't guarantee views, campaign approval or income. Campaign rates, budgets and rules are set by the campaign platforms, not by us.</p>
<h2>Third parties</h2>
<p>ClipCutter isn't affiliated with or endorsed by Rockstar Games, YouTube, Twitch, Kick, TikTok, Instagram, Content Rewards, Vyro or any other platform mentioned. All trademarks belong to their owners.</p>
<h2>Optional AI providers</h2>
<p>If you add your own AI key, your use of that provider is governed by its terms.</p>
<h2>Changes</h2>
<p>We may update these terms. The date above shows the latest version.</p>
""")


def contact():
    return head("Contact · ClipCutter", "Get help with ClipCutter or say hello.", "contact") + nav() + f"""
<main class="page"><div class="wrap"><div class="doc" style="max-width:none">
<span class="eyebrow">Contact</span>
<h1>Talk to us</h1>
<p class="sub">The fastest way to get help is to open an issue on GitHub or comment on our YouTube video.</p>
<div class="contact">
  <a class="rv" href="{ISSUES}" target="_blank" rel="noopener"><img src="img/brands/github.svg" alt=""><b>Report a bug</b><span>Open an issue on GitHub with what you tried and what happened.</span></a>
  <a class="rv d1" href="{YT}" target="_blank" rel="noopener"><img src="img/brands/youtube.svg" alt=""><b>YouTube</b><span>Setup videos and updates. Ask in the comments.</span></a>
  <a class="rv d2" href="download.html"><img src="img/icon.png" alt="" style="border-radius:8px"><b>Install help</b><span>Step-by-step guide and fixes for common problems.</span></a>
</div>
</div></div></main>
""" + FOOT


def notfound():
    return head("Page not found · ClipCutter", "This page doesn't exist.", "404") + nav() + f"""
<main><div class="hero" style="min-height:80vh;display:grid;place-items:center">
  <div class="aurora"><i></i><i></i><i></i></div>
  <div class="wrap"><h1 style="font-size:clamp(80px,14vw,160px);margin:0" class="grad">404</h1>
  <p class="lead">This page doesn't exist. Maybe it got clipped.</p>
  <div class="ctas"><a class="btn primary" href="index.html">Go home</a><a class="btn ghost" href="download.html">Download</a></div></div>
</div></main>
""" + FOOT


PAGES = {"index.html": index, "download.html": download, "privacy.html": privacy, "terms.html": terms,
         "contact.html": contact, "404.html": notfound}

if __name__ == "__main__":
    import re
    for name, fn in PAGES.items():
        html = fn()
        # step lists are flex rows: wrap each item's content so inline tags don't become separate columns
        html = re.sub(r'(<ol class="steps">)(.*?)(</ol>)',
                      lambda m: m[1] + re.sub(r"<li>(.*?)</li>", r"<li><span>\1</span></li>", m[2], flags=re.S) + m[3],
                      html, flags=re.S)
        (WEB / name).write_text(html, encoding="utf-8")
    urls = ["", "download", "privacy", "terms", "contact"]
    (WEB / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     + "".join(f"  <url><loc>{SITE}/{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    (WEB / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    (WEB / "vercel.json").write_text('{\n  "cleanUrls": true,\n  "trailingSlash": false,\n  "headers": [\n'
                                     '    {"source": "/media/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=604800"}]},\n'
                                     '    {"source": "/(img|assets)/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=86400"}]}\n  ]\n}\n')
    print("built", ", ".join(PAGES))
