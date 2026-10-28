#!/usr/bin/env python3
"""Нейросетевая очистка дублей (DeepFilterNet3): шум комнаты, часть эха.

Нужны torch, torchaudio, deepfilternet и модель DeepFilterNet3
(raw.githubusercontent.com/Rikorose/DeepFilterNet/main/models/DeepFilterNet3.zip).
Запуск: python enhance.py <папка_модели> [ATTEN_DB]
Пишет audio/work/take-*.wav (48 кГц) — их подхватывает process_audio.py.
"""
import os, subprocess, sys
import numpy as np, torch
from df.enhance import enhance, init_df

ROOT = os.path.dirname(os.path.abspath(__file__))
model, state, _ = init_df(sys.argv[1], post_filter=True)
atten = float(sys.argv[2]) if len(sys.argv) > 2 else 24.0   # сколько дБ шума максимум убирать — больше даёт «подводный» звук
sr = state.sr()
os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
for f in sorted(os.listdir(os.path.join(ROOT, "raw"))):
    if not f.endswith(".m4a"):
        continue
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(ROOT, "raw", f), "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = torch.from_numpy(np.frombuffer(raw, np.float32).copy())[None]
    y = enhance(model, state, x, atten_lim_db=atten)[0].numpy().astype(np.float32)
    out = os.path.join(ROOT, "work", f.replace(".m4a", ".wav"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
                    "-c:a", "pcm_f32le", out], input=y.tobytes(), check=True)
    print(f, "->", out)
