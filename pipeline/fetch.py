"""Download full Statcast seasons from Baseball Savant in weekly chunks.

Usage:  python -m pipeline.fetch 2025 2026
Writes data/raw/statcast_<year>_raw.parquet (git-ignored).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import pybaseball as pb

RAW_DIR = Path("data/raw")
SEASON_WINDOW = ("03-15", "11-10")  # spring openers through World Series
CHUNK_DAYS = 6


def fetch_season(year: int) -> pd.DataFrame:
    start = pd.Timestamp(f"{year}-{SEASON_WINDOW[0]}")
    end = pd.Timestamp(f"{year}-{SEASON_WINDOW[1]}")
    frames = []
    cur = start
    while cur <= end:
        stop = min(cur + pd.Timedelta(days=CHUNK_DAYS), end)
        for attempt in range(3):
            try:
                df = pb.statcast(cur.strftime("%Y-%m-%d"), stop.strftime("%Y-%m-%d"), verbose=False)
                break
            except Exception as exc:  # network hiccups from Savant
                print(f"  retry {attempt + 1} {cur.date()}: {exc}", flush=True)
                time.sleep(10)
        else:
            raise RuntimeError(f"failed chunk {cur.date()}")
        if df is not None and len(df):
            frames.append(df)
        print(f"  {year} {cur.date()} → {stop.date()}: {0 if df is None else len(df):,}", flush=True)
        cur = stop + pd.Timedelta(days=1)
        time.sleep(2)
    out = pd.concat(frames, ignore_index=True)
    out = out[~out["game_type"].isin(["S", "E", "A"])]
    return out


def main(years: list[int]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    pb.cache.enable()
    for year in years:
        path = RAW_DIR / f"statcast_{year}_raw.parquet"
        if path.exists():
            print(f"{path} exists, skipping")
            continue
        df = fetch_season(year)
        df.to_parquet(path, index=False)
        print(f"saved {path}: {len(df):,} pitches", flush=True)


if __name__ == "__main__":
    main([int(y) for y in sys.argv[1:]] or [2025, 2026])
