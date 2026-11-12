import requests
from pathlib import Path

COUNTRIES = {
    "ru": "🇷🇺 Россия",
    "tj": "🇹🇯 Таджикистан",
    "uz": "🇺🇿 Узбекистан",
    "tr": "🇹🇷 Турция",
    "ir": "🇮🇷 Иран",
    "af": "🇦🇫 Афганистан",
}

BASE_URL = "https://iptv-org.github.io/iptv/countries/"

def main():
    channels = []
    seen = set()

    for country, country_name in COUNTRIES.items():
        url = f"{BASE_URL}{country}.m3u"

        print(f"Загружаю: {country_name}")

        try:
            response = requests.get(url, timeout=40)
            response.raise_for_status()
            lines = response.text.splitlines()

            for i, line in enumerate(lines):
                if not line.startswith("#EXTINF:"):
                    continue

                if i + 1 >= len(lines):
                    continue

                stream = lines[i + 1].strip()

                if not stream.startswith(("http://", "https://")):
                    continue

                if stream in seen:
                    continue

                seen.add(stream)
                channels.extend([line, stream])

        except requests.RequestException as error:
            print(f"Ошибка {country}: {error}")

    playlist = ["#EXTM3U"] + channels
    Path("tv.m3u").write_text(
        "\n".join(playlist) + "\n",
        encoding="utf-8"
    )

    print(f"Готово! Каналов: {len(channels) // 2}")

if __name__ == "__main__":
    main()
