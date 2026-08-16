#!/usr/bin/env python3
"""Garante minimo de 2 posts publicados por dia (decisao do usuario, 2026-08-16):
normalmente 1 evergreen (build_schedule.py) + 1 de atualidade (atualidade.yml, roda
antes deste script no rebuild.yml). Se a atualidade pulou hoje (sem noticia boa o
suficiente -- acontece, e é correto pular em vez de forcar post fraco), este script
puxa o PROXIMO post evergreen da fila pra hoje tambem, em vez de deixar o dia com
só 1 post.

Roda em rebuild.yml, depois de build_schedule.py e antes de generate.py.

Nunca mexe em posts "atualidade-*" (esses sao sempre reativos, datados no dia em que
sao escritos -- puxar um deles pra frente nao faz sentido, e nunca teriam data futura
de qualquer forma).
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEDULE_PATH = ROOT / "publish-schedule.json"

def main():
    schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    today_iso = date.today().isoformat()

    atualidade_hoje = any(
        slug.startswith("atualidade-") and v["date"] == today_iso
        for slug, v in schedule.items()
    )
    if atualidade_hoje:
        print("Post de atualidade já saiu hoje -- não precisa puxar evergreen extra.")
        return

    # Acha o próximo evergreen (nunca "atualidade-*") com data futura, pela data mais
    # próxima -- desempate por slug pra ser determinístico entre execuções.
    candidatos = [
        (v["date"], slug) for slug, v in schedule.items()
        if not slug.startswith("atualidade-") and v["date"] > today_iso
    ]
    if not candidatos:
        print("Nenhum evergreen futuro na fila -- nada a puxar (estoque zerado).")
        return

    candidatos.sort()
    proxima_data, slug_escolhido = candidatos[0]
    schedule[slug_escolhido]["date"] = today_iso
    SCHEDULE_PATH.write_text(json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sem atualidade hoje -- puxado '{slug_escolhido}' (era {proxima_data}) pra hoje, garantindo 2 posts no dia.")

if __name__ == "__main__":
    main()
