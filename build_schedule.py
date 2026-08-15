#!/usr/bin/env python3
"""Atribui data de publicacao a cada post que ainda nao tem uma, gravando em
site/publish-schedule.json (nao mexe nos arquivos originais em output/BLOG/ --
mais seguro, reversivel, e outros steps do squad continuam lendo o formato original
sem mudanca). generate.py le esse arquivo pra saber o que ja pode ir ao ar.

Regra de distribuicao (pedido do usuario, 2026-08-14): primeiros 5 posts (ordem
numerica) publicados hoje, os outros ~55 espalhados ao longo de ~2 meses (1/dia).
Autor e fontes tambem entram aqui -- autor e um valor institucional por padrao
(nunca um nome/credencial inventado sem o usuario confirmar quem deve assinar).

Rodar de novo com seguranca: nunca reatribui data de post que ja tem uma (so
preenche o que falta) -- assim dar re-run depois de adicionar posts novos ao
output/BLOG/ so agenda os novos, sem bagunçar o calendario ja publicado.

Uso: python build_schedule.py
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BLOG_DIR = ROOT / "content"  # site/content/ -- ver nota em generate.py (site/ é autocontido)
SCHEDULE_PATH = ROOT / "publish-schedule.json"

DEFAULT_AUTHOR = "Thallis Ribeiro"  # trocado 2026-08-15 (decisão do usuário) -- credenciais reais em generate.py:AUTHOR_INFO, mais forte pra E-E-A-T que autoria institucional genérica
FIRST_BATCH = 5          # quantos posts entram publicados imediatamente (hoje)
SPREAD_DAYS = 60         # janela pra distribuir o resto ("~2 meses")

SOURCE_KEYWORDS = [
    "Banco Central", "BACEN", "IBGE", "Serasa", "SPC", "CNDL", "FGV", "IBRE",
    "CVM", "ANBIMA", "Andima", "Receita Federal", "Senado", "Câmara dos Deputados",
    "Caixa Econômica Federal", "Agência Brasil", "Dieese", "MindMiners",
]

def slugify(filename: str) -> str:
    stem = Path(filename).stem
    m = re.match(r"^(\d+)-(.+)$", stem)
    return m.group(2) if m else stem

def extract_sources(text: str) -> list:
    found = []
    for kw in SOURCE_KEYWORDS:
        if kw.lower() in text.lower() and kw not in found:
            found.append(kw)
    return found

def main():
    schedule = {}
    if SCHEDULE_PATH.exists():
        schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))

    files = sorted(BLOG_DIR.glob("*.md"))
    files = [f for f in files if not f.stem.startswith("_")]

    today = date.today()
    new_slugs = [slugify(f.name) for f in files if slugify(f.name) not in schedule]
    n_new = len(new_slugs)
    print(f"{len(files)} posts no total, {n_new} sem data agendada ainda")

    for i, f in enumerate(files):
        slug = slugify(f.name)
        if slug in schedule:
            continue
        idx_among_new = new_slugs.index(slug)
        if idx_among_new < FIRST_BATCH:
            pub_date = today
        else:
            # espalha o resto ao longo de SPREAD_DAYS, ~1 por dia
            day_offset = 1 + round((idx_among_new - FIRST_BATCH) * SPREAD_DAYS / max(1, n_new - FIRST_BATCH))
            pub_date = today + timedelta(days=day_offset)
        text = f.read_text(encoding="utf-8")
        schedule[slug] = {
            "date": pub_date.isoformat(),
            "author": DEFAULT_AUTHOR,
            "sources": extract_sources(text),
        }

    SCHEDULE_PATH.write_text(json.dumps(schedule, ensure_ascii=False, indent=2), encoding="utf-8")
    dates = sorted(v["date"] for v in schedule.values())
    print(f"Cronograma gravado em {SCHEDULE_PATH}")
    print(f"Primeira data: {dates[0]} | Última data: {dates[-1]}")
    print(f"Publicados hoje ({today.isoformat()}): {sum(1 for v in schedule.values() if v['date'] == today.isoformat())}")

if __name__ == "__main__":
    main()
