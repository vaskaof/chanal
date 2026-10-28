#!/usr/bin/env python3
"""Нарезка и обработка озвучки «Кнопки».

Источники (audio/raw/):
  take-A, take-B — первые полные прогоны; take-C — первый перезаписанный финал;
  take-D  — третий полный прогон (здесь появилось «В приложении»);
  take-E  — два дубля финала подряд (E1 — основной: «заполните», «ваш канал»).
  Альтернативные дубли блоков — в audio/alt/.

Цепочка на блок: вырезка с запасом → сокращение длинных пауз (кроссфейд) →
HPF 80 Гц → шумодав → EQ (минус «бубнёж» 250 Гц, плюс разборчивость 3–4 кГц) →
де-эссер → компрессор → темп (atempo, тон не меняется) → громкость −16 LUFS / TP −1.5 дБ.
Запуск: python3 audio/process_audio.py
"""
import json, os, subprocess, numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "raw")
ENH = os.path.join(ROOT, "work")   # дубли после нейросетевой очистки (audio/enhance.py), если есть
SR = 48000
TAKES = {"A": "take-A-1793208292245.m4a", "B": "take-B-1793208487779.m4a", "C": "take-C-1793208584380.m4a",
         "D": "take-D-1793211481739.m4a", "E": "take-E-1793211576134.m4a"}

# (имя, [(дубль, начало, конец), ...], темп) — границы по silencedetect −42 дБ, с запасом.
# Несколько кусков в блоке склеиваются через паузу GAP (громкость кусков выравнивается до склейки).
BLOCKS = [
    ("01-hook",      [("A",  0.70,  5.56)], 1.00),
    ("02-bron",      [("D",  6.50, 10.45), ("A", 9.55, 14.80)], 1.00),  # «В приложении» есть только в D; начало с 6.50 — иначе срезается тихое «в»
    ("03-oplata",    [("A", 15.85, 31.30)], 1.04),
    ("04-statusy",   [("A", 33.60, 42.08)], 1.00),
    ("05-zashchita", [("A", 42.65, 48.78)], 1.00),
    # финал сокращён: «Меня зовут Василий. Я разработал Кнопку.» (A, интонация точки) +
    # «По ссылке… автоматизировать.» (E1). Выпала фраза «приложение, которое автоматизирует…»,
    # которая во всех дублях звучала как «броню… работу заказами».
    ("06-final",     [("A", 49.30, 52.50), ("E", 8.62, 18.15)], 1.04),
]
ALT = [
    ("01-hook-B",      [("B",  0.00,  5.85)], 1.00),
    ("01-hook-D",      [("D",  0.80,  6.15)], 1.00),
    ("02-bron-B",      [("B",  6.55, 15.85)], 1.00),
    ("02-bron-D",      [("D",  6.50, 16.55)], 1.00),
    ("03-oplata-B",    [("B", 16.76, 32.70)], 1.04),
    ("03-oplata-D",    [("D", 17.20, 33.70)], 1.08),
    ("04-statusy-B",   [("B", 33.58, 42.35)], 1.00),
    ("04-statusy-D",   [("D", 34.37, 42.85)], 1.00),
    ("05-zashchita-B", [("B", 43.22, 49.05)], 1.00),
    ("05-zashchita-D", [("D", 43.47, 49.58)], 1.00),
    ("06-final-long-E1", [("E",  0.75, 18.15)], 1.08),
    ("06-final-C",     [("C",  0.65, 17.62)], 1.08),
    ("06-final-D",     [("D", 50.18, 68.39)], 1.08),
    ("06-final-E2",    [("E", 19.42, 38.10)], 1.08),
]
GAP = 0.32

MAX_PAUSE = 0.38   # паузы длиннее — ужимаем до этого значения
XF = 0.015         # кроссфейд на склейке, с

# Подгонка тембра: усреднённый спектр голоса (1/3 окт.) тянем к эталонному спектру мужской речи
# (LTASS, Byrne et al. 1994) на MATCH долю, усиление/ослабление ограничено.
BANDS = [63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000,
         2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500]
LTASS = [-24, -19, -8, -5, -6, -4.4, -3, -2.6, -0.2, 0, -3, -7, -9.8, -11.2, -12.3, -15.2,
         -16, -16.6, -17.7, -18.6, -19.6, -21.3, -21.9, -22.8]
MATCH, GMIN, GMAX = 0.75, -6.0, 8.0

PRE = "highpass=f=75:p=2"
POST = ("deesser=i=0.35:m=0.5:f=0.5,"
        "acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120:knee=4:makeup=2,"
        "aexciter=amount=0.5:drive=4:blend=0:freq=7500:ceil=16000,"
        "acompressor=threshold=-10dB:ratio=6:attack=1:release=40")
CHAIN = None   # собирается в main() после замера спектра


def band_db(x):
    n = 4096; fr = x[:len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((fr ** 2).mean(1)); fr = fr[rms > np.percentile(rms, 40)]
    P = (np.abs(np.fft.rfft(fr * np.hanning(n), axis=1)) ** 2).mean(0); f = np.fft.rfftfreq(n, 1 / SR)
    o = np.array([10 * np.log10(P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-20) for c in BANDS])
    return o - o[BANDS.index(500)]


def match_eq(x, g0=None, y=None):
    """Первый проход: x — сырой голос. Второй: g0 — прошлые усиления, y — голос после всей цепочки."""
    g = MATCH * (np.array(LTASS) - band_db(x)) if g0 is None else g0 + MATCH * (np.array(LTASS) - band_db(y))
    g = np.clip(g, GMIN, GMAX)
    g[:4] = np.minimum(g[:4], 1.5)                    # низ почти не поднимаем — иначе бубнит
    g = np.convolve(np.pad(g, 1, mode="edge"), [0.25, 0.5, 0.25], "valid")
    g -= g[BANDS.index(500):BANDS.index(1250)].mean()  # середину не трогаем, громкость выровняет loudnorm
    entries = ";".join(f"entry({c},{v:.1f})" for c, v in zip(BANDS, g))
    return f"firequalizer=gain_entry='{entries}':delay=0.05:fixed=on", g


def ff(args, data=None):
    return subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, input=data, capture_output=True, check=True).stdout


def src(take):
    e = os.path.join(ENH, TAKES[take].replace(".m4a", ".wav"))
    return e if os.path.exists(e) else os.path.join(RAW, TAKES[take])


def load(path, a, b):
    raw = ff(["-ss", str(a), "-to", str(b), "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    return np.frombuffer(raw, np.float32).copy()


def env_db(x, hop=0.01):
    h = int(SR * hop); n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9), h


def tighten(x, thr=-42.0):
    """Ужимает паузы длиннее MAX_PAUSE: вырезает середину паузы, склейка кроссфейдом."""
    db, h = env_db(x)
    quiet = db < thr
    cuts, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if i > 0 and j < len(quiet) and (j - i) * h / SR > MAX_PAUSE:
                keep = int(MAX_PAUSE * SR / 2)
                cuts.append((i * h + keep, j * h - keep))
            i = j
        else:
            i += 1
    xf = int(XF * SR); out, pos = [], 0
    for a, b in cuts:
        out.append(x[pos:a + xf]); pos = b
    out.append(x[pos:])
    y = out[0]
    ramp = np.linspace(0, 1, xf, dtype=np.float32)
    for seg in out[1:]:
        y = np.concatenate([y[:-xf], y[-xf:] * (1 - ramp) + seg[:xf] * ramp, seg[xf:]])
    removed = sum(b - a for a, b in cuts) / SR
    return y, removed


def speech_rms(x):
    db, h = env_db(x)
    return np.sqrt(np.mean(x[:len(db) * h].reshape(len(db), h)[db > -35] ** 2))


def assemble(parts):
    segs = [load(src(t), a, b) for t, a, b in parts]
    ref = speech_rms(segs[0])
    gap = np.zeros(int(GAP * SR), np.float32)
    x = segs[0]
    for seg in segs[1:]:
        x = np.concatenate([x, gap, seg * (ref / speech_rms(seg))])
    return tighten(x)


def process(name, parts, tempo, outdir):
    y, removed = assemble(parts)
    take = "+".join(t for t, _, _ in parts)
    a, b = parts[0][1], parts[-1][2]
    pcm = y.astype(np.float32).tobytes()
    flt = CHAIN + (f",atempo={tempo}" if tempo != 1.0 else "")
    common = ["-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-"]
    # проход 1: замер громкости после цепочки
    meas = subprocess.run(["ffmpeg", "-v", "info", "-y"] + common +
                          ["-af", flt + ",loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"],
                          input=pcm, capture_output=True).stderr.decode()
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I=-16:TP=-1.5:LRA=7:linear=true:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
    out = os.path.join(outdir, f"{name}.wav")
    ff(common + ["-af", flt + "," + ln + ",aresample=48000,afade=t=in:d=0.03,areverse,afade=t=in:d=0.08,areverse,"
                 "apad=pad_dur=0.12", "-c:a", "pcm_s24le", out], pcm)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                               capture_output=True, text=True).stdout)
    return {"block": name, "take": take, "src": parts, "src_dur": round(sum(q - p for _, p, q in parts), 2),
            "pauses_cut": round(removed, 2), "tempo": tempo, "dur": round(dur, 2)}


def main():
    global CHAIN
    voice = np.concatenate([assemble(p)[0] for _, p, _ in BLOCKS])
    eq, g = match_eq(voice)
    for _ in range(2):  # компрессор и де-эссер сдвигают баланс — доводим по результату цепочки
        out = np.frombuffer(ff(["-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", PRE + "," + eq + "," + POST,
                                "-f", "f32le", "-"], voice.astype(np.float32).tobytes()), np.float32)
        eq, g = match_eq(voice, g, out)
    CHAIN = PRE + "," + eq + "," + POST
    print("EQ, дБ:", dict(zip(BANDS, np.round(g, 1))))
    os.makedirs(os.path.join(ROOT, "alt"), exist_ok=True)
    rep = {"main": [process(*blk, ROOT) for blk in BLOCKS],
           "alt": [process(*blk, os.path.join(ROOT, "alt")) for blk in ALT]}
    # склейка для прослушивания: блоки с паузой 0.35 с
    lst = os.path.join(ROOT, "_concat.txt")
    sil = os.path.join(ROOT, "_gap.wav")
    ff(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.35", "-c:a", "pcm_s24le", sil])
    with open(lst, "w") as f:
        for i, r in enumerate(rep["main"]):
            if i: f.write(f"file '{sil}'\n")
            f.write(f"file '{os.path.join(ROOT, r['block'] + '.wav')}'\n")
    ff(["-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s24le", os.path.join(ROOT, "voice-full.wav")])
    ff(["-i", os.path.join(ROOT, "voice-full.wav"), "-c:a", "libmp3lame", "-b:a", "192k", os.path.join(ROOT, "voice-full.mp3")])
    os.remove(lst); os.remove(sil)
    json.dump(rep, open(os.path.join(ROOT, "blocks.json"), "w"), ensure_ascii=False, indent=1)
    for k in rep:
        for r in rep[k]:
            print(k, r)


if __name__ == "__main__":
    main()
