#!/usr/bin/env python3
"""Размывает личные данные в записях экрана, отслеживая их по шаблонам в каждом кадре
(текст прокручивается, поэтому фиксированные прямоугольники не годятся).

Шаблоны вырезаются из опорных кадров (REF): (кадр, x, y, w, h, доп. область размытия вниз).
Запуск: python3 video/build/redact.py  → video/src/*-clean.mp4
"""
import os, subprocess, numpy as np, cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
W, H, FPS = 720, 1450, 30

JOBS = {
    "1-bron": [  # ник и имя менеджера в подписи поста
        (0.5, 256, 1104, 168, 36, 0),   # @DDmngK
        (0.5, 40, 1142, 140, 36, 0),    # (Милена)
    ],
    "4-proverka-peresylka": [  # номер в сообщении «администратора» и ники менеджеров
        (6.0, 352, 1252, 232, 32, 0),   # +77005005050 — серый пузырь
        (9.5, 460, 1250, 216, 34, 0),   # — синий пузырь (пересылка)
        (10.5, 458, 650, 218, 34, 0),   # — фиолетовый пузырь
        (10.5, 44, 1060, 436, 36, 40),  # @username_2378 — Милена, + «менеджер» строкой ниже
        (10.5, 44, 1138, 492, 34, 0),   # @ddmngk — Милена, менеджер
        (10.5, 44, 1214, 492, 34, 0),   # @weexxikik — Настя, менеджер
    ],
}
THR = 0.80


def frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()


def main():
    for name, refs in JOBS.items():
        src = os.path.join(SRC, f"{name}.mp4")
        allf = list(frames(src))
        tpls = []
        for t, x, y, w, h, extra in refs:
            g = cv2.cvtColor(allf[int(round(t * FPS))], cv2.COLOR_BGR2GRAY)
            tpls.append((g[y:y + h, x:x + w], extra))
        out = os.path.join(SRC, f"{name}-clean.mp4")
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                                "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
        hits = 0
        for fr in allf:
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            for tp, extra in tpls:
                th, tw = tp.shape
                r = cv2.matchTemplate(g, tp, cv2.TM_CCOEFF_NORMED)
                for _ in range(4):  # одна надпись может быть в кадре несколько раз
                    _, mv, _, (mx, my) = cv2.minMaxLoc(r)
                    if mv < THR:
                        break
                    x0, y0 = max(mx - 6, 0), max(my - 6, 0)
                    x1, y1 = min(mx + tw + 6, W), min(my + th + extra + 6, H)
                    fr[y0:y1, x0:x1] = cv2.GaussianBlur(fr[y0:y1, x0:x1], (0, 0), 9)
                    r[max(my - th, 0):my + th, max(mx - tw, 0):mx + tw] = -1
                    hits += 1
            enc.stdin.write(fr.tobytes())
        enc.stdin.close(); enc.wait()
        print(name, "кадров", len(allf), "размытий", hits)


if __name__ == "__main__":
    main()
