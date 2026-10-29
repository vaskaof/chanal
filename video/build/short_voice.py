#!/usr/bin/env python3
"""Короткий ролик «Кнопки» под озвучку (≤ 60 с): 1920×1080 и 1080×1920.

Раскадровка привязана к таймингам audio/voice-full.wav:
  хук (анимированная карточка) → бронь → оплата → коллективка → проверка аккаунта → финал (анимированная карточка).
Субтитры по фразам озвучки, метка «Со звуком» первые 2 с.

Источники экрана (video/src):
  1-bron.mp4, 4-proverka-peresylka-clean.mp4 — записи телефона (в «проверке» размыт номер, build/redact.py);
  cc/01-oplata…, cc/02-kollektivka… — записи приложения (оплата клиент + менеджер, этап коллективки).

Запуск: python3 video/build/short_voice.py   (нужны ffmpeg, node + playwright, npm i в video/build)
"""
import json, os, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "video")
B = os.path.join(V, "build")
OUT = os.path.join(B, "out")
FIN = os.path.join(V, "final")
SRC = os.path.join(V, "src")
AUDIO = os.path.join(ROOT, "audio", "voice-full.wav")
for d in (OUT, FIN):
    os.makedirs(d, exist_ok=True)

# --- бренд: всё, что может поменяться, — здесь
PRODUCT = "Кнопка"
CHANNEL = "Неручной режим"
CONTACT = "@vaskaof"
AUTHOR = "Василий Коровин"
# палитра и шрифты — как в презентации (deck) и прошлых роликах
BG, INK = "#14202B", "#F6F4EF"
ACCENT = "#FF6B3D"        # заливки; текст на них — цвет фона BG
ACCENT_TX = "#FF6B3D"
MUTED = "#C9D1D9"
CARD = "#1E2C39"
FPS = 30
TAIL = 0.85               # финальная карточка держится после конца голоса (ролик ≤ 60 с)

# --- тайминг блоков озвучки (из audio/blocks.json: блоки подряд с паузой 0.35 с)
GAP = 0.35
_blocks = json.load(open(os.path.join(ROOT, "audio", "blocks.json")))["main"]
T0, t = {}, 0.0
for r in _blocks:
    T0[r["block"]] = t
    t += r["dur"] + GAP
VOICE_END = t - GAP
DUR = {}
names = [r["block"] for r in _blocks]
for i, n in enumerate(names):
    DUR[n] = (T0[names[i + 1]] if i + 1 < len(names) else VOICE_END + TAIL) - T0[n]
TOTAL = VOICE_END + TAIL

# --- субтитры: (начало, конец, текст), абсолютное время; по словам из распознавания voice-full.wav
SUBS = [
    (0.00, 1.75, "Чем больше у байера заказов —"),
    (1.82, 5.05, "тем больше времени уходит на&nbsp;переписки, оплаты и&nbsp;учёт"),
    (5.50, 8.24, "В приложении клиент просто нажимает кнопку —"),
    (8.24, 9.45, "и бронь за ним."),
    (9.55, 11.40, "Мест нет — он в очереди."),
    (11.60, 13.25, "Вам не нужно разбирать комментарии"),
    (13.25, 15.00, "и выяснять, кто был первым."),
    (15.28, 16.60, "Партия приехала —"),
    (16.66, 19.30, "клиент сам видит, сколько доплатить за&nbsp;вес."),
    (19.45, 20.95, "Например, 1&nbsp;300&nbsp;₽."),
    (21.40, 23.60, "Переводит, прикрепляет чек —"),
    (23.80, 25.45, "вам приходит заявка."),
    (25.70, 27.20, "Проверили, подтвердили —"),
    (27.20, 28.90, "и долг пересчитался сам."),
    (29.00, 31.70, "Без поиска чеков по&nbsp;перепискам."),
    (31.80, 34.04, "С коллективками та же история."),
    (34.17, 35.69, "Обновили статус один раз —"),
    (35.69, 38.04, "и все участники видят, где их заказ."),
    (38.09, 40.64, "И никому не надо объяснять отдельно."),
    (40.83, 43.69, "А если клиенту пишет мошенник от&nbsp;вашего имени —"),
    (43.79, 45.09, "бот проверит аккаунт"),
    (45.09, 47.19, "и подскажет, что это не вы."),
    (47.50, 48.80, "Меня зовут Василий."),
    (48.90, 50.25, "Я разработал «Кнопку»."),
    (50.38, 52.95, "По ссылке можно посмотреть, как она работает."),
    (53.12, 54.65, "А если заполните анкету —"),
    (54.72, 56.25, "я бесплатно разберу ваш канал"),
    (56.30, 59.10, "и покажу, что можно упростить и&nbsp;автоматизировать."),
]

# --- геометрия
FMT = {
    "W": dict(cw=1920, ch=1080, SW=430, SH=900, px=1260, py=118, bz=14, r=44, bh=50,
              colx=110, colw=960, eb_y=150, title_fs=58,
              sub=dict(x=110, y=740, w=980, h=270, fs=54, align="left", va="flex-end")),
    "V": dict(cw=1080, ch=1920, SW=540, SH=1130, px=270, py=410, bz=16, r=56, bh=50,
              colx=70, colw=940, eb_y=120, title_fs=50,
              sub=dict(x=50, y=1572, w=980, h=150, fs=50, align="center", va="flex-start")),
}
ROLE = {"L": "Ваш клиент", "R": "Вы"}

SOURCES = {
    "TB": "1-bron.mp4",
    "TP": "4-proverka-peresylka-clean.mp4",
    "A1": "cc/01-oplata-klient-i-menedzher-1080x1920.mp4",
    "A2": "cc/02-kollektivka-etap-1080x1920.mp4",
}
# записи приложения 1080×1920: экран телефона — полоса 888 px по центру
PRECROP = {"A1": "crop=888:1858:96:31,", "A2": "crop=888:1858:96:31,"}


def S(src, a, b, d, side="L"):
    """Кусок экрана: источник, отрезок [a, b] исходника, длительность в ролике, чей экран."""
    return dict(src=src, a=a, b=b, d=d, side=side)


# Раскадровка. Комментарии — какая фраза озвучки идёт поверх куска (время от начала сцены).
SCENES = [
    dict(id="02-bron", eb="01 · Бронь", title="Бронь — кнопкой. Мест&nbsp;нет — очередь", segs=[
        S("TB", 0.15, 3.90, 3.75),      # «нажимает кнопку — и бронь за ним»: «Место №2 из 50 — ваше!»
        S("TB", 7.60, 9.60, 2.00),      # «Мест нет — он в очереди»: «вы №1 в листе ожидания»
        S("TB", 24.0, 28.6, None),      # «не нужно выяснять, кто был первым»: список броней в боте
    ]),
    dict(id="03-oplata", eb="02 · Оплата", title="Чек приходит заявкой — вы&nbsp;подтверждаете", segs=[
        S("A1", 0.00, 1.60, 1.40),        # «Партия приехала»: «К оплате: 1 300 ₽», открывает заказ
        S("A1", 2.00, 2.90, 1.00),        # «клиент сам видит…»: заказ, вес 0 / 1 300
        S("A1", 3.70, 6.90, 3.30),        # «…сколько доплатить за вес. Например, 1 300»: «1 300 ₽ осталось»
        S("A1", 9.60, 12.0, 2.20),        # «Переводит, прикрепляет чек»: сумма 1 300, чек
        S("A1", 16.7, 17.4, 0.65),        # отправил
        S("A1", 20.8, 23.0, 1.85, "R"),   # «вам приходит заявка»
        S("A1", 24.0, 24.95, 0.80, "R"),  # «Проверили»: чек 1 300 ₽
        S("A1", 29.0, 30.3, 1.10, "R"),   # «подтвердили»
        S("A1", 34.2, 36.6, 2.10, "R"),   # «долг пересчитался сам»: Соня 2 200 → 900 ₽
        S("A2", 2.80, 5.20, None),        # «без поиска чеков»: у клиента «всё оплачено»
    ]),
    dict(id="04-statusy", eb="03 · Коллективка", title="Один статус — видят все&nbsp;участники", segs=[
        S("A2", 3.00, 4.90, 1.90),        # «с коллективками та же история»: у клиента «Формируется»
        S("A2", 7.70, 8.50, 0.70, "R"),   # коллективка на 5 заказов
        S("A2", 14.6, 15.9, 1.10, "R"),   # «обновили статус»: «Отправлено (СДЭК)»
        S("A2", 20.3, 21.4, 0.90, "R"),   # «один раз»: «будет установлен для 5 из 5 заказов»
        S("A2", 21.8, 22.7, 0.80, "R"),   # «Статус изменён у 5 заказов»
        S("A2", 26.0, 29.4, None),        # «все видят, где их заказ»: «Едет в Россию»
    ]),
    dict(id="05-zashchita", eb="04 · Проверка аккаунта", title="Бот сверяет аккаунт с&nbsp;официальным списком", segs=[
        S("TP", 5.35, 7.60, 2.60),        # «пишет мошенник от вашего имени» (экран чата — с 5.3 с)
        S("TP", 1.00, 2.20, 1.20),        # «бот проверит аккаунт»: «Проверить продавца»
        S("TP", 9.40, 10.6, 1.20),        # пересылка → «Это ДРУГОЙ аккаунт»
        S("TP", 10.6, 14.6, None),        # «подскажет, что это не вы»
    ]),
]

ov_items = []


def ov(name, w, h, html, transparent=True, frames=None):
    f = os.path.join(OUT, f"{name}.png")
    it = dict(file=f, w=w, h=h, html=html, transparent=transparent)
    if frames:
        it["frames"] = frames
    ov_items.append(it)
    return f


def glow(fmt):
    pos = "75% 40%" if fmt == "W" else "50% 45%"
    return (f'<div style="position:absolute;inset:0;background:radial-gradient(circle at {pos}, '
            f'rgba(255,107,61,.18) 0%, rgba(20,32,43,0) 58%)"></div>')


def bezel(x, y, w, h, bz, r):
    return (f'<div style="position:absolute;left:{x-bz}px;top:{y-bz}px;width:{w+2*bz}px;height:{h+2*bz}px;'
            f'border-radius:{r+bz}px;background:#0A1118;border:2px solid #33475A;box-shadow:0 30px 80px rgba(0,0,0,.45)"></div>')


def scene_bg(fmt, eb, title):
    g = FMT[fmt]
    head = (f'<div style="position:absolute;left:{g["colx"]}px;top:{g["eb_y"]}px;width:{g["colw"] if fmt=="V" else 1040}px">'
            f'<p style="font-size:{26 if fmt=="W" else 28}px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:{ACCENT_TX}">{eb}</p>'
            f'<p class="u" style="margin-top:18px;font-size:{g["title_fs"]}px;font-weight:700;line-height:1.14">{title}</p></div>')
    brand = (f'<p class="u" style="position:absolute;left:{g["colx"]}px;top:{48 if fmt=="W" else 60}px;font-size:24px;'
             f'font-weight:700;color:#7E8B98">{PRODUCT}</p>') if fmt == "W" else ""
    return glow(fmt) + bezel(g["px"], g["py"], g["SW"], g["SH"], g["bz"], g["r"]) + head + brand


def badge(text, bh):
    return (f'<div style="display:flex;justify-content:center;align-items:center;width:360px;height:{bh}px">'
            f'<span style="background:{ACCENT};color:{BG};font-size:{int(bh*0.52)}px;font-weight:800;padding:0 26px;'
            f'height:{bh}px;line-height:{bh}px;border-radius:{bh//2}px">{text}</span></div>')


def sub_html(fmt, text):
    s = FMT[fmt]["sub"]
    return (f'<div style="width:{s["w"]}px;height:{s["h"]}px;display:flex;flex-direction:column;justify-content:{s["va"]};'
            f'text-align:{s["align"]}"><p style="font-size:{s["fs"]}px;font-weight:800;line-height:1.2;'
            f'text-shadow:0 3px 14px rgba(0,0,0,.8),0 0 2px rgba(0,0,0,.9)">{text}</p></div>')


def sound_html():
    return (f'<div style="display:flex;justify-content:flex-end;width:300px;height:64px"><span style="background:rgba(10,17,24,.85);'
            f'border:2px solid {ACCENT};color:{INK};font-size:28px;font-weight:800;padding:0 24px;height:64px;line-height:60px;'
            f'border-radius:32px">🔊 Со звуком</span></div>')


def mask(w, h, r):
    return f'<div style="width:{w}px;height:{h}px;background:#fff;border-radius:{r}px"></div>'


# ---------- анимированные карточки (покадрово: window.setT(t))
ANIM_JS = """
<script>
const ease = x => x<0?0:x>1?1:1-Math.pow(1-x,3);
window.setT = t => {
  document.querySelectorAll('[data-in]').forEach(el => {
    const a = +el.dataset.in, o = el.dataset.out ? +el.dataset.out : 1e9, d = +(el.dataset.d || 0.35);
    let k = ease((t - a) / d) * (1 - ease((t - o) / 0.3));
    const dim = el.dataset.dim ? +el.dataset.dim : null;
    if (dim !== null && t > dim) k *= 1 - 0.65 * ease((t - dim) / 0.6);
    const m = el.dataset.m || 'up';
    const p = ease((t - a) / d);
    el.style.opacity = k;
    el.style.transform = m === 'pop' ? `scale(${0.85 + 0.15*p})` : m === 'left' ? `translateX(${(1-p)*-40}px)` : `translateY(${(1-p)*30}px)`;
  });
  document.querySelectorAll('[data-count]').forEach(el => {
    const [f, to, a, b] = el.dataset.count.split(',').map(Number);
    const x = Math.max(0, Math.min(1, (t - a) / (b - a)));
    el.textContent = Math.round(f + (to - f) * x * x);
  });
  const fo = document.getElementById('fadeout');
  if (fo) { const a = +fo.dataset.at; fo.style.opacity = Math.max(0, Math.min(1, (t - a) / 0.3)); }
};
</script>"""

BUBBLES = ["Бронь!", "Я первая была 🙋", "Оплатила, вот чек", "Сколько доплатить за вес?", "Где мой заказ?",
           "Чек дошёл?", "Бронь 2 шт", "Когда отправка?", "Можно ещё одну?", "Скинула 1 300 ₽",
           "Почему долг не списали?", "Что с коллективкой?", "Куда переводить?", "Есть место?"]


def hook_html(fmt, dur):
    W = fmt == "W"
    # пузыри переписки: учащаются с ростом счётчика заказов, потом приглушаются
    times = [0.15 + 1.7 * (i / len(BUBBLES)) ** 0.75 for i in range(len(BUBBLES))]
    if W:
        cols = [(900, 120), (1330, 170)]
        pos = [(cols[i % 2][0] + (i * 37) % 60, cols[i % 2][1] + (i // 2) * 118) for i in range(len(BUBBLES))]
    else:
        pos = [((60 if i % 2 == 0 else 520) + (i * 29) % 50, 560 + (i // 2) * 96) for i in range(len(BUBBLES))]
    bub = "".join(
        f'<div data-in="{t:.2f}" data-m="pop" data-d="0.2" data-dim="1.9" style="position:absolute;left:{x}px;top:{y}px;opacity:0;'
        f'display:flex;gap:12px;align-items:center;background:#22303D;border:1px solid #33475A;border-radius:22px;padding:12px 20px">'
        f'<span style="width:38px;height:38px;border-radius:19px;background:{["#3B82F6","#E25F9B","#22A06B","#F59E0B","#8B5CF6"][i%5]};flex:none"></span>'
        f'<span style="font-size:{30 if W else 30}px;font-weight:700;white-space:nowrap">{txt}</span></div>'
        for i, ((x, y), t, txt) in enumerate(zip(pos, times, BUBBLES)))
    lx, top = (110, 150) if W else (70, 150)
    pills = "".join(
        f'<div data-in="{t}" data-m="left" data-d="0.3" style="opacity:0;display:flex;align-items:center;gap:20px">'
        f'<span style="width:12px;height:{70 if W else 64}px;border-radius:6px;background:{ACCENT}"></span>'
        f'<span class="u" style="font-size:{72 if W else 66}px;font-weight:800">{w}</span></div>'
        for w, t in (("Переписки", 3.10), ("Оплаты", 3.66), ("Учёт", 4.22)))
    left = (f'<div style="position:absolute;left:{lx}px;top:{top}px;width:{860 if W else 940}px">'
            f'<p data-in="0" data-d="0.3" style="font-size:28px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:{ACCENT_TX}">Байерам и посредникам</p>'
            f'<div data-in="0" data-d="0.3" style="margin-top:22px;display:flex;align-items:baseline;gap:24px">'
            f'<span style="font-size:{40 if W else 40}px;font-weight:700;color:{MUTED}">Заказов:</span>'
            f'<span class="u" data-count="12,148,0.1,1.7" style="font-size:{140 if W else 130}px;font-weight:800;line-height:1">12</span></div>'
            f'<p data-in="1.85" style="opacity:0;margin-top:{26 if W else 18}px;font-size:{40 if W else 40}px;font-weight:700;color:{MUTED}">⏱ Время уходит на:</p>'
            f'<div style="margin-top:18px;display:flex;flex-direction:column;gap:{14 if W else 12}px">{pills}</div></div>')
    if not W:  # на вертикали «время уходит на» и тезисы — под пузырями
        left = (f'<div style="position:absolute;left:{lx}px;top:{top}px;width:940px">'
                f'<p data-in="0" data-d="0.3" style="font-size:28px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:{ACCENT_TX}">Байерам и посредникам</p>'
                f'<div data-in="0" data-d="0.3" style="margin-top:22px;display:flex;align-items:baseline;gap:24px">'
                f'<span style="font-size:40px;font-weight:700;color:{MUTED}">Заказов:</span>'
                f'<span class="u" data-count="12,148,0.1,1.7" style="font-size:130px;font-weight:800;line-height:1">12</span></div></div>'
                f'<div style="position:absolute;left:{lx}px;top:1240px;width:940px">'
                f'<p data-in="1.85" style="opacity:0;font-size:40px;font-weight:700;color:{MUTED}">⏱ Время уходит на:</p>'
                f'<div style="margin-top:14px;display:flex;gap:26px;flex-wrap:wrap">{pills}</div></div>')
    fade = f'<div id="fadeout" data-at="{dur-0.3:.2f}" style="position:absolute;inset:0;background:{BG};opacity:0"></div>'
    return glow(fmt) + bub + left + fade + ANIM_JS


def outro_html(fmt, dur, phone):
    """Финал. Время — от начала блока финала. Фразы: «Меня зовут Василий» 0.2, «Я разработал Кнопку» 1.7,
    «По ссылке… как она работает» 3.2–5.6, «А если заполните анкету» 6.0, «бесплатно разберу» 7.6, «покажу…» 9.3."""
    W = fmt == "W"
    x0 = 110 if W else 70
    wcol = 960 if W else 940
    # фаза A: кто я (как слайд «Кто делает» в презентации)
    a = (f'<div style="position:absolute;left:{x0}px;top:{230 if W else 380}px;width:{wcol}px">'
         f'<p data-in="0.05" data-out="2.9" style="opacity:0;font-size:26px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{ACCENT_TX}">Кто делает</p>'
         f'<p class="u" data-in="0.15" data-out="2.9" style="opacity:0;margin-top:30px;font-size:{100 if W else 88}px;font-weight:700;line-height:1.05">{AUTHOR}</p>'
         f'<div data-in="1.55" data-out="2.9" style="opacity:0;margin-top:40px;display:flex;flex-direction:column;align-items:flex-start;gap:20px">'
         f'<p style="font-size:{44 if W else 42}px;font-weight:700;line-height:1.25;color:{MUTED}">Разработал</p>'
         f'<p style="background:{ACCENT};color:{BG};font-size:{56 if W else 54}px;font-weight:800;padding:26px 44px;border-radius:28px;'
         f'box-shadow:0 24px 60px rgba(255,107,61,.35)"><span class="u">{PRODUCT}</span></p></div></div>')
    # фаза B: демо по ссылке (телефон с записью — накладывается в ffmpeg)
    g = phone
    b = (f'<div style="position:absolute;left:{x0}px;top:{230 if W else 150}px;width:{780 if W else wcol}px">'
         f'<p data-in="2.95" data-out="5.55" style="opacity:0;font-size:28px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:{ACCENT_TX}">Как это работает</p>'
         f'<p class="u" data-in="3.05" data-out="5.55" style="opacity:0;margin-top:22px;font-size:{72 if W else 64}px;font-weight:800;line-height:1.1">Демо — по&nbsp;ссылке в&nbsp;посте</p>'
         f'<p data-in="3.4" data-out="5.55" style="opacity:0;margin-top:28px;display:inline-block;background:{ACCENT};color:{BG};'
         f'font-size:{38 if W else 36}px;font-weight:800;padding:16px 30px;border-radius:22px">▶ Посмотрите глазами клиента</p></div>'
         f'<div data-in="2.9" data-out="5.55" style="opacity:0;position:absolute;left:0;top:0">'
         f'{bezel(g["x"], g["y"], g["w"], g["h"], g["bz"], g["r"])}</div>')
    # фаза C: анкета → разбор
    steps = [("5.8", "Заполните анкету — ссылка в&nbsp;посте"), ("7.4", "Бесплатно разберу ваш&nbsp;канал"),
             ("8.95", "Покажу, что упростить и&nbsp;автоматизировать")]
    # как слайд CTA в презентации: шаги с оранжевой чертой сверху
    if W:
        st = '<div style="display:flex;gap:28px;margin-top:40px">' + "".join(
            f'<div data-in="{t}" style="opacity:0;flex:1;border-top:4px solid {ACCENT};padding-top:26px">'
            f'<p class="u" style="font-size:48px;font-weight:700;color:{ACCENT_TX}">{i+1}</p>'
            f'<p style="margin-top:12px;font-size:42px;font-weight:700;line-height:1.3">{txt}</p></div>'
            for i, (t, txt) in enumerate(steps)) + '</div>'
    else:
        st = "".join(
            f'<div data-in="{t}" style="opacity:0;border-top:4px solid {ACCENT};padding-top:22px;margin-top:34px;display:flex;gap:26px;align-items:baseline">'
            f'<p class="u" style="font-size:48px;font-weight:700;color:{ACCENT_TX}">{i+1}</p>'
            f'<p style="font-size:42px;font-weight:700;line-height:1.3">{txt}</p></div>'
            for i, (t, txt) in enumerate(steps))
    c = (f'<div style="position:absolute;left:{x0}px;top:{150 if W else 330}px;width:{1700 if W else wcol}px">'
         f'<p class="u" data-in="5.7" style="opacity:0;font-size:{64 if W else 60}px;font-weight:700;line-height:1.15">Бесплатный разбор вашего канала</p>'
         f'{st}'
         f'<div data-in="10.4" data-m="pop" style="opacity:0;margin-top:{48 if W else 70}px;display:flex;gap:28px;align-items:center;flex-wrap:wrap">'
         f'<p style="background:{ACCENT};color:{BG};font-size:{38 if W else 36}px;font-weight:800;padding:24px 40px;border-radius:24px">Написать: {CONTACT}</p>'
         f'<p style="font-size:30px;font-weight:600;color:{MUTED}">Анкета и демо — ссылки в посте</p></div></div>')
    fadein = (f'<div id="fadein" style="position:absolute;inset:0;background:{BG};pointer-events:none"></div>'
              '<script>const _st=window.setT;window.setT=t=>{_st(t);document.getElementById("fadein").style.opacity=Math.max(0,1-t/0.25);}</script>')
    return glow(fmt) + a + b + c + ANIM_JS + fadein


# ---------- сборка сцен с экраном
def fit(segs, total):
    """Последний кусок добирает остаток; скорость ограничена 0.8–1.25, нехватку закрываем стоп-кадром."""
    rest = total - sum(s["d"] for s in segs if s["d"])
    out, t0 = [], 0.0
    for s in segs:
        s = dict(s)
        if s["d"] is None:
            s["d"] = round(rest, 3)
        s["sp"] = max(0.8, min(1.25, (s["b"] - s["a"]) / s["d"])) if s["b"] > s["a"] else 1.0
        s["t0"] = t0
        t0 += s["d"]
        out.append(s)
    return out


def en(a, b):
    return f"enable='between(t,{a:.3f},{b:.3f})'"


def render_scene(sc, fmt):
    g = FMT[fmt]
    T = DUR[sc["id"]]
    segs = fit(sc["segs"], T)
    args, fc, idx = [], [], 0

    def img(path):
        nonlocal idx
        args.extend(["-loop", "1", "-framerate", str(FPS), "-t", f"{T:.3f}", "-i", path]); idx += 1; return idx - 1

    def vid(path, a, d):
        nonlocal idx
        args.extend(["-i", path]); idx += 1; return idx - 1   # отрезок режет trim в фильтре: -ss перед -i
                                                              # подмешивал кадры до точки входа

    tag = f"{sc['id']}_{fmt}"
    bg = img(ov(f"bg_{tag}", g["cw"], g["ch"], scene_bg(fmt, sc["eb"], sc["title"]), transparent=False))
    mk = img(ov(f"mask_{fmt}", g["SW"], g["SH"], mask(g["SW"], g["SH"], g["r"])))
    labels = []
    for j, s in enumerate(segs):
        i = vid(os.path.join(SRC, SOURCES[s["src"]]), s["a"], max(s["b"] - s["a"], 0.05))  # ровно [a, b], остаток — стоп-кадр
        fc.append(f"[{i}:v]trim=start={s['a']:.3f}:duration={max(s['b'] - s['a'], 0.05):.3f},setpts=PTS-STARTPTS,"
                  f"{PRECROP.get(s['src'], '')}scale=-2:{g['SH']}:flags=lanczos,crop={g['SW']}:{g['SH']},setsar=1,fps={FPS},"
                  f"setpts=(PTS-STARTPTS)/{s['sp']:.4f},tpad=stop_mode=clone:stop_duration={s['d']:.3f},"
                  f"trim=duration={s['d']:.3f},setpts=PTS-STARTPTS[s{j}]")
        labels.append(f"[s{j}]")
    fc.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0,trim=duration={T:.3f},format=yuva420p[c0]")
    fc.append(f"[c0][{mk}:v]alphamerge[c]")
    fc.append(f"[{bg}:v][c]overlay={g['px']}:{g['py']}[b0]")
    cur = "[b0]"
    for n, side in enumerate(("L", "R")):
        spans = [(s["t0"], s["t0"] + s["d"]) for s in segs if s["side"] == side]
        if not spans:
            continue
        bi = img(ov(f"badge_{fmt}_{side}", 360, g["bh"], badge(ROLE[side], g["bh"])))
        expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in spans)
        fc.append(f"{cur}[{bi}:v]overlay={g['px'] + g['SW']//2 - 180}:{g['py'] - g['bz'] - g['bh'] - 10}:enable='{expr}'[g{n}]")
        cur = f"[g{n}]"
    fc.append(f"{cur}fade=t=in:st=0:d=0.25:color={BG.replace('#','0x')},"
              f"fade=t=out:st={T-0.25:.3f}:d=0.25:color={BG.replace('#','0x')},format=yuv420p[out]")
    out = os.path.join(OUT, f"{tag}.mp4")
    return dict(cmd=["ffmpeg", "-v", "error", "-y"] + args + ["-filter_complex", ";".join(fc), "-map", "[out]",
                     "-t", f"{T:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
                     "-pix_fmt", "yuv420p", out], out=out)


def phone_box(fmt):
    if fmt == "W":
        return dict(x=1220, y=150, w=372, h=778, bz=14, r=40)
    return dict(x=315, y=590, w=450, h=940, bz=16, r=46)


def frames_to_mp4(d, out, extra_in=None, extra_fc=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(d, "%05d.png")]
    if extra_in:
        cmd += extra_in
    if extra_fc:
        cmd += ["-filter_complex", extra_fc, "-map", "[out]"]
    cmd += ["-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", out]
    subprocess.run(cmd, check=True)


def main():
    jobs, cards = [], {}
    for fmt in ("W", "V"):
        for sc in SCENES:
            jobs.append(render_scene(sc, fmt))
        g = FMT[fmt]
        cards[("hook", fmt)] = os.path.join(OUT, f"hook_{fmt}")
        ov(f"hook_{fmt}", g["cw"], g["ch"], hook_html(fmt, DUR["01-hook"]), transparent=False,
           frames=dict(dir=cards[("hook", fmt)], fps=FPS, dur=DUR["01-hook"]))
        cards[("final", fmt)] = os.path.join(OUT, f"final_{fmt}")
        ov(f"final_{fmt}", g["cw"], g["ch"], outro_html(fmt, DUR["06-final"], phone_box(fmt)), transparent=False,
           frames=dict(dir=cards[("final", fmt)], fps=FPS, dur=DUR["06-final"]))
        for k, (a, b, txt) in enumerate(SUBS):
            s = g["sub"]
            ov(f"sub_{fmt}_{k:02d}", s["w"], s["h"], sub_html(fmt, txt))
        ov(f"sound_{fmt}", 300, 64, sound_html())
        p = phone_box(fmt)
        ov(f"mask_final_{fmt}", p["w"], p["h"], mask(p["w"], p["h"], p["r"]))
    for d in [v for v in cards.values()]:
        shutil.rmtree(d, ignore_errors=True)
    json.dump(ov_items, open(os.path.join(OUT, "ov.json"), "w"), ensure_ascii=False)
    subprocess.run(["node", os.path.join(B, "render.js"), os.path.join(OUT, "ov.json")], check=True, cwd=B)
    for j in jobs:
        subprocess.run(j["cmd"], check=True)
        print("сцена", os.path.basename(j["out"]))
    for fmt in ("W", "V"):
        frames_to_mp4(cards[("hook", fmt)], os.path.join(OUT, f"01-hook_{fmt}.mp4"))
        # финал: в фазе «демо по ссылке» в рамке телефона идёт запись брони
        p = phone_box(fmt)
        mk = os.path.join(OUT, f"mask_final_{fmt}.png")
        fc = (f"[1:v]trim=start=0.15:duration=2.9,setpts=PTS-STARTPTS,scale=-2:{p['h']}:flags=lanczos,crop={p['w']}:{p['h']},setsar=1,fps={FPS},setpts=PTS-STARTPTS+2.9/TB,"
              f"format=yuva420p,fade=t=in:st=2.9:d=0.35:alpha=1,fade=t=out:st=5.25:d=0.3:alpha=1[ph0];"
              f"[ph0][2:v]alphamerge[ph];[0:v][ph]overlay={p['x']}:{p['y']}:eof_action=pass:{en(2.9, 5.6)}[out]")
        frames_to_mp4(cards[("final", fmt)], os.path.join(OUT, f"06-final_{fmt}.mp4"),
                      ["-i", os.path.join(SRC, SOURCES["TB"]), "-loop", "1", "-i", mk], fc)
    for fmt in ("W", "V"):
        files = [os.path.join(OUT, f"01-hook_{fmt}.mp4")] + [os.path.join(OUT, f"{sc['id']}_{fmt}.mp4") for sc in SCENES] + \
                [os.path.join(OUT, f"06-final_{fmt}.mp4")]
        lst = os.path.join(OUT, f"list_{fmt}.txt")
        open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
        g = FMT[fmt]
        # склейка concat-фильтром: демуксер concat путал кадры на стыке сцен
        args = sum((["-i", f] for f in files), []) + ["-i", AUDIO]
        na = len(files)
        fc = ["".join(f"[{i}:v]" for i in range(na)) + f"concat=n={na}:v=1:a=0,fps={FPS}[cat]"]
        cur, n = "[cat]", na + 1
        for k, (a, b, txt) in enumerate(SUBS):
            args += ["-i", os.path.join(OUT, f"sub_{fmt}_{k:02d}.png")]
            fc.append(f"{cur}[{n}:v]overlay={g['sub']['x']}:{g['sub']['y']}:{en(a, b)}[v{k}]"); cur = f"[v{k}]"; n += 1
        args += ["-i", os.path.join(OUT, f"sound_{fmt}.png")]
        sx, sy = (1920 - 300 - 60, 40) if fmt == "W" else (1080 - 300 - 50, 130)
        fc.append(f"{cur}[{n}:v]overlay={sx}:{sy}:{en(0.2, 2.2)},format=yuv420p[vout]")
        fc.append(f"[{na}:a]apad=whole_dur={TOTAL:.3f},aresample=48000[aout]")
        name = f"knopka-korotko-озвучка-{g['cw']}x{g['ch']}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y"] + args + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
                        "-t", f"{TOTAL:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        os.path.join(FIN, name)], check=True)
        print("готово", name, f"{TOTAL:.2f} с")


if __name__ == "__main__":
    main()
