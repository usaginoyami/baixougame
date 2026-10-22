#!/usr/bin/env python3
"""Atualiza data/games.json com os preços em reais (BRL) da Steam Brasil.

Uso:  python scripts/update_prices.py

O script faz duas coisas:

1. Descobre jogos novos. Olha as promoções em destaque da Steam Brasil e
   cadastra em data/discovered.json os jogos com desconto grande que ainda
   não estão no site (veja as constantes DISCOVER, MIN_DISCOUNT etc.).
2. Consulta o preço atual de todos os jogos (data/watchlist.json, a sua lista
   manual, mais data/discovered.json) e grava em data/games.json. O histórico
   só ganha uma linha nova quando algum preço muda.

Só usa a biblioteca padrão do Python (nada para instalar).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST = ROOT / "data" / "watchlist.json"    # sua lista manual (você edita)
DISCOVERED = ROOT / "data" / "discovered.json"  # jogos cadastrados pelo script
IGNORED = ROOT / "data" / "ignored.json"        # appids que nunca devem entrar
OUT = ROOT / "data" / "games.json"

BATCH = 20      # jogos por requisição de preço
PAUSE = 2.0     # segundos entre requisições, para não sobrecarregar a loja
TZ = ZoneInfo("America/Sao_Paulo")
USER_AGENT = "baixougame/1.0"

# Descoberta automática de jogos
DISCOVER = True         # False desliga a descoberta
MIN_DISCOUNT = 50       # só cadastra jogos com pelo menos esse desconto (%)
MAX_NEW_PER_RUN = 10    # limite de jogos novos por execução
MAX_GAMES = 300         # limite total de jogos no site (manuais + descobertos)

# Lojas coletadas. Para somar outra loja, crie uma função parecida com
# fetch_steam() e registre aqui (veja o README).
STORE_NAMES = {"steam": "Steam"}

# Lojas que só ganham um botão com o seu link de afiliado, sem preço no site.
# O link de cada jogo vai em data/watchlist.json, no campo "links".
LINK_STORES = {"nuuvem": "Nuuvem"}


def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_steam(appids):
    """Devolve {appid: {price, regular, cut, url}} para os jogos que têm preço."""
    qs = urllib.parse.urlencode({
        "appids": ",".join(str(a) for a in appids),
        "cc": "br",
        "filters": "price_overview",
    })
    raw = fetch_json(f"https://store.steampowered.com/api/appdetails?{qs}")

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


def featured_deals():
    """Promoções em destaque da Steam BR com desconto >= MIN_DISCOUNT.

    Junta todas as listas da vitrine (promoções, mais vendidos, oferta do dia
    etc.) e devolve do maior para o menor desconto.
    """
    raw = fetch_json("https://store.steampowered.com/api/featuredcategories?cc=br&l=portuguese")
    deals = {}
    for source, category in raw.items():
        if not isinstance(category, dict):
            continue
        for item in category.get("items") or []:
            if not isinstance(item, dict) or item.get("type") != 0 or not item.get("discounted"):
                continue
            if item.get("currency") not in (None, "BRL"):
                continue
            cut = item.get("discount_percent") or 0
            appid = item.get("id")
            if cut < MIN_DISCOUNT or not isinstance(appid, int):
                continue
            if appid not in deals or cut > deals[appid]["cut"]:
                deals[appid] = {"appid": appid, "name": item.get("name") or "", "cut": cut, "source": source}
    return sorted(deals.values(), key=lambda d: -d["cut"])


def game_name_if_game(appid):
    """Nome do jogo, ou None se não for um jogo pago (DLC, trilha, demo...)."""
    raw = fetch_json(f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=br&l=portuguese")
    entry = raw.get(str(appid)) or {}
    data = entry.get("data")
    if not entry.get("success") or not isinstance(data, dict):
        return None
    if data.get("type") != "game" or data.get("is_free"):
        return None
    return data.get("name") or ""


def discover(known, ignored, room, today):
    """Devolve a lista de jogos novos a cadastrar (respeitando os limites)."""
    added = []
    for deal in featured_deals():
        if len(added) >= min(MAX_NEW_PER_RUN, room):
            break
        if deal["appid"] in known or deal["appid"] in ignored:
            continue
        try:
            name = game_name_if_game(deal["appid"])
        except Exception as exc:
            print(f"Não consegui conferir o jogo {deal['appid']}: {exc}", file=sys.stderr)
            name = None
        time.sleep(PAUSE)
        if name is None:
            continue  # não é jogo (ou a conferência falhou): fica de fora
        added.append({
            "appid": deal["appid"],
            "name": name or deal["name"],
            "added": today,
            "via": deal["source"],
        })
    return added


def load_list(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def write_summary(lines):
    """Escreve no resumo da execução do GitHub Actions, se estiver rodando lá."""
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target and lines:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def main():
    watchlist = load_list(WATCHLIST)
    discovered = load_list(DISCOVERED)
    ignored = {int(a) for a in load_list(IGNORED)}
    today = datetime.now(TZ).date().isoformat()

    # jogos que você mandou ignorar saem dos descobertos
    kept = [d for d in discovered if d["appid"] not in ignored]
    if len(kept) != len(discovered):
        discovered = kept
        save_json(DISCOVERED, discovered)

    summary = []
    if DISCOVER:
        known = {i["appid"] for i in watchlist} | {d["appid"] for d in discovered}
        room = MAX_GAMES - len(known)
        if room <= 0:
            print(f"Limite de {MAX_GAMES} jogos atingido; descoberta pulada.")
        else:
            try:
                new = discover(known, ignored, room, today)
            except Exception as exc:  # a descoberta nunca derruba a coleta de preços
                print(f"Descoberta falhou (os preços seguem normalmente): {exc}", file=sys.stderr)
                new = []
            if new:
                discovered.extend(new)
                save_json(DISCOVERED, discovered)
                print(f"{len(new)} jogo(s) novo(s) cadastrado(s):")
                summary.append(f"### Jogos novos ({len(new)})")
                for g in new:
                    print(f"  + {g['name']} ({g['appid']})")
                    summary.append(f"- {g['name']} (`{g['appid']}`)")
            else:
                print("Nenhum jogo novo encontrado nas promoções.")

    manual_ids = {i["appid"] for i in watchlist}
    items = list(watchlist) + [d for d in discovered if d["appid"] not in manual_ids]

    previous = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        if not old.get("sample"):  # dados de exemplo não viram histórico real
            previous = {g["appid"]: g for g in old.get("games", [])}

    appids = [item["appid"] for item in items]
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

    if batches and failed_batches == len(batches):
        print("Nenhum lote funcionou; arquivo mantido como estava.", file=sys.stderr)
        sys.exit(1)

    games = []
    for item in items:
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
    save_json(OUT, result)
    priced = sum(1 for g in games if g["stores"])
    print(f"{priced}/{len(games)} jogos com preço. Salvo em {OUT}.")
    write_summary(summary)


if __name__ == "__main__":
    main()
