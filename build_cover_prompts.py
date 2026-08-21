#!/usr/bin/env python3
"""Preenche cover-manifest.json com um prompt estruturado pra todo post de content/*.md
que ainda nao tem entrada -- mesmo template validado nas 7 capas ja publicadas (sujeito
unico, fundo preto puro, luz de borda, lente/abertura, "sem texto/logo/pessoas/marca").

Nunca sobrescreve entrada existente. Roda uma vez pra zerar o backlog (2026-08-21); dai
em diante, atualidade.yml e rebuild.yml escrevem a propria entrada pro slug do dia antes
de chamar generate_cover_pollinations.py.

Piscina de sujeitos restrita a objetos sem "superficie rotulavel" natural -- licao real
do FLUX-schnell local (2026-08-16): moeda de ouro virou logo de Bitcoin, relogio de
bolso ganhou nome de marca falso no mostrador. Evitar qualquer coisa com mostrador,
selo, rotulo ou face que convide o modelo a "preencher" um texto.
"""
import json
import re
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
MANIFEST_PATH = ROOT / "cover-manifest.json"

WRAPPER = (
    "product photography of {subject}, centered in frame, sitting on a dark "
    "reflective black surface, deep pure black background, single soft {color} "
    "rim light from upper right edge, studio lighting from the left, {lens}, "
    "sharp focus, high contrast, minimalist, no text, no numbers, no logos, "
    "no people, no brand markings"
)

SUBJECTS = [
    ("an hourglass with sand falling through the middle", "100mm macro lens, f/4"),
    ("a simple metal balance scale with two empty pans", "85mm lens, f/2.8"),
    ("a single brass key", "100mm macro lens, f/4"),
    ("a closed brass padlock", "100mm macro lens, f/4"),
    ("a short stack of plain white ceramic plates", "85mm lens, f/2.8"),
    ("a single piece of dark folded fabric", "85mm lens, f/2.8"),
    ("a spiral seashell", "100mm macro lens, f/4"),
    ("a small pyramid of plain wooden blocks", "85mm lens, f/2.8"),
    ("a single ripple frozen on a still dark water surface", "100mm macro lens, f/4"),
    ("a single water droplet suspended in mid-air", "100mm macro lens, f/2.8"),
    ("a wound spool of plain dark thread", "100mm macro lens, f/4"),
    ("a brass magnifying glass with a plain handle", "85mm lens, f/2.8"),
    ("a plain brass compass, closed", "100mm macro lens, f/4"),
    ("a single closed black umbrella standing upright", "85mm lens, f/2.8"),
    ("a clear glass prism", "100mm macro lens, f/4"),
    ("a small potted plant with a single green sprout", "85mm lens, f/2.8"),
    ("a single folded paper airplane", "85mm lens, f/2.8"),
    ("a single feather", "100mm macro lens, f/4"),
    ("a plain glass marble", "100mm macro lens, f/4"),
    ("a short wooden ladder seen close on two rungs", "85mm lens, f/2.8"),
]

RED_HINTS = (
    "divida", "rotativo", "cheque", "cartao", "parcelamento", "negativad",
    "consignado", "atraso", "vermelho", "escondid", "armadilha", "golpe",
    "credito-tarde", "credito-negativado", "financiamento",
)


def slugify(filename: str) -> str:
    stem = Path(filename).stem
    m = re.match(r"^(\d+)-(.+)$", stem)
    return m.group(2) if m else stem


def pick_color(slug: str) -> str:
    return "red" if any(h in slug for h in RED_HINTS) else "green"


def pick_subject(slug: str):
    idx = int(hashlib.sha1(slug.encode("utf-8")).hexdigest(), 16) % len(SUBJECTS)
    return SUBJECTS[idx]


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    existing = {m["slug"] for m in manifest}

    files = sorted(CONTENT_DIR.glob("*.md"))
    added = []
    for f in files:
        slug = slugify(f.name)
        if slug in existing:
            continue
        subject, lens = pick_subject(slug)
        color = pick_color(slug)
        prompt = WRAPPER.format(subject=subject, color=color, lens=lens)
        manifest.append({"slug": slug, "prompt": prompt})
        added.append(slug)

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Adicionadas {len(added)} entradas novas em cover-manifest.json:")
    for s in added:
        print(" -", s)


if __name__ == "__main__":
    main()
