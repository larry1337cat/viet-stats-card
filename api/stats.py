from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.error
import json
import os

API = "https://api.github.com"

THEMES = {
    "dark": {"bg": "#141321", "title": "#fe428e", "text": "#a9fef7", "border": "#2a2942"},
    "light": {"bg": "#ffffff", "title": "#2f80ed", "text": "#434d58", "border": "#e4e2e2"},
}


def fetch(url, token=None):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "viet-stats-card")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=8) as res:
        return json.loads(res.read().decode())


def get_stats(username, token=None):
    user = fetch(f"{API}/users/{username}", token)

    repos, page = [], 1
    while True:
        batch = fetch(f"{API}/users/{username}/repos?per_page=100&page={page}", token)
        if not batch:
            break
        repos += batch
        if len(batch) < 100 or page >= 5:
            break
        page += 1

    stars = sum(r.get("stargazers_count", 0) for r in repos)

    langs = {}
    for r in repos:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top_lang = max(langs, key=langs.get) if langs else "N/A"

    return {
        "name": user.get("name") or username,
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "stars": stars,
        "top_lang": top_lang,
    }


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_card(d, theme="dark"):
    c = THEMES.get(theme, THEMES["dark"])
    rows = [
        ("📦", "Kho lưu trữ công khai", d["public_repos"]),
        ("⭐", "Tổng số sao nhận được", d["stars"]),
        ("👥", "Người theo dõi", d["followers"]),
        ("➡️", "Đang theo dõi", d["following"]),
        ("💻", "Ngôn ngữ dùng nhiều nhất", d["top_lang"]),
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

    return f'''<svg width="495" height="225" viewBox="0 0 495 225" xmlns="http://www.w3.org/2000/svg">
  <style>
    .card {{ font-family: "Segoe UI", Ubuntu, Sans-Serif; }}
    .title {{ font-size: 18px; font-weight: 600; fill: {c['title']}; }}
    .label, .value {{ font-size: 13px; fill: {c['text']}; }}
    .value {{ font-weight: 700; }}
    .stagger {{ opacity: 0; animation: fadeIn 0.3s ease-in-out forwards; }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  </style>
  <rect x="0.5" y="0.5" rx="10" width="494" height="224" fill="{c['bg']}" stroke="{c['border']}" />
  <g class="card">
    <text x="25" y="35" class="title">Thống kê GitHub · {esc(d['name'])}</text>
    {body}
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
        token = os.environ.get("GH_TOKEN")

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Cache-Control", "s-maxage=1800, stale-while-revalidate")
        self.end_headers()

        if not username:
            self.wfile.write(render_error("Thiếu tham số username").encode())
            return

        try:
            data = get_stats(username, token)
            self.wfile.write(render_card(data, theme).encode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.wfile.write(render_error("Không tìm thấy user này").encode())
            elif e.code == 403:
                self.wfile.write(render_error("Vượt giới hạn GitHub API, thử lại sau").encode())
            else:
                self.wfile.write(render_error(f"Lỗi GitHub API ({e.code})").encode())
        except Exception:
            self.wfile.write(render_error("Đã có lỗi xảy ra").encode())
