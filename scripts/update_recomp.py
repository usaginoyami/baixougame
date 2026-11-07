#!/usr/bin/env python3
"""Coleta estrelas, último push e última release dos projetos da página /recomp/.

Lê o catálogo que o Usagi Game Launcher publica e grava data/recomp-stats.json.
Só GitHub (repos 'gl:' e jogos de fora são ignorados). Usa o GITHUB_TOKEN quando existe.
Se um projeto falhar (rede, limite), mantém o valor antigo dele.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "recomp-stats.json"
CATALOG_URL = os.environ.get(
    "RECOMP_CATALOG_URL",
    "https://raw.githubusercontent.com/usaginoyami/UsagiGameLauncher/main/catalog/catalog.json")
REPO_RE = re.compile(r"^[\w.-]+/[\w.-]+$")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def get(url: str):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "baixougame-recomp-stats",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (403, 429) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(3)
    return None


def fetch(repo: str) -> dict | None:
    info = get(f"https://api.github.com/repos/{repo}")
    if not info:
        return None
    rel = get(f"https://api.github.com/repos/{repo}/releases/latest")
    out = {"stars": info.get("stargazers_count", 0),
           "pushed": info.get("pushed_at") or "",
           "archived": bool(info.get("archived"))}
    if rel:
        out["release"] = rel.get("tag_name") or rel.get("name") or ""
        out["release_date"] = rel.get("published_at") or ""
    return out


def main() -> int:
    with urllib.request.urlopen(urllib.request.Request(CATALOG_URL, headers={"User-Agent": "baixougame"}), timeout=30) as r:
        catalog = json.load(r)
    repos = sorted({g["repo"] for g in catalog.get("games", []) if REPO_RE.match(g.get("repo", ""))})
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8")).get("stats", {})
        except ValueError:
            pass
    stats, falhas = {}, 0

    def work(repo):
        try:
            return repo, fetch(repo), None
        except Exception as e:  # noqa: BLE001 - um projeto ruim não derruba os outros
            return repo, None, e

    with ThreadPoolExecutor(max_workers=6) as ex:
        for repo, data, err in ex.map(work, repos):
            if data:
                stats[repo] = data
            elif repo in old:
                stats[repo] = old[repo]
            if err:
                falhas += 1
                print(f"aviso: {repo}: {err}", file=sys.stderr)
    payload = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stats": dict(sorted(stats.items()))}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(stats)} projetos, {falhas} falhas")
    return 0 if stats else 1


if __name__ == "__main__":
    sys.exit(main())
