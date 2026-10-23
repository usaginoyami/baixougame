#!/usr/bin/env python3
"""Gera uma página estática por jogo (jogos/<slug>/index.html) e o sitemap.xml
a partir de data/games.json.

Uso:  python scripts/build_pages.py

Cada página tem título, descrição e prévia de link (Open Graph) próprios, para o
Google e para quando alguém compartilha o endereço. Roda depois de
update_prices.py. Só usa a biblioteca padrão do Python.
"""
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "games.json"
SITE = ROOT / "site.json"
PAGES = ROOT / "jogos"
SERIES_COLORS = ["var(--accent)", "var(--s2)", "var(--s3)"]
FONTS = ("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700"
         "&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&display=swap")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%23ff5566'/%3E"
           "%3Cpath d='M9 21l5-5 4 3 6-8' fill='none' stroke='%23fff' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")

esc = html.escape


def money(n):
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + s


def dmy(s):
    y, m, d = s.split("-")
    return f"{d}/{m}/{y}"


def day_num(s):
    from datetime import date
    y, m, d = map(int, s.split("-"))
    return date(y, m, d).toordinal()


def load_site():
    site = json.loads(SITE.read_text(encoding="utf-8"))
    site["url"] = site["url"].rstrip("/") + "/"
    return site


def analytics_tag(site):
    a = site.get("analytics") or {}
    src = a.get("src") if isinstance(a, dict) else None
    if not src or not str(src).startswith("https://"):
        return ""
    attrs = "".join(f' {esc(k)}="{esc(str(v))}"' for k, v in (a.get("attrs") or {}).items())
    return f'<script defer src="{esc(src)}"{attrs}></script>'


def low_high(game):
    low, high = None, None
    for e in game.get("history", []):
        for key, price in e["p"].items():
            if low is None or price < low[0]:
                low = (price, e["d"], key)
            if high is None or price > high:
                high = price
    return low, high


def chart_svg(game, today, names):
    """Gráfico de degraus do histórico (mesmo desenho da janela do site)."""
    history = game.get("history", [])
    W, H, ml, mr, mt, mb = 640, 240, 64, 14, 12, 28
    pw, ph = W - ml - mr, H - mt - mb
    prices = [p for e in history for p in e["p"].values()]
    lo_p, hi_p = min(prices), max(prices)
    if lo_p == hi_p:
        lo_p = hi_p * 0.8
    raw = (hi_p - lo_p) / 4
    import math
    pow10 = 10 ** math.floor(math.log10(raw))
    f = raw / pow10
    step = (1 if f <= 1 else 2 if f <= 2 else 5 if f <= 5 else 10) * pow10
    lo = max(0, math.floor(lo_p / step) * step)
    hi = math.ceil(hi_p / step) * step
    x0 = day_num(history[0]["d"])
    x_end = max(day_num(history[-1]["d"]), day_num(today))
    span = max(1, x_end - x0)
    X = lambda d: ml + (d - x0) / span * pw
    Y = lambda p: mt + (1 - (p - lo) / (hi - lo)) * ph

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Histórico de preço de {esc(game["name"])} em reais">']
    v = lo
    while v <= hi + step / 2:
        y = Y(v)
        out.append(f'<line class="gridline" x1="{ml}" x2="{W - mr}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="tick" x="{ml - 8}" y="{y + 4:.1f}" text-anchor="end">R$&#160;{v:.0f}</text>')
        v += step
    out.append(f'<line class="ax" x1="{ml}" x2="{W - mr}" y1="{mt + ph}" y2="{mt + ph}"/>')
    from datetime import date
    for frac, anchor in ((0, "start"), (0.5, "middle"), (1, "end")):
        d = date.fromordinal(round(x0 + span * frac))
        out.append(f'<text class="tick" x="{ml + pw * frac:.1f}" y="{H - 8}" text-anchor="{anchor}">{d.day:02d}/{d.month:02d}</text>')
    keys = []
    for e in history:
        for k in e["p"]:
            if k not in keys:
                keys.append(k)
    for i, key in enumerate(keys):
        pts = [(day_num(e["d"]), e["p"][key]) for e in history if key in e["p"]]
        d = f"M{X(pts[0][0]):.1f},{Y(pts[0][1]):.1f}"
        for px, py in pts[1:]:
            d += f" H{X(px):.1f} V{Y(py):.1f}"
        d += f" H{X(x_end):.1f}"
        out.append(f'<path class="series" d="{d}" style="stroke:{SERIES_COLORS[i % 3]}"/>')
    low, _ = low_high(game)
    if low:
        out.append(f'<circle class="dot" cx="{X(day_num(low[1])):.1f}" cy="{Y(low[0]):.1f}" r="5" style="fill:var(--good)"/>')
    out.append("</svg>")
    return "".join(out), keys


def page_html(game, data, site, today):
    names = data.get("stores", {})
    link_names = data.get("link_stores", {})
    name = game["name"]
    stores = sorted(game.get("stores", {}).items(), key=lambda kv: kv[1]["price"])
    low, high = low_high(game)
    history = game.get("history", [])
    url = f'{site["url"]}jogos/{game["slug"]}/'
    cover = f'https://cdn.cloudflare.steamstatic.com/steam/apps/{game["appid"]}/header.jpg'

    if stores:
        k, best = stores[0]
        desc = f'Preço de {name} em reais: {money(best["price"])} na {names.get(k, k)}'
        if best["cut"] > 0:
            desc += f' (−{best["cut"]}%)'
        desc += "."
        if low and len(history) >= 2:
            desc += f' Menor preço registrado: {money(low[0])} em {dmy(low[1])}.'
        desc += " Histórico de preços atualizado todo dia."
    else:
        desc = f"{name}: sem preço em reais nas lojas acompanhadas. Veja o histórico no baixougame."
    title = f'{name}: preço e histórico | {site["name"]}'

    rows = ""
    for i, (key, info) in enumerate(stores):
        flag = '<span class="best-flag">menor preço</span>' if i == 0 and len(stores) > 1 else ""
        link = (f'<a href="{esc(info["url"])}" target="_blank" rel="noopener">Ir à loja</a>'
                if info.get("url", "").startswith(("http://", "https://")) else "")
        rows += (f'<tr class="{"best" if i == 0 and len(stores) > 1 else ""}"><td>{esc(names.get(key, key))}{flag}</td>'
                 f'<td class="num">{money(info["price"])}</td>'
                 f'<td class="num">{money(info["regular"]) if info["cut"] > 0 else "–"}</td>'
                 f'<td class="num">{"−%d%%" % info["cut"] if info["cut"] > 0 else "–"}</td><td>{link}</td></tr>')
    table = (f'<div class="scroll"><table><thead><tr><th>Loja</th><th>Preço</th><th>Preço cheio</th><th>Desconto</th><th></th></tr></thead>'
             f'<tbody>{rows}</tbody></table></div>') if rows else \
        '<p class="note">Este jogo não tem preço em reais nas lojas acompanhadas.</p>'

    if len(history) >= 2:
        svg, keys = chart_svg(game, today, names)
        legend = ""
        if len(keys) > 1:
            legend = '<div class="legend">' + "".join(
                f'<span><i style="background:{SERIES_COLORS[i % 3]}"></i>{esc(names.get(k, k))}</span>' for i, k in enumerate(keys)) + "</div>"
        stats = (f'<div class="stats"><span>Menor preço registrado: <b>{money(low[0])}</b> em {dmy(low[1])} ({esc(names.get(low[2], low[2]))})</span>'
                 f'<span>Maior: <b>{money(high)}</b></span></div>')
        hist = f'{legend}<div class="chart">{svg}</div>{stats}'
    else:
        first = dmy(history[0]["d"]) if history else "breve"
        hist = f'<p class="note">O histórico deste jogo começa em {first}. As variações de preço aparecem aqui conforme forem acontecendo.</p>'

    link_items = [(k, u) for k, u in (game.get("links") or {}).items() if str(u).startswith(("http://", "https://"))]
    links = ""
    if link_items:
        btns = "".join(f'<a class="linkbtn" href="{esc(u)}" target="_blank" rel="sponsored noopener">Ver na {esc(link_names.get(k, k))}</a>' for k, u in link_items)
        links = (f'<div><h3>Ver também em</h3><div class="links">{btns}</div>'
                 '<p class="links-note">Link de afiliado. O preço não aparece aqui, confira na loja.</p></div>')

    ld = {"@context": "https://schema.org", "@type": "Product", "name": name, "image": cover, "url": url}
    if stores:
        k, best = stores[0]
        ld["offers"] = {"@type": "Offer", "priceCurrency": "BRL", "price": f'{best["price"]:.2f}',
                        "availability": "https://schema.org/InStock", "url": best.get("url") or url}
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")

    aff = ('<p class="foot">Alguns botões levam a lojas parceiras por links de afiliado. Se você comprar por eles, '
           'o baixougame pode receber uma comissão, sem custo extra para você.</p>') if link_items else ""

    return f"""<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(site["name"])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(cover)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="../../style.css">
<script type="application/ld+json">{ld_json}</script>

<header class="bar">
  <div class="gutter">
    <a class="logo" href="../../" aria-label="baixougame, página inicial">baixou<span>game</span></a>
    <span class="cur" title="Preços em reais">R$<small>BRL</small></span>
  </div>
</header>

<main class="gutter">
  <p class="crumb"><a href="../../">← Todos os jogos</a></p>
  <article class="page">
    <span class="cover"><img src="{esc(cover)}" alt="" width="460" height="215" referrerpolicy="no-referrer"></span>
    <div class="dbody">
      <h1>{esc(name)}</h1>
      <div><h3>Preço por loja</h3>{table}</div>
      {links}
      <div><h3>Histórico de preço</h3>{hist}</div>
    </div>
  </article>
  <p class="foot">Preços atualizados em {dmy(today)}. Podem mudar a qualquer momento; confira o valor final na página da loja antes de comprar. Projeto independente, sem vínculo com as lojas listadas. A capa pertence ao seu dono.</p>
  {aff}
</main>
{analytics_tag(site)}
</html>
"""


def sitemap(site, data, today):
    urls = [site["url"]] + [f'{site["url"]}jogos/{g["slug"]}/' for g in data["games"]]
    body = "".join(f"  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}</urlset>\n')


def main():
    if not DATA.exists():
        print("data/games.json não existe; rode update_prices.py antes.", file=sys.stderr)
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    games = [g for g in data.get("games", []) if g.get("slug")]
    if data.get("sample") or not games:
        print("Dados de exemplo ou sem slug; nenhuma página gerada.")
        return 0
    data["games"] = games
    site = load_site()
    today = data["updated"][:10]
    # a data exibida segue o horário de Brasília
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        today = datetime.fromisoformat(data["updated"]).astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    except Exception:
        pass

    wanted = {g["slug"] for g in games}
    if PAGES.exists():
        for d in PAGES.iterdir():
            if d.is_dir() and d.name not in wanted:
                shutil.rmtree(d)  # jogo que saiu do site perde a página
    for g in games:
        out = PAGES / g["slug"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(page_html(g, data, site, today), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(sitemap(site, data, today), encoding="utf-8")
    (ROOT / "robots.txt").write_text(f'User-agent: *\nAllow: /\n\nSitemap: {site["url"]}sitemap.xml\n', encoding="utf-8")
    print(f"{len(games)} página(s) gerada(s) em {PAGES} e sitemap.xml atualizado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
