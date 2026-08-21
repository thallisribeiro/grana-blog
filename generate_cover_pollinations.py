#!/usr/bin/env python3
"""Gera as imagens de capa que faltam via Pollinations.ai (gratis, sem chave, HTTP puro
-- roda dentro do GitHub Actions, ao contrario do ComfyUI/FLUX local que precisa do PC
ligado). Le cover-manifest.json; pra cada slug cujo images/covers/{slug}.jpg ainda nao
existe, baixa a imagem e salva.

Decisao do usuario (2026-08-21): "quero que ja saia com imagem" -- os posts vinham
saindo sem capa e alguem tinha que rodar o gerador local depois, manualmente. Isso roda
sozinho, antes de generate.py, tanto em atualidade.yml quanto em rebuild.yml.

Falha de rede/API pontual nunca derruba o build inteiro -- pula o post e segue (a capa
fica pendente pro proximo run, generate.py ja trata ausencia de capa graciosamente).
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "cover-manifest.json"
COVERS_DIR = ROOT / "images" / "covers"

WIDTH = 1280
HEIGHT = 720


def fetch(slug: str, prompt: str, attempt: int = 1) -> bool:
    encoded = urllib.parse.quote(prompt)
    # seed fixo por slug (hash simples) -- mesma capa se o script rodar de novo pro
    # mesmo post antes do arquivo existir, em vez de sortear uma imagem diferente a
    # cada retry.
    seed = sum(ord(c) for c in slug) % 100000
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={WIDTH}&height={HEIGHT}&nologo=true&seed={seed}"
    dest = COVERS_DIR / f"{slug}.jpg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "grana-blog-cover-generator/1.0"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        if len(data) < 2000:  # resposta suspeita demais pequena pra ser imagem real
            raise ValueError(f"resposta pequena demais ({len(data)} bytes)")
        COVERS_DIR.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print(f"OK  {slug} ({len(data)} bytes)")
        return True
    except Exception as e:
        if attempt < 2:
            time.sleep(5)
            return fetch(slug, prompt, attempt + 1)
        print(f"FALHOU {slug}: {e} -- pulando, tenta de novo no proximo run")
        return False


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pending = [m for m in manifest if not (COVERS_DIR / f"{m['slug']}.jpg").exists()]
    if not pending:
        print("Todas as capas ja existem -- nada a gerar.")
        return
    print(f"Gerando {len(pending)} capa(s) faltando...")
    ok = 0
    for m in pending:
        if fetch(m["slug"], m["prompt"]):
            ok += 1
    print(f"Concluido: {ok}/{len(pending)} capas geradas.")


if __name__ == "__main__":
    main()
