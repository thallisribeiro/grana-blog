#!/usr/bin/env python3
"""Usa a arte de fundo JA FEITA dos carrosseis (../output/DATA/NN-slug/assets/slide-01.jpg)
como capa do post do blog, em vez de gerar imagem nova. Pedido direto do usuario,
2026-08-21: "tem mt coisa de imagem ja feita pro grana... so precisa que as imagens
conversem com o tema do post" -- as capas geradas via Pollinations, mesmo corrigidas por
palavra-chave, eram abstratas (metafora generica), enquanto o carrossel de cada post ja
tem arte de verdade feita especificamente pro assunto daquele post.

assets/slide-01.jpg e' o fundo LIMPO do slide de abertura (sem texto, sem moldura de
carrossel "@suagrana.app / ARRASTE / 1-8" -- isso so existe em images/slide-01.png, o
slide final composto). Corta pro centro em 16:9 (a composicao do carrossel poe o
assunto principal no meio/topo, o texto entra embaixo na versao final -- um corte
central deixa o assunto na tela quase sempre).

So roda uma vez, manual -- nao entra no pipeline diario (posts futuros do backlog ja
tem carrossel derivado por outro processo antes de chegar aqui; ver nota no README ou
perguntar ao usuario se vale automatizar depois).
"""
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
SQUAD_ROOT = ROOT.parent
OUTPUT_DIR = SQUAD_ROOT / "output"
CONTENT_DIR = ROOT / "content"
COVERS_DIR = ROOT / "images" / "covers"

# Slugs sem carrossel proprio (variantes numeradas de um post que ja existe) --
# reaproveita a arte do post-base listado.
ALIAS = {
    "ordem-certa-prioridades-29": "ordem-certa-prioridades",
    "raiox-nao-e-extrato-30": "raiox-nao-e-extrato",
    "proximo-passo-30": "proximo-passo",
    "custo-sobrevivencia-tutorial-31": "custo-sobrevivencia-tutorial",
}


def slugify(filename: str) -> str:
    stem = Path(filename).stem
    m = re.match(r"^(\d+)-(.+)$", stem)
    return m.group(2) if m else stem


def build_folder_map():
    folder_map = {}
    for p in sorted(OUTPUT_DIR.glob("*/*")):
        if not p.is_dir():
            continue
        m = re.match(r"^\d+-(.+)$", p.name)
        slug = m.group(1) if m else p.name
        asset = p / "assets" / "slide-01.jpg"
        if asset.exists() and slug not in folder_map:
            folder_map[slug] = asset
    return folder_map


def center_crop_16_9(img: Image.Image) -> Image.Image:
    w, h = img.size
    target_h = round(w * 9 / 16)
    if target_h <= h:
        top = (h - target_h) // 2
        return img.crop((0, top, w, top + target_h))
    target_w = round(h * 16 / 9)
    left = (w - target_w) // 2
    return img.crop((left, 0, left + target_w, h))


def main():
    folder_map = build_folder_map()
    files = sorted(CONTENT_DIR.glob("*.md"))
    used, skipped = [], []

    for f in files:
        slug = slugify(f.name)
        source_slug = ALIAS.get(slug, slug)
        asset_path = folder_map.get(source_slug)
        if not asset_path:
            skipped.append(slug)
            continue

        img = Image.open(asset_path).convert("RGB")
        cropped = center_crop_16_9(img)
        cropped = cropped.resize((1280, 720), Image.LANCZOS)
        dest = COVERS_DIR / f"{slug}.jpg"
        cropped.save(dest, "JPEG", quality=88)
        used.append((slug, str(asset_path)))

    print(f"Capas trocadas pela arte do carrossel: {len(used)}")
    for s, p in used:
        print(f"  {s} <- {p}")
    print(f"\nSem arte de carrossel disponivel (mantida a capa anterior): {len(skipped)}")
    for s in skipped:
        print(f"  {s}")


if __name__ == "__main__":
    main()
