#!/usr/bin/env python3
"""Gera imagens de capa (1280x720, 16:9) pros posts do blog, localmente via ComfyUI +
FLUX.1-schnell -- 100% gratis, mesma base de edit-engine/generate_images_local.py,
só com dimensões de capa de blog em vez de slide vertical de carrossel.

Requer ComfyUI rodando em localhost:8188.
Uso: python generate_cover_images.py <manifest.json>
Salva em images/covers/<slug>.png
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.parse

COMFYUI_URL = "http://127.0.0.1:8188"
WIDTH, HEIGHT = 1280, 720
STEPS = 4
GUIDANCE = 1.0
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "images", "covers")

WORKFLOW = {
    "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "flux1-schnell-Q4_K_S.gguf"}},
    "2": {"class_type": "DualCLIPLoader", "inputs": {
        "clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors",
        "type": "flux", "device": "default"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "__PROMPT__", "clip": ["2", 0]}},
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
    "6": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["4", 0], "negative": ["7", 0], "latent_image": ["5", 0],
        "seed": 42, "steps": STEPS, "cfg": GUIDANCE, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "__FILENAME__"}},
}


def check_comfyui() -> bool:
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def queue_prompt(workflow: dict) -> str:
    payload = json.dumps({"prompt": workflow, "client_id": "grana-blog-covers"}).encode()
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=payload,
                                  headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["prompt_id"]


def wait_for_prompt(prompt_id: str, timeout: int = 300) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10) as r:
                history = json.loads(r.read())
                if prompt_id in history and history[prompt_id].get("outputs"):
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def get_output_image(prompt_id: str) -> bytes | None:
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10) as r:
        history = json.loads(r.read())
        outputs = history[prompt_id].get("outputs", {})
        for node_output in outputs.values():
            images = node_output.get("images", [])
            if images:
                info = images[0]
                params = f"filename={urllib.parse.quote(info['filename'])}&subfolder={urllib.parse.quote(info.get('subfolder', ''))}&type=output"
                with urllib.request.urlopen(f"{COMFYUI_URL}/view?{params}", timeout=30) as img_r:
                    return img_r.read()
    return None


def main():
    manifest_path = sys.argv[1]
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not check_comfyui():
        print("ERRO: ComfyUI nao esta rodando em localhost:8188")
        sys.exit(1)

    items = json.load(open(manifest_path, encoding="utf-8"))
    print(f"Gerando {len(items)} capas localmente (FLUX.1-schnell, 1280x720, gratis)...")

    for idx, item in enumerate(items):
        slug, prompt = item["slug"], item["prompt"]
        jpg_path = os.path.join(OUTPUT_DIR, f"{slug}.jpg")
        png_path = os.path.join(OUTPUT_DIR, f"{slug}.png")
        if os.path.exists(jpg_path) and os.path.getsize(jpg_path) > 3_000:
            print(f"[{idx+1}/{len(items)}] {slug}: ja existe, pulando")
            continue

        t0 = time.time()
        workflow = json.loads(json.dumps(WORKFLOW))
        workflow["4"]["inputs"]["text"] = prompt
        workflow["6"]["inputs"]["seed"] = 100 + idx
        workflow["9"]["inputs"]["filename_prefix"] = f"grana_cover_{slug}"

        prompt_id = queue_prompt(workflow)
        if not wait_for_prompt(prompt_id, timeout=300):
            print(f"[{idx+1}/{len(items)}] {slug}: TIMEOUT")
            continue
        img_bytes = get_output_image(prompt_id)
        if not img_bytes:
            print(f"[{idx+1}/{len(items)}] {slug}: imagem nao encontrada")
            continue
        with open(png_path, "wb") as f:
            f.write(img_bytes)

        # Converte pra JPEG comprimido -- PNG do FLUX sai grande (500KB-1.2MB), JPEG
        # q:v 4 fica ~10-30% disso, sem perda visível, e página carrega mais rápido
        # (velocidade de página é sinal de ranqueamento do Google).
        subprocess.run(
            ["ffmpeg", "-y", "-i", png_path, "-q:v", "4", jpg_path, "-loglevel", "error"],
            check=True,
        )
        os.remove(png_path)
        print(f"[{idx+1}/{len(items)}] {slug}: ok ({time.time()-t0:.1f}s, {os.path.getsize(jpg_path)//1024}KB)")

    print("Concluido.")


if __name__ == "__main__":
    main()
