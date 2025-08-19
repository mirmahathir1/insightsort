#!/usr/bin/env python3
"""
Download CSV files listed in metadata CSV using parallel processing with deterministic sampling.

Metadata CSV (default: data/data_downloader_whole_content/links_with_filenames.csv)
	- Required columns: file_name, csv_link, data_organization

Features:
  - Parallel downloads via multiprocessing (default 20 workers)
  - Deterministic sampling: take first N after stable sort by (organization_type, file_name, csv_link)
  - Per-download overall timeout (default 15s); if exceeded, salvage partial content into a valid CSV by
	truncating to the last complete line
  - Files saved under: data/data_downloader_whole_content/downloads/{organization_type}/{file_name}
  - Central tqdm progress bar in main process
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from typing import Optional, Tuple, Dict, Any

import pandas as pd
import requests
from tqdm import tqdm


DEFAULT_METADATA = "data/data_downloader_whole_content/links_with_filenames.csv"
DEFAULT_OUTDIR = "data/data_downloader_whole_content/downloads"


def sanitize_component(name: str) -> str:
	"""Make a safe filesystem path component.

	- Replace path separators
	- Strip surrounding whitespace
	- Collapse to ascii-ish if necessary (best-effort)
	- Limit length
	"""
	if not isinstance(name, str):
		name = str(name)
	s = name.strip().replace("/", "-").replace("\\", "-")
	# Remove problematic characters
	bad_chars = "\"'`<>|:*?\n\r\t\0"
	for ch in bad_chars:
		s = s.replace(ch, "-")
	# Avoid hidden names
	if s.startswith('.'):
		s = s.lstrip('.')
	s = s or "unnamed"
	# Limit to reasonable length
	return s[:180]


@dataclass
class Task:
	url: str
	data_organization: str
	file_name: str
	out_dir: str
	timeout: float
	overwrite: bool

	def dest_path(self) -> str:
		sub = sanitize_component(self.data_organization or "unknown")
		fname = sanitize_component(self.file_name or "file.csv")
		# Ensure .csv extension if missing
		if not fname.lower().endswith(".csv"):
			fname = f"{fname}.csv"
		return os.path.join(self.out_dir, sub, fname)


def ensure_parent_dir(path: str) -> None:
	os.makedirs(os.path.dirname(path), exist_ok=True)


def save_bytes_safely(path: str, data: bytes) -> None:
	ensure_parent_dir(path)
	tmp = f"{path}.part"
	with open(tmp, "wb") as f:
		f.write(data)
	os.replace(tmp, path)


def salvage_to_valid_csv(data: bytes) -> bytes:
	"""Attempt to make the byte content a valid CSV by trimming to the last full line.

	- Find the last newline; if found, truncate after it to avoid partial final row.
	- If no newline found, return empty bytes (can't guarantee a full row).
	"""
	if not data:
		return b""
	nl = data.rfind(b"\n")
	if nl == -1:
		# No complete lines; keep nothing to avoid malformed partial row
		return b""
	return data[: nl + 1]


def download_with_deadline(url: str, timeout_seconds: float) -> Tuple[bool, bytes, bool, Optional[str]]:
	"""Download URL with an overall deadline.

	Returns: (success, content_bytes, timed_out, error_message)
	"""
	headers = {
		"User-Agent": "semantic-sort-downloader/1.0 (+https://example.com)"
	}
	start = time.time()
	buf = bytearray()
	timed_out = False
	try:
		# Use small connect/read timeouts but enforce our own overall deadline
		with requests.get(url, headers=headers, stream=True, timeout=(5, 5)) as resp:
			resp.raise_for_status()
			for chunk in resp.iter_content(chunk_size=1024 * 64):
				if chunk:
					buf.extend(chunk)
				if time.time() - start > timeout_seconds:
					timed_out = True
					break
	except requests.exceptions.Timeout as e:
		timed_out = True
		return False, bytes(buf), timed_out, f"timeout: {e}"
	except Exception as e:
		return False, bytes(buf), timed_out, f"error: {e}"

	# If timed out mid-stream, indicate partial success
	if timed_out:
		return False, bytes(buf), True, "overall timeout exceeded"

	return True, bytes(buf), False, None


def worker(task: Task) -> Dict[str, Any]:
	path = task.dest_path()
	try:
		if (not task.overwrite) and os.path.exists(path):
			return {"status": "skipped_exists", "path": path, "url": task.url}

		ok, data, timed_out, err = download_with_deadline(task.url, task.timeout)
		if ok:
			save_bytes_safely(path, data)
			return {"status": "downloaded", "path": path, "bytes": len(data)}

		# If timed out but have some data, salvage
		if timed_out and data:
			salvaged = salvage_to_valid_csv(data)
			save_bytes_safely(path, salvaged)
			return {
				"status": "salvaged_timeout",
				"path": path,
				"bytes": len(salvaged),
				"note": f"timed out; saved {len(salvaged)} bytes",
			}

		# If timed out and no data, create empty CSV file placeholder
		if timed_out and not data:
			save_bytes_safely(path, b"")
			return {"status": "empty_timeout", "path": path}

		# Other errors
		return {"status": "error", "path": path, "error": err}
	except Exception as e:
		return {"status": "error", "path": path, "error": f"{e}\n{traceback.format_exc()}"}


def build_tasks(df: pd.DataFrame, out_dir: str, timeout: float, overwrite: bool) -> list[Task]:
	tasks: list[Task] = []
	for _, row in df.iterrows():
		url = str(row["csv_link"]).strip()
		org = str(row.get("data_organization", "unknown"))
		fname = str(row["file_name"]).strip()
		tasks.append(Task(url=url, data_organization=org, file_name=fname, out_dir=out_dir, timeout=timeout, overwrite=overwrite))
	return tasks


def deterministic_sample(df: pd.DataFrame, sample_size: Optional[int]) -> pd.DataFrame:
	# Stable sort ensures deterministic selection
	df_sorted = df.sort_values(["data_organization", "file_name", "csv_link"], kind="stable").reset_index(drop=True)
	if sample_size is None or sample_size <= 0 or sample_size >= len(df_sorted):
		return df_sorted
	return df_sorted.iloc[:sample_size].copy()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
	p = argparse.ArgumentParser(description="Parallel CSV downloader with deterministic sampling")
	p.add_argument("--metadata", default=DEFAULT_METADATA, help="Path to metadata CSV with file_name,csv_link,data_organization")
	p.add_argument("--outdir", default=DEFAULT_OUTDIR, help="Output downloads directory")
	p.add_argument("--processes", type=int, default=min(20, cpu_count()), help="Number of parallel worker processes (default 20)")
	p.add_argument("--timeout", type=float, default=15.0, help="Overall timeout per download in seconds")
	p.add_argument("--sample-size", type=int, default=None, help="Deterministic sample size (first N after stable sort)")
	p.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
	return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
	args = parse_args(argv)

	# Load metadata
	try:
		df = pd.read_csv(args.metadata)
	except Exception as e:
		print(f"Failed to read metadata CSV at {args.metadata}: {e}", file=sys.stderr)
		return 2

	required_cols = {"file_name", "csv_link", "data_organization"}
	missing = required_cols - set(df.columns)
	if missing:
		print(f"Metadata CSV missing required columns: {sorted(missing)}", file=sys.stderr)
		return 2

	df = deterministic_sample(df, args.sample_size)
	tasks = build_tasks(df, args.outdir, args.timeout, args.overwrite)

	# Progress tracking
	outcomes = {"downloaded": 0, "salvaged_timeout": 0, "empty_timeout": 0, "skipped_exists": 0, "error": 0}

	# Ensure base directory exists
	os.makedirs(args.outdir, exist_ok=True)

	# Multiprocessing pool
	with Pool(processes=args.processes) as pool:
		with tqdm(total=len(tasks), desc="Downloading CSVs", unit="file") as pbar:
			for res in pool.imap_unordered(worker, tasks, chunksize=1):
				status = res.get("status", "error")
				outcomes[status] = outcomes.get(status, 0) + 1
				pbar.update(1)
				pbar.set_postfix(outcomes)

	# Summary
	total = sum(outcomes.values())
	print(
		"\nDone. Summary: "
		f"downloaded={outcomes['downloaded']}, "
		f"salvaged_timeout={outcomes['salvaged_timeout']}, "
		f"empty_timeout={outcomes['empty_timeout']}, "
		f"skipped_exists={outcomes['skipped_exists']}, "
		f"error={outcomes['error']}, "
		f"total={total}"
	)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())

