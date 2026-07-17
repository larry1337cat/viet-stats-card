from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import urllib.error
import json
import math
import os

LANG_FETCH_WORKERS = 10

API = "https://api.github.com"

THEMES = {
    "dark": {"bg": "#141321", "title": "#fe428e", "text": "#a9fef7", "border": "#2a2942"},
    "light": {"bg": "#ffffff", "title": "#2f80ed", "text": "#434d58", "border": "#e4e2e2"},
}

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#2b7489",
    "Java": "#b07219", "HTML": "#e34c26", "CSS": "#563d7c", "C": "#555555",
    "C++": "#f34b7d", "C#": "#178600", "Go": "#00ADD8", "Rust": "#dea584",
    "PHP": "#4F5D95", "Ruby": "#701516", "Shell": "#89e051", "Kotlin": "#A97BFF",
    "Swift": "#ffac45", "Dart": "#00B4AB", "Vue": "#41b883",
}


def fetch(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "viet-stats-card")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=8) as res:
        return json.loads(res.read().decode())


def get_repos(username, token=None):
    safe_username = quote(username)
    repos, page = [], 1
    while True:
        batch = fetch(f"{API}/users/{safe_username}/repos?per_page=100&page={page}", token)
        if not batch:
            break
        repos += batch
        if len(batch) < 100 or page >= 5:
            break
        page += 1
    return repos


def fetch_repo_languages(username, repo_name, token=None):
    safe_username = quote(username)
    safe_repo_name = quote(repo_name)
    try:
        return fetch(f"{API}/repos/{safe_username}/{safe_repo_name}/languages", token)
    except urllib.error.HTTPError:
        return {}


MIN_LANGS_COUNT = 5
MAX_LANGS_COUNT = 10
DEFAULT_LANGS_COUNT = 5


def clamp_langs_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        return DEFAULT_LANGS_COUNT
    return max(MIN_LANGS_COUNT, min(MAX_LANGS_COUNT, count))


def get_language_breakdown(username, repos, token=None, include_forks=False, cap=30, langs_count=DEFAULT_LANGS_COUNT):
    targets = repos if include_forks else [r for r in repos if not r.get("fork")]
    targets = sorted(targets, key=lambda r: r.get("size", 0), reverse=True)[:cap]

    totals = {}
    with ThreadPoolExecutor(max_workers=LANG_FETCH_WORKERS) as pool:
        results = pool.map(lambda r: fetch_repo_languages(username, r["name"], token), targets)
        for data in results:
            for lang, count in data.items():
                totals[lang] = totals.get(lang, 0) + count

    total = sum(totals.values())
    if total == 0:
        return []

    breakdown = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:langs_count]
    return [(lang, round(count / total * 100, 1)) for lang, count in breakdown]


def get_stats(username, token=None, include_forks=False, langs_count=DEFAULT_LANGS_COUNT):
    user = fetch(f"{API}/users/{quote(username)}", token)
    repos = get_repos(username, token)

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    langs_breakdown = get_language_breakdown(username, repos, token, include_forks, langs_count=langs_count)
    top_lang = langs_breakdown[0][0] if langs_breakdown else "N/A"

    return {
        "name": user.get("name") or username,
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "stars": stars,
        "top_lang": top_lang,
        "lang_breakdown": langs_breakdown,
    }


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lang_color(name):
    return LANG_COLORS.get(name, "#8b8b8b")


def pie_slice(cx, cy, r, start_pct, end_pct, color):
    start_angle = start_pct / 100 * 360 - 90
    end_angle = end_pct / 100 * 360 - 90
    start_rad, end_rad = math.radians(start_angle), math.radians(end_angle)
    x1, y1 = cx + r * math.cos(start_rad), cy + r * math.sin(start_rad)
    x2, y2 = cx + r * math.cos(end_rad), cy + r * math.sin(end_rad)
    large_arc = 1 if end_pct - start_pct > 50 else 0
    return f'<path d="M{cx},{cy} L{x1:.2f},{y1:.2f} A{r},{r} 0 {large_arc} 1 {x2:.2f},{y2:.2f} Z" fill="{color}" />'


def render_card(d, theme="dark", chart="bar"):
    c = THEMES.get(theme, THEMES["dark"])
    rows = [
        ("📦", "Kho lưu trữ công khai", d["public_repos"]),
        ("⭐", "Tổng số sao nhận được", d["stars"]),
        ("👥", "Người theo dõi", d["followers"]),
        ("➡️", "Đang theo dõi", d["following"]),
    ]

    body = ""
    for i, (icon, label, value) in enumerate(rows):
        y = 70 + i * 25
        body += f'''
        <g class="stagger" style="animation-delay: {i * 100}ms" transform="translate(25, {y})">
          <text class="icon" x="0" y="0">{icon}</text>
          <text class="label" x="28" y="0">{esc(label)}:</text>
          <text class="value" x="420" y="0" text-anchor="end">{esc(value)}</text>
        </g>'''

    breakdown = d.get("lang_breakdown", [])
    section_y = 70 + len(rows) * 25 + 15

    if chart == "pie":
        cx, cy, r = 25 + 55, section_y + 55, 50
        slices = ""
        cursor = 0
        for lang, pct in breakdown:
            slices += pie_slice(cx, cy, r, cursor, cursor + pct, lang_color(lang))
            cursor += pct

        legend = ""
        for i, (lang, pct) in enumerate(breakdown):
            ly = section_y + i * 22
            legend += f'''
            <g class="stagger" style="animation-delay: {(len(rows) + i) * 100}ms" transform="translate(155, {ly + 8})">
              <circle cx="4" cy="-4" r="4" fill="{lang_color(lang)}" />
              <text class="label" x="14" y="0">{esc(lang)} {pct}%</text>
            </g>'''

        chart_svg = f'<g>{slices}</g>{legend}'
        height = max(section_y + r * 2 + 20, section_y + len(breakdown) * 22 + 20)

    else:
        bar_width = 445
        bar_x = 25
        bar_segments = ""
        x_cursor = bar_x
        for lang, pct in breakdown:
            seg_width = bar_width * pct / 100
            bar_segments += f'<rect x="{x_cursor:.1f}" y="{section_y}" width="{seg_width:.1f}" height="8" fill="{lang_color(lang)}" />'
            x_cursor += seg_width

        legend = ""
        for i, (lang, pct) in enumerate(breakdown):
            col = i % 2
            row = i // 2
            lx = bar_x + col * 230
            ly = section_y + 30 + row * 22
            legend += f'''
            <g class="stagger" style="animation-delay: {(len(rows) + i) * 100}ms" transform="translate({lx}, {ly})">
              <circle cx="4" cy="-4" r="4" fill="{lang_color(lang)}" />
              <text class="label" x="14" y="0">{esc(lang)} {pct}%</text>
            </g>'''

        chart_svg = f'<rect x="{bar_x}" y="{section_y}" width="{bar_width}" height="8" rx="4" fill="#2a2942" />{bar_segments}{legend}'
        height = section_y + 40 + ((len(breakdown) + 1) // 2) * 22 + 10

    return f'''<svg width="495" height="{height}" viewBox="0 0 495 {height}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .card {{ font-family: "Segoe UI", Ubuntu, Sans-Serif; }}
    .title {{ font-size: 18px; font-weight: 600; fill: {c['title']}; }}
    .label, .value {{ font-size: 13px; fill: {c['text']}; }}
    .value {{ font-weight: 700; }}
    .stagger {{ opacity: 0; animation: fadeIn 0.3s ease-in-out forwards; }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  </style>
  <rect x="0.5" y="0.5" rx="10" width="494" height="{height - 1}" fill="{c['bg']}" stroke="{c['border']}" />
  <g class="card">
    <text x="25" y="35" class="title">Thống kê GitHub · {esc(d['name'])}</text>
    {body}
    {chart_svg}
  </g>
</svg>'''


def render_error(msg):
    return f'''<svg width="495" height="120" viewBox="0 0 495 120" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" rx="10" width="494" height="119" fill="#141321" stroke="#2a2942" />
  <text x="25" y="55" font-family="Segoe UI, Sans-Serif" font-size="14" fill="#fe428e">Lỗi: {esc(msg)}</text>
  <text x="25" y="80" font-family="Segoe UI, Sans-Serif" font-size="12" fill="#a9fef7">Kiểm tra lại username hoặc thử lại sau.</text>
</svg>'''


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        username = query.get("username", [None])[0]
        theme = query.get("theme", ["dark"])[0]
        chart = query.get("chart", ["bar"])[0]
        include_forks = query.get("include_forks", ["false"])[0].lower() == "true"
        langs_count = clamp_langs_count(query.get("langs_count", [DEFAULT_LANGS_COUNT])[0])
        token = os.environ.get("GH_TOKEN")

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Cache-Control", "s-maxage=1800, stale-while-revalidate")
        self.end_headers()

        if not username:
            self.wfile.write(render_error("Thiếu tham số username").encode())
            return

        try:
            data = get_stats(username, token, include_forks, langs_count)
            self.wfile.write(render_card(data, theme, chart).encode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.wfile.write(render_error("Không tìm thấy user này").encode())
            elif e.code == 403:
                self.wfile.write(render_error("Vượt giới hạn GitHub API, thử lại sau").encode())
            else:
                self.wfile.write(render_error(f"Lỗi GitHub API ({e.code})").encode())
        except Exception:
            self.wfile.write(render_error("Đã có lỗi xảy ra").encode())
