import requests
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SOURCE = Path("all_channels.m3u")
OUTPUT = Path("tv.m3u")
REPORT = Path("check_report.txt")

TIMEOUT = 12
WORKERS = 20

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 Central-Asia-IPTV"


def parse_playlist(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    channels = []
    i = 0

    while i < len(lines):
        info = lines[i].strip()

        if not info.startswith("#EXTINF:"):
            i += 1
            continue

        extras = []
        i += 1

        while i < len(lines):
            line = lines[i].strip()

            if line.startswith(("http://", "https://")):
                break

            if line.startswith("#EXTINF:"):
                break

            if line.startswith("#"):
                extras.append(line)

            i += 1

        if i < len(lines):
            url = lines[i].strip()

            if url.startswith(("http://", "https://")):
                channels.append((info, extras, url))

        i += 1

    return channels


def check_stream(channel):
    info, extras, url = channel

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            stream=True,
            timeout=TIMEOUT,
            allow_redirects=True
        )

        status = response.status_code
        content_type = response.headers.get("Content-Type", "").lower()

        response.close()

        if status == 200 and (
            "mpegurl" in content_type
            or "video" in content_type
            or "octet-stream" in content_type
            or not content_type
        ):
            return channel, True, "HTTP 200"

        return channel, False, f"HTTP {status}: {content_type}"

    except requests.RequestException as error:
        return channel, False, str(error)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError("Не найден all_channels.m3u")

    channels = parse_playlist(SOURCE)

    working = []
    failed = []

    print(f"Всего потоков для проверки: {len(channels)}")

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [
            executor.submit(check_stream, channel)
            for channel in channels
        ]

        for future in as_completed(futures):
            channel, ok, message = future.result()

            if ok:
                working.append(channel)
            else:
                failed.append((channel, message))

    # Сохраняем исходные данные, включая метаданные каналов
    output = ["#EXTM3U"]

    for info, extras, url in working:
        output.append(info)
        output.extend(extras)
        output.append(url)

    OUTPUT.write_text(
        "\n".join(output) + "\n",
        encoding="utf-8"
    )

    report = [
        f"Всего проверено: {len(channels)}",
        f"HTTP-доступны: {len(working)}",
        f"Недоступны: {len(failed)}",
        "",
        "Проверка не гарантирует воспроизведение на телевизоре.",
        "",
        "Недоступные потоки:"
    ]

    for channel, message in failed:
        report.append(f"{channel[0]} | {message}")

    REPORT.write_text(
        "\n".join(report) + "\n",
        encoding="utf-8"
    )

    print(f"Доступны по HTTP: {len(working)}")
    print(f"Недоступны: {len(failed)}")
    print("Проверка завершена!")


if __name__ == "__main__":
    main()
