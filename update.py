import re
import requests
from pathlib import Path

COUNTRIES = {
    "ru": "Россия",
    "tj": "Таджикистан",
    "uz": "Узбекистан",
    "tr": "Турция",
    "ir": "Иран",
    "af": "Афганистан",
}

BASE_URL = "https://iptv-org.github.io/iptv/countries/"

session = requests.Session()
session.headers.update({
    "User-Agent": "Central-Asia-IPTV/1.0"
})


def add_country_group(extinf, country):
    match = re.search(r'group-title="([^"]*)"', extinf)

    if match:
        category = match.group(1).strip()
        group = f"{country} / {category or 'Без категории'}"
        return extinf[:match.start(1)] + group + extinf[match.end(1):]

    if "," in extinf:
        group = f'{country} / Без категории'
        return extinf.replace(
            ",",
            f' group-title="{group}",',
            1
        )

    return extinf


def main():
    playlist = ["#EXTM3U"]
    seen = set()
    total = 0
    failed = []

    for code, country in COUNTRIES.items():
        url = f"{BASE_URL}{code}.m3u"
        print(f"Загружаю: {country}")

        try:
            response = session.get(url, timeout=60)
            response.raise_for_status()
            lines = response.text.lstrip("\ufeff").splitlines()

        except requests.RequestException as error:
            print(f"Ошибка загрузки {country}: {error}")
            failed.append(country)
            continue

        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line.startswith("#EXTINF:"):
                i += 1
                continue

            extinf = line
            extra = []
            i += 1

            while i < len(lines):
                current = lines[i].strip()

                if current.startswith("http://") or current.startswith("https://"):
                    break

                if current.startswith("#EXTINF:"):
                    break

                if current.startswith("#") and current != "#EXTM3U":
                    extra.append(current)

                i += 1

            if i >= len(lines):
                break

            stream = lines[i].strip()

            if not stream.startswith(("http://", "https://")):
                continue

            i += 1

            if stream in seen:
                continue

            seen.add(stream)

            extinf = add_country_group(extinf, country)

            playlist.append(extinf)
            playlist.extend(extra)
            playlist.append(stream)

            total += 1

        print(f"Каналов добавлено: {total}")

    if total == 0:
        raise RuntimeError("Не удалось получить ни одного канала!")

    Path("tv.m3u").write_text(
        "\n".join(playlist) + "\n",
        encoding="utf-8"
    )

    print("=" * 40)
    print(f"Всего каналов: {total}")
    print(f"Ошибки загрузки стран: {failed}")
    print("Плейлист tv.m3u создан!")


if __name__ == "__main__":
    main()
