import re
import requests
from pathlib import Path

SOURCES = [
    ("https://iptv-org.github.io/iptv/countries/ru.m3u", "Россия"),
    ("https://iptv-org.github.io/iptv/languages/rus.m3u", "Русский язык"),

    ("https://iptv-org.github.io/iptv/countries/uz.m3u", "Узбекистан"),
    ("https://iptv-org.github.io/iptv/languages/uzb.m3u", "Узбекский язык"),

    ("https://iptv-org.github.io/iptv/countries/tj.m3u", "Таджикистан"),
    ("https://iptv-org.github.io/iptv/languages/tgk.m3u", "Таджикский язык"),

    ("https://iptv-org.github.io/iptv/countries/tr.m3u", "Турция"),
    ("https://iptv-org.github.io/iptv/countries/ir.m3u", "Иран"),
    ("https://iptv-org.github.io/iptv/countries/af.m3u", "Афганистан"),
]

NEXUS_UZ_API = (
    "https://dearbulut.github.io/iptv/api/v1/by-country/uz.json"
)

session = requests.Session()
session.headers["User-Agent"] = "Central-Asia-IPTV/1.0"


def clean(value):
    return str(value or "").replace('"', "'").replace("\n", " ").strip()


def parse_playlist(text):
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

            if current.startswith(("http://", "https://")):
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

        if url.startswith(("http://", "https://")):
            if 'group-title="' not in info:
                info = info.replace(
                    ",",
                    ' group-title="Без категории",',
                    1
                )

            result.append((info, extras, url))

    return result


def get_nexus_uzbekistan():
    print("Загружаю IPTV Nexus — Узбекистан")

    response = session.get(NEXUS_UZ_API, timeout=120)
    response.raise_for_status()

    channels = response.json()

    if not isinstance(channels, list):
        raise ValueError("Неожиданный формат IPTV Nexus API")

    result = []

    for channel in channels:
        name = clean(channel.get("name"))
        channel_id = clean(channel.get("id"))
        logo = clean(channel.get("logo"))

        categories = channel.get("categories") or []
        languages = channel.get("languages") or []

        category = clean(categories[0]) if categories else "Узбекистан"
        language = ",".join(clean(x) for x in languages)

        for stream in channel.get("streams") or []:
            url = clean(stream.get("url"))

            if not url.startswith(("http://", "https://")):
                continue

            attrs = [
                f'tvg-id="{channel_id}"',
                f'tvg-name="{name}"',
                'tvg-country="UZ"',
                f'group-title="Узбекистан / {category}"'
            ]

            if logo:
                attrs.append(f'tvg-logo="{logo}"')

            if language:
                attrs.append(f'tvg-language="{language}"')

            health = stream.get("health") or {}
            score = health.get("score")

            if score is not None:
                attrs.append(f'nexus-score="{score}"')

            title = clean(stream.get("title")) or name

            info = (
                '#EXTINF:-1 '
                + " ".join(attrs)
                + ","
                + title
            )

            extras = []

            user_agent = stream.get("user_agent")
            referrer = stream.get("referrer")

            if user_agent:
                extras.append(
                    "#EXTVLCOPT:http-user-agent=" + clean(user_agent)
                )

            if referrer:
                extras.append(
                    "#EXTVLCOPT:http-referrer=" + clean(referrer)
                )

            # Не удаляем повторяющиеся потоки.
            # Не фильтруем временно недоступные ссылки.
            result.append((info, extras, url))

    print(f"Nexus: получено потоков — {len(result)}")
    return result


def main():
    all_channels = []
    report = []

    for url, source_name in SOURCES:
        print(f"Загружаю: {source_name}")

        try:
            response = session.get(url, timeout=90)
            response.raise_for_status()

            channels = parse_playlist(response.text)

            # Сохраняем все записи, включая дубликаты.
            all_channels.extend(channels)

            report.append(f"{source_name}: {len(channels)}")
            print(f"Добавлено: {len(channels)}")

        except requests.RequestException as error:
            report.append(f"{source_name}: ОШИБКА")
            print(f"Ошибка: {error}")

    # Дополнительный источник узбекских каналов.
    try:
        nexus_channels = get_nexus_uzbekistan()
        all_channels.extend(nexus_channels)
        report.append(
            f"IPTV Nexus — Узбекистан: {len(nexus_channels)}"
        )

    except (requests.RequestException, ValueError) as error:
        report.append("IPTV Nexus — Узбекистан: ОШИБКА")
        print(f"Ошибка Nexus: {error}")

    if not all_channels:
        raise RuntimeError("Нет каналов для создания плейлиста")

    header = [
        "#EXTM3U",
        "# Central Asia IPTV — все источники и резервные потоки"
    ]

    for info, extras, url in all_channels:
        header.append(info)
        header.extend(extras)
        header.append(url)

    playlist = "\n".join(header) + "\n"

    Path("all_channels.m3u").write_text(
        playlist,
        encoding="utf-8"
    )

    Path("tv.m3u").write_text(
        playlist,
        encoding="utf-8"
    )

    Path("report.txt").write_text(
        "\n".join(report)
        + f"\nВсего записей (с повторами): {len(all_channels)}\n",
        encoding="utf-8"
    )

    print(f"Всего записей: {len(all_channels)}")


if __name__ == "__main__":
    main()
