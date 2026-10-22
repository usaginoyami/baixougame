#!/usr/bin/env python3
"""Cadastra jogos na sua lista manual (data/watchlist.json) a partir do nome.

Uso:
    python scripts/add_game.py "Hades"
    python scripts/add_game.py "Hades; Celeste; Hollow Knight"
    python scripts/add_game.py https://store.steampowered.com/app/1145360/Hades/
    python scripts/add_game.py 1145360

Aceita o nome, o link da página na Steam ou o appid. Vários jogos podem vir
separados por ponto e vírgula. O script procura o jogo na Steam Brasil, confere
que é mesmo um jogo (trilha sonora, DLC e demo ficam de fora) e grava o nome
oficial na watchlist.json. O preço e a capa entram na próxima execução do
update_prices.py (o workflow "Adicionar jogo" já faz isso em seguida).

Se o nome não bater com um único jogo, o script NÃO chuta: mostra as opções
com o appid de cada uma. Rode de novo com o appid ou com o nome exato.

Só usa a biblioteca padrão do Python (nada para instalar).
"""
import json
import re
import sys
import time
import unicodedata
import urllib.parse

import update_prices as up

MAX_CHECK = 6  # quantos resultados da busca conferir por nome digitado


def normalize(text):
    """Minúsculas, sem acento, sem ™®© e sem pontuação: 'Baldur's Gate' == 'baldurs gate'."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[™®©'’`]", "", text.casefold())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_query(text):
    """('appid', n) para link da Steam ou número; ('name', texto) nos demais casos."""
    match = re.search(r"store\.steampowered\.com/app/(\d+)", text)
    if match:
        return "appid", int(match.group(1))
    if re.fullmatch(r"\d{3,}", text):
        return "appid", int(text)
    return "name", text


def search(term):
    """Resultados da busca da loja: [{'id': int, 'name': str}, ...]."""
    qs = urllib.parse.urlencode({"term": term, "cc": "br", "l": "portuguese"})
    raw = up.fetch_json(f"https://store.steampowered.com/api/storesearch/?{qs}")
    items = []
    for item in raw.get("items") or []:
        if isinstance(item, dict) and isinstance(item.get("id"), int) and item.get("name"):
            items.append({"id": item["id"], "name": item["name"]})
    return items


def inspect_app(appid):
    """Dados do app ou None se a Steam não o conhece."""
    raw = up.fetch_json(
        f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=br&l=portuguese"
    )
    entry = raw.get(str(appid)) or {}
    data = entry.get("data")
    if not entry.get("success") or not isinstance(data, dict):
        return None
    return {
        "appid": appid,
        "name": data.get("name") or "",
        "type": data.get("type"),
        "free": bool(data.get("is_free")),
        "priced": "price_overview" in data,
    }


def find_games(term):
    """Procura jogos pelo nome. Devolve (status, lista de dados de app).

    status: 'ok' (um jogo certo), 'ambiguous' (vários possíveis) ou 'none'.
    """
    items = search(term)
    nt = normalize(term)
    exact = [i for i in items if normalize(i["name"]) == nt]
    part = [i for i in items if i not in exact and nt and nt in normalize(i["name"])]
    rest = [i for i in items if i not in exact and i not in part]
    checked = 0

    def games_in(group):
        nonlocal checked
        found = []
        for item in group:
            if checked >= MAX_CHECK:
                break
            checked += 1
            info = inspect_app(item["id"])
            time.sleep(up.PAUSE)
            if info and info["type"] == "game":
                found.append(info)
        return found

    for item in exact:  # nome idêntico: o primeiro que for jogo é o certo
        found = games_in([item])
        if found:
            return "ok", found
    found = games_in(part)
    if len(found) == 1:
        return "ok", found
    if found:
        return "ambiguous", found[:5]
    found = games_in(rest)
    if found:
        return "ambiguous", found[:5]
    return "none", []


def options_text(games):
    return "; ".join(f"{g['name']} (appid {g['appid']})" for g in games)


def process(text, watchlist, discovered, ignored):
    """Cadastra um jogo. Devolve (status, mensagem). Altera as listas recebidas."""
    kind, value = parse_query(text)
    if kind == "appid":
        info = inspect_app(value)
        if not info:
            return "none", f"A Steam não conhece o appid {value}."
        if info["type"] != "game":
            return "rejected", f"{info['name'] or value} (appid {value}) não é um jogo (tipo: {info['type']})."
        status, games = "ok", [info]
    else:
        status, games = find_games(value)

    if status == "none":
        return "none", f'Não achei nenhum jogo para "{text}". Confira o nome ou use o link da Steam.'
    if status == "ambiguous":
        return "ambiguous", (
            f'"{text}" bate com mais de um jogo: {options_text(games)}. '
            "Rode de novo com o appid (ou o nome exato) do jogo certo."
        )

    info = games[0]
    appid = info["appid"]
    name = info["name"] or text
    if info["free"]:
        return "rejected", f"{name} (appid {appid}) é gratuito, então não tem preço para acompanhar."
    if any(item["appid"] == appid for item in watchlist):
        return "exists", f"{name} (appid {appid}) já estava na sua lista."

    watchlist.append({"appid": appid, "name": name})
    notes = []
    if appid in ignored:
        ignored.remove(appid)
        notes.append("estava na lista de ignorados e saiu de lá")
    if any(d["appid"] == appid for d in discovered):
        discovered[:] = [d for d in discovered if d["appid"] != appid]
        notes.append("passou da lista automática para a sua lista")
    if not info["priced"]:
        notes.append("ainda sem preço em reais na Steam")
    extra = f" ({'; '.join(notes)})" if notes else ""
    return "added", f"Adicionado: {name} (appid {appid}){extra}."


def dump_watchlist(items):
    """Um jogo por linha, como o arquivo já é escrito à mão."""
    body = ",\n".join("  " + json.dumps(item, ensure_ascii=False) for item in items)
    up.WATCHLIST.write_text("[\n" + body + "\n]\n", encoding="utf-8")


def main(argv):
    names = []
    for arg in argv:
        names += [p.strip() for p in re.split(r"[;\n]", arg) if p.strip()]
    if not names:
        print(__doc__)
        return 2

    watchlist = up.load_list(up.WATCHLIST)
    discovered = up.load_list(up.DISCOVERED)
    ignored = [int(a) for a in up.load_list(up.IGNORED)]
    before = (len(watchlist), len(discovered), len(ignored))

    lines, failed = [], 0
    for name in names:
        try:
            status, message = process(name, watchlist, discovered, ignored)
        except Exception as exc:  # rede fora, limite da Steam etc.
            status, message = "error", f'Falha ao procurar "{name}": {exc}'
        print(message, file=sys.stderr if status not in ("added", "exists") else sys.stdout)
        lines.append(f"- {message}")
        if status not in ("added", "exists"):
            failed += 1
        time.sleep(up.PAUSE)

    if len(watchlist) != before[0]:
        dump_watchlist(watchlist)
    if len(discovered) != before[1]:
        up.save_json(up.DISCOVERED, discovered)
    if len(ignored) != before[2]:
        up.save_json(up.IGNORED, ignored)

    up.write_summary(["### Cadastro manual"] + lines)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
