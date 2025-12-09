"""
Simple Flask-based "Link Hub" / launcher scaffold.
Save as linkhub.py and run with: FLASK_APP=linkhub.py flask run --host=0.0.0.0 --port=5000

Features:
- index page with responsive grid of link cards
- add / edit / delete links via an admin page protected by ADMIN_PASSWORD env var
- stores links in links.json (created automatically)
- search & categories & optional icons
- single-file for quick testing; easy to split into templates/static later

Dependencies: Flask (pip install flask)
"""
from flask import Flask, request, redirect, url_for, render_template_string, jsonify, abort
import os
import json
from urllib.parse import urlparse
from datetime import datetime

app = Flask(__name__)
DATA_FILE = os.environ.get('LINKHUB_DATA', 'links.json')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')

# Default sample links if none exist
DEFAULT_LINKS = [
    {"id": 1, "title": "Google", "url": "https://www.google.com", "notes": "Search", "category": "Search", "created": ""},
    {"id": 2, "title": "GitHub", "url": "https://github.com", "notes": "Code hosting", "category": "Dev", "created": ""},
    {"id": 3, "title": "YouTube", "url": "https://www.youtube.com", "notes": "Videos", "category": "Media", "created": ""}
]


def load_links():
    if not os.path.exists(DATA_FILE):
        for l in DEFAULT_LINKS:
            l['created'] = datetime.utcnow().isoformat() + 'Z'
        save_links(DEFAULT_LINKS)
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_links(links):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def next_id(links):
    if not links:
        return 1
    return max(l.get('id', 0) for l in links) + 1


# --- Templates (render_template_string to keep single-file) ---
BASE_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Link Hub</title>
  <style>
    :root{--bg:#0f1724;--card:#0b1220;--muted:#9aa4b2;--accent:#06b6d4}
    body{font-family:Inter,system-ui,Segoe UI,Roboto,Arial; margin:0;background:linear-gradient(180deg,#071021, #071826);color:#e6eef6}
    .container{max-width:1100px;margin:36px auto;padding:24px}
    header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
    h1{margin:0;font-size:20px}
    .search{min-width:220px}
    input[type=text]{padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.06);background:transparent;color:inherit}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
    .card{background:var(--card);padding:14px;border-radius:12px;box-shadow:0 6px 18px rgba(2,6,23,0.6);display:flex;flex-direction:column;gap:8px}
    .card a{color:inherit;text-decoration:none}
    .meta{font-size:13px;color:var(--muted)}
    .category{font-size:12px;padding:4px 8px;border-radius:999px;background:rgba(255,255,255,0.03);display:inline-block}
    footer{margin-top:26px;font-size:13px;color:var(--muted)}
    .small{font-size:13px;color:var(--muted)}
    .top-actions{display:flex;gap:8px;align-items:center}
    button{background:var(--accent);border:none;color:#042; padding:8px 12px;border-radius:8px;font-weight:600}
    .muted-btn{background:transparent;border:1px solid rgba(255,255,255,0.04);color:var(--muted)}
    .admin-link{font-size:13px;color:var(--muted);text-decoration:none}
    .notes{font-size:13px;color:var(--muted);min-height:30px}
    @media (max-width:600px){.container{padding:14px}}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>Link Hub</h1>
        <div class="small">Переходник на другие сайты — удобные ярлыки и категории</div>
      </div>
      <div class="top-actions">
        <form method="get" action="/" class="search">
          <input type="text" name="q" placeholder="Поиск ссылок..." value="{{q|e}}">
        </form>
        <a class="admin-link" href="/admin">Админ</a>
      </div>
    </header>

    <main>
      {% if categories %}
      <div style="margin-bottom:12px">
        Категории:
        {% for c in categories %}
          <a href="/?category={{c|urlencode}}" class="category">{{c}}</a>
        {% endfor %}
        <a href="/" class="category">Все</a>
      </div>
      {% endif %}

      <div class="grid">
        {% for l in links %}
        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <a href="/r/{{l.id}}" target="_blank"><strong>{{l.title}}</strong></a>
              <div class="meta">{{l.url}}</div>
            </div>
            <div class="small">{{l.created[:10]}}</div>
          </div>
          <div class="notes">{{l.notes}}</div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div class="meta">{{l.category}}</div>
            <div><a class="muted-btn" href="/r/{{l.id}}" target="_blank">Открыть</a></div>
          </div>
        </div>
        {% endfor %}
      </div>

      {% if not links %}
        <p class="small">Ссылки не найдены. Перейдите в <a href="/admin">админ</a>, чтобы добавить.</p>
      {% endif %}
    </main>

    <footer>
      <div class="small">Работает на Flask • Дата: {{now}}</div>
    </footer>
  </div>
</body>
</html>
"""

ADMIN_HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Admin — Link Hub</title>
  <style>
    body{font-family:Inter,system-ui,Segoe UI,Roboto,Arial;background:#071426;color:#eaf3fb;padding:20px}
    .box{max-width:900px;margin:0 auto;background:#071926;padding:20px;border-radius:12px}
    label{display:block;margin-top:8px;font-size:13px}
    input[type=text],textarea,select{width:100%;padding:8px;border-radius:8px;border:1px solid rgba(255,255,255,0.04);background:transparent;color:inherit}
    .row{display:flex;gap:8px}
    .row>div{flex:1}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{padding:8px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.03)}
    .btn{padding:8px 10px;border-radius:8px;border:none}
    .danger{background:#ef4444;color:white}
    .primary{background:#06b6d4;color:#042}
    a{color:#76e3ef}
  </style>
</head>
<body>
  <div class="box">
    <h2>Админ панель</h2>
    <form method="post" action="/admin/add">
      <div class="row">
        <div>
          <label>Название</label>
          <input name="title" required>
        </div>
        <div>
          <label>URL</label>
          <input name="url" required>
        </div>
      </div>
      <label>Категория</label>
      <input name="category">
      <label>Примечание</label>
      <textarea name="notes" rows="2"></textarea>
      <label>Пароль администратора</label>
      <input type="password" name="pass" required>
      <div style="margin-top:10px">
        <button class="btn primary">Добавить</button>
      </div>
    </form>

    <h3>Существующие ссылки</h3>
    <table>
      <tr><th>ID</th><th>Название</th><th>URL</th><th>Категория</th><th>Действия</th></tr>
      {% for l in links %}
      <tr>
        <td>{{l.id}}</td>
        <td>{{l.title}}</td>
        <td><a href="{{l.url}}" target="_blank">{{l.url}}</a></td>
        <td>{{l.category}}</td>
        <td>
          <form method="post" action="/admin/delete" style="display:inline">
            <input type="hidden" name="id" value="{{l.id}}">
            <input type="password" name="pass" placeholder="пароль" required>
            <button class="btn danger">Удалить</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>

    <hr>
    <p class="small">Файл данных: {{data_file}}</p>
    <p class="small">Совет: установите переменную окружения ADMIN_PASSWORD для защиты (по умолчанию "changeme").</p>

  </div>
</body>
</html>
"""


# --- Routes ---
@app.route('/')
def index():
    q = request.args.get('q', '').strip()
    cat = request.args.get('category', '').strip()
    links = load_links()
    filtered = links
    if cat:
        filtered = [l for l in filtered if (l.get('category','') or '').lower() == cat.lower()]
    if q:
        ql = q.lower()
        filtered = [l for l in filtered if ql in l.get('title','').lower() or ql in l.get('notes','').lower() or ql in l.get('url','').lower()]
    categories = sorted(list({l.get('category','') for l in links if l.get('category')}))
    return render_template_string(BASE_HTML, links=filtered, q=q, categories=categories, now=datetime.utcnow().isoformat()[:10])


@app.route('/r/<int:link_id>')
def redirect_link(link_id):
    links = load_links()
    match = next((l for l in links if l.get('id') == link_id), None)
    if not match:
        abort(404)
    # Optionally could increment click counters here
    return redirect(match.get('url'))


@app.route('/admin')
def admin_index():
    links = load_links()
    return render_template_string(ADMIN_HTML, links=links, data_file=os.path.abspath(DATA_FILE))


@app.route('/admin/add', methods=['POST'])
def admin_add():
    pw = request.form.get('pass','')
    if pw != ADMIN_PASSWORD:
        abort(403)
    title = request.form.get('title','').strip()
    url = request.form.get('url','').strip()
    category = request.form.get('category','').strip()
    notes = request.form.get('notes','').strip()
    if not (title and url):
        abort(400)
    # minimal URL normalization
    if not urlparse(url).scheme:
        url = 'https://' + url
    links = load_links()
    new = {"id": next_id(links), "title": title, "url": url, "notes": notes, "category": category, "created": datetime.utcnow().isoformat() + 'Z'}
    links.append(new)
    save_links(links)
    return redirect(url_for('admin_index'))


@app.route('/admin/delete', methods=['POST'])
def admin_delete():
    pw = request.form.get('pass','')
    if pw != ADMIN_PASSWORD:
        abort(403)
    try:
        lid = int(request.form.get('id'))
    except Exception:
        abort(400)
    links = load_links()
    links = [l for l in links if l.get('id') != lid]
    save_links(links)
    return redirect(url_for('admin_index'))


@app.route('/api/links')
def api_links():
    return jsonify(load_links())


if __name__ == '__main__':
    # Run with: python linkhub.py
    app.run(host='0.0.0.0', port=5000, debug=True)
