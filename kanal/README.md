# Задача 2 — канал и бренд

Основной документ (название, оформление, воронка, контент-план, 10 постов, привлечение, Kwork, риски):
https://claude.ai/artifact/8Xb9wvotdGRn5CU5FxLSLL

Здесь:
- `kontent-plan-30-dney.xlsx` — контент-план на 30 дней (открывается в Excel / импортируется в Google Sheets)
- `kontent-plan-30-dney.csv` — то же в CSV (UTF-8)

## Логотип (палитра карточек и презентации)
`logo/neruchnoy-*` — тёмно-синий `#14202B`, оранжевый `#FF6B3D`, «бумага» `#F6F4EF`, шрифт Unbounded.
- `neruchnoy-dark.png` — основной аватар канала (640×640)
- `neruchnoy-light.png` — светлый вариант
- `neruchnoy-dark-text.png` — с надписью, для крупных размеров (сторис, обложки)
- `neruchnoy-wordmark.png` — горизонтальный логотип для шапок и Kwork
- `preview-v2.png` — как смотрится в списке чатов (светлая/тёмная тема, мелкие размеры)

Пересборка: `npm i @fontsource/unbounded @fontsource/manrope opentype.js playwright && node logo/build-logo.js logo`
