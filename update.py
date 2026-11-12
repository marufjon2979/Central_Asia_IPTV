import re
import requests
from pathlib import Path

BASE = "https://iptv-org.github.io/iptv/"

SOURCES = [
    ("countries/ru.m3u", "Россия"),
    ("languages/rus.m3u", "Русский язык"),

    ("countries/uz.m3u", "Узбекистан"),
    ("languages/uzb.m3u", "Узбекский язык"),

    ("countries/tj.m3u", "Таджикистан"),
    ("languages/tgk.m3u", "Таджикский язык"),

    ("countries/tr.m3u", "Турция"),
    ("countries/ir.m3u", "Иран"),
    ("countries/af.m3u", "Афганистан"),
]

session = requests.Session()
session.headers["User-Agent"] = "Central-Asia-IPTV/1.0"


def parse_playlist(text, source_name):
    lines = text.lstrip("\ufeff").splitlines()
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if not line.startswith("#EXTINF:"):
            i += 1
            continue

        info = line
        extras = []
        i += 1

        while i < len(lines):
            current = lines[i].strip()

            if current.startswith("http://") or current.startswith("https://"):
                break

            if current.startswith("#EXTINF:"):
                break

            if current.startswith("#") and current != "#EXTM3U":
                extras.append(current)

            i += 1

        if i >= len(lines):
            break

        url = lines[i].strip()
        i += 1

        if not url.startswith(("http://", "https://")):
            continue

        # Сохраняем оригинальную категорию
        match = re.search(r'group-title="([^"]*)"', info)

        if match:
            category = match.group(1).strip() or "Без категории"
        else:
            category = "Без категории"
            if "," in info:
                info = info.replace(
                    ",",
                    f' group-title="{category}",',
                    1
                )

        result.append((info, extras, url))

    return result


def main():
    all_channels = []
    seen = set()
    report = []

    for path, source_name in SOURCES:
        print(f"Загружаю: {source_name}")

        try:
            response = session.get(BASE + path, timeout=60)
            response.raise_for_status()

            channels = parse_playlist(response.text, source_name)
            added = 0

            for info, extras, url in channels:
                if url in seen:
                    continue

                seen.add(url)
                all_channels.append((info, extras, url))
                added += 1

            report.append(f"{source_name}: {added}")
            print(f"Добавлено: {added}")

        except requests.RequestException as error:
            report.append(f"{source_name}: ОШИБКА")
            print(f"Ошибка: {error}")

    if not all_channels:
        raise RuntimeError("Нет каналов для создания плейлиста")

    header = [
        "#EXTM3U",
        "# Список собран из открытых каталогов IPTV"
    ]

    for info, extras, url in all_channels:
        header.append(info)
        header.extend(extras)
        header.append(url)

    Path("all_channels.m3u").write_text(
        "\n".join(header) + "\n",
        encoding="utf-8"
    )

    # Пока tv.m3u сохраняет все найденные потоки.
    # Проверку реального воспроизведения добавим отдельно.
    Path("tv.m3u").write_text(
        "\n".join(header) + "\n",
        encoding="utf-8"
    )

    Path("report.txt").write_text(
        "\n".join(report) +
        f"\nВсего уникальных потоков: {len(all_channels)}\n",
        encoding="utf-8"
    )

    print(f"Всего потоков: {len(all_channels)}")


if __name__ == "__main__":
    main()
