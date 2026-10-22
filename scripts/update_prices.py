#!/usr/bin/env python3
"""Atualiza data/games.json com os preços em reais (BRL) da Steam Brasil.

Uso:  python scripts/update_prices.py

Lê a lista de jogos em data/watchlist.json, consulta o preço atual de cada um
e grava em data/games.json. O histórico só ganha uma linha nova quando algum
preço muda, então o arquivo cresce devagar.

Só usa a biblioteca padrão do Python (nada para instalar).
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "data" / "watchlist.json"
OUT = ROOT / "data" / "games.json"

BATCH = 20      # jogos por requisição
PAUSE = 2.0     # segundos entre requisições, para não sobrecarregar a loja
TZ = ZoneInfo("America/Sao_Paulo")

# Lojas coletadas. Para somar outra loja, crie uma função parecida com
# fetch_steam() e registre aqui (veja o README).
STORE_NAMES = {"steam": "Steam"}

# Lojas que só ganham um botão com o seu link de afiliado, sem preço no site.
# O link de cada jogo vai em data/watchlist.json, no campo "links".
LINK_STORES = {"nuuvem": "Nuuvem"}


def fetch_steam(appids):
    """Devolve {appid: {price, regular, cut, url}} para os jogos que têm preço."""
    qs = urllib.parse.urlencode({
        "appids": ",".join(str(a) for a in appids),
        "cc": "br",
        "filters": "price_overview",
    })
    req = urllib.request.Request(
        f"https://store.steampowered.com/api/appdetails?{qs}",
        headers={"User-Agent": "baixougame/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.load(resp)

    found = {}
    for appid in appids:
        entry = raw.get(str(appid))
        if not entry or not entry.get("success"):
            continue
        data = entry.get("data")
        if not isinstance(data, dict) or "price_overview" not in data:
            continue  # jogo gratuito ou sem preço na região
        po = data["price_overview"]
        found[appid] = {
            "price": po["final"] / 100,
            "regular": po["initial"] / 100,
            "cut": po["discount_percent"],
            "url": f"https://store.steampowered.com/app/{appid}/",
        }
    return found


def main():
    watchlist = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    previous = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        if not old.get("sample"):  # dados de exemplo não viram histórico real
            previous = {g["appid"]: g for g in old.get("games", [])}

    today = datetime.now(TZ).date().isoformat()
    appids = [item["appid"] for item in watchlist]
    steam = {}
    failed_batches = 0
    batches = [appids[i:i + BATCH] for i in range(0, len(appids), BATCH)]

    for n, batch in enumerate(batches):
        try:
            steam.update(fetch_steam(batch))
        except Exception as exc:  # rede fora, limite de requisições etc.
            failed_batches += 1
            print(f"Falha no lote {n + 1}/{len(batches)}: {exc}", file=sys.stderr)
        if n < len(batches) - 1:
            time.sleep(PAUSE)

    if failed_batches == len(batches):
        print("Nenhum lote funcionou; arquivo mantido como estava.", file=sys.stderr)
        sys.exit(1)

    games = []
    for item in watchlist:
        appid = item["appid"]
        game = previous.get(appid, {"appid": appid, "history": []})
        game["name"] = item["name"]

        links = {k: v for k, v in (item.get("links") or {}).items() if k in LINK_STORES and str(v).startswith(("http://", "https://"))}
        if links:
            game["links"] = links
        else:
            game.pop("links", None)

        stores = {}
        if appid in steam:
            stores["steam"] = steam[appid]
        elif appid in previous and failed_batches:
            stores = game.get("stores", {})  # lote falhou: mantém o último preço
        game["stores"] = stores

        snapshot = {key: info["price"] for key, info in stores.items()}
        history = game.setdefault("history", [])
        if snapshot and (not history or history[-1]["p"] != snapshot):
            history.append({"d": today, "p": snapshot})
        games.append(game)

    games.sort(key=lambda g: g["name"].lower())
    result = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currency": "BRL",
        "sample": False,
        "stores": STORE_NAMES,
        "link_stores": LINK_STORES,
        "games": games,
    }
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    priced = sum(1 for g in games if g["stores"])
    print(f"{priced}/{len(games)} jogos com preço. Salvo em {OUT}.")


if __name__ == "__main__":
    main()
