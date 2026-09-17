"""Télécharge les différentiels LEGI nécessaires à un snapshot daté."""

from __future__ import annotations

import argparse
import http.client
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_URL = "https://echanges.dila.gouv.fr/OPENDATA/LEGI/"
DELTA_RE = re.compile(r'href="(LEGI_(\d{8}-\d{6})\.tar\.gz)"')
UA = "Balise-CASF-builder/1.0"


def list_delta_urls(html: str, *, after: str, as_of: str) -> list[str]:
    """Liste chronologique des différentiels après le stock, jusqu'à as_of."""
    limit = as_of.replace("-", "")
    found = {
        stamp: BASE_URL + filename
        for filename, stamp in DELTA_RE.findall(html)
        if stamp > after and stamp[:8] <= limit
    }
    return [found[stamp] for stamp in sorted(found)]


def _download(url: str, dest_dir: Path) -> Path:
    dest = dest_dir / url.rsplit("/", 1)[-1]
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    part = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response, part.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            part.replace(dest)
            return dest
        except (OSError, http.client.HTTPException) as exc:  # réseau : trois reprises bornées
            last_error = exc
            part.unlink(missing_ok=True)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"échec téléchargement {url}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--after", default="20250713-140000")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    request = urllib.request.Request(BASE_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", "replace")
    urls = list_delta_urls(html, after=args.after, as_of=args.as_of)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"{len(urls)} différentiels à synchroniser", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 12))) as pool:
        futures = {pool.submit(_download, url, args.out): url for url in urls}
        for done, future in enumerate(as_completed(futures), start=1):
            path = future.result()
            print(f"[{done}/{len(urls)}] {path.name}", flush=True)


if __name__ == "__main__":
    main()
