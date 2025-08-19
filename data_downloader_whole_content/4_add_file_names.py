import random
import os
import sys
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import requests
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def repo_root() -> Path:
	return Path(__file__).resolve().parent.parent

def links_csv_path() -> Path:
	return repo_root() / "data" / "data_downloader_whole_content" / "links.csv"

def parse_content_disposition(header: Optional[str]) -> Optional[str]:
	if not header:
		return None
	m_star = re.search(r"filename\*=([^;]+)", header, flags=re.IGNORECASE)
	if m_star:
		val = m_star.group(1).strip().strip('"')
		if "''" in val:
			_, _, val = val.partition("''")
		try:
			from urllib.parse import unquote
			return unquote(val)
		except Exception:
			return val
	m = re.search(r"filename=\"?([^\";]+)\"?", header, flags=re.IGNORECASE)
	if m:
		return m.group(1).strip()
	return None

def parse_name_from_content_type(header: Optional[str]) -> Optional[str]:
	if not header:
		return None
	m = re.search(r"name=\"?([^\";]+)\"?", header, flags=re.IGNORECASE)
	if m:
		return m.group(1).strip()
	return None

def filename_from_url(url: str) -> str:
	base = url.split("?", 1)[0].split("#", 1)[0]
	name = base.rstrip("/").rsplit("/", 1)[-1] or "download.csv"
	return name

def get_filename(url: str) -> str:
	# Try HEAD first
	try:
		resp = requests.head(url, allow_redirects=True, timeout=15)
		if resp.ok:
			cd = resp.headers.get("Content-Disposition") or resp.headers.get("content-disposition")
			name = parse_content_disposition(cd)
			if name:
				return name
			# Some servers put name= in Content-Type
			ct = resp.headers.get("Content-Type") or resp.headers.get("content-type")
			name2 = parse_name_from_content_type(ct)
			if name2:
				return name2
	except Exception:
		pass

	# Fallback: tiny GET with byte range to avoid full download; many servers include headers on GET only
	try:
		headers = {"Range": "bytes=0-0"}
		r = requests.get(url, headers=headers, allow_redirects=True, stream=True, timeout=20)
		try:
			if r.ok:
				cd = r.headers.get("Content-Disposition") or r.headers.get("content-disposition")
				name = parse_content_disposition(cd)
				if name:
					return name
				ct = r.headers.get("Content-Type") or r.headers.get("content-type")
				name2 = parse_name_from_content_type(ct)
				if name2:
					return name2
		finally:
			# Ensure connection is closed without reading body
			r.close()
	except Exception:
		pass

	# Last resort: derive from URL
	return filename_from_url(url)

def load_all_links() -> List[str]:
	path = links_csv_path()
	if not path.exists():
		print(f"links.csv not found at {path}")
		return []
	try:
		import pandas as pd
		df = pd.read_csv(path)
		links = df["csv_link"].dropna().astype(str).tolist()
	except Exception:
		import csv
		links = []
		with path.open("r", encoding="utf-8", newline="") as fh:
			reader = csv.DictReader(fh)
			for row in reader:
				link = (row.get("csv_link") or "").strip()
				if link:
					links.append(link)
	return links


def resolve_all_filenames(urls: List[str], processes: int = 10) -> Dict[str, str]:
	# Deduplicate and shuffle
	uniq = list(dict.fromkeys(urls))
	random.shuffle(uniq)

	# Worker pool
	procs = min(processes, cpu_count() or 1)
	mapping: Dict[str, str] = {}
	with Pool(processes=procs) as pool:
		for url, name in tqdm(pool.imap_unordered(_worker_get_name, uniq), total=len(uniq), desc="Resolving filenames", unit="file"):
			mapping[url] = name
	return mapping


def _worker_get_name(url: str) -> Tuple[str, str]:
	# separate function for pickling by multiprocessing
	try:
		return (url, get_filename(url))
	except Exception:
		return (url, filename_from_url(url))

def main():
	# number of processes can be passed as the first CLI arg; default 10
	procs = 20
	if len(sys.argv) >= 2 and sys.argv[1].strip():
		try:
			procs = int(sys.argv[1])
		except Exception:
			pass
	sample_size = None
	links_all = load_all_links()
	if not links_all:
		return

	# deduplicate first
	uniq_links = list(dict.fromkeys(links_all))
	# shuffle for fair distribution
	random.shuffle(uniq_links)
	links = uniq_links if sample_size is None or sample_size >= len(uniq_links) else random.sample(uniq_links, sample_size)

	print(f"Processing {len(links)} links (of {len(uniq_links)} unique total) using {procs} processes.")

	name_map = resolve_all_filenames(links, processes=procs)

	# Print a short sample of results
	print(f"Resolved filenames for {len(name_map)} links.")
	for i, url in enumerate(list(name_map.keys())[:10], 1):
		print(f"{i:2d}. {name_map[url]}\n    {url}")

	# Save augmented CSV with new file_name column
	out_dir = repo_root() / "data" / "data_downloader_whole_content"
	out_dir.mkdir(parents=True, exist_ok=True)
	out_path = out_dir / ("links_with_filenames.csv" if sample_size is None else f"links_with_filenames_sample{len(links)}.csv")
	try:
		import pandas as pd
		df = pd.read_csv(links_csv_path())
		if sample_size is None:
			# annotate all rows
			df["file_name"] = df["csv_link"].map(lambda u: name_map.get(u, filename_from_url(str(u))))
		else:
			# write only sampled rows
			df = df[df["csv_link"].isin(set(links))].copy()
			df["file_name"] = df["csv_link"].map(lambda u: name_map.get(u, filename_from_url(str(u))))
		df.to_csv(out_path, index=False)
	except Exception:
		# Fallback: write manually
		import csv
		in_path = links_csv_path()
		with in_path.open("r", encoding="utf-8", newline="") as infh, out_path.open("w", encoding="utf-8", newline="") as outfh:
			reader = csv.DictReader(infh)
			if sample_size is None:
				rows_iter = reader
			else:
				sel = set(links)
				rows_iter = (r for r in reader if (r.get("csv_link") or "").strip() in sel)
			fieldnames = list(reader.fieldnames or []) + (["file_name"] if "file_name" not in (reader.fieldnames or []) else [])
			writer = csv.DictWriter(outfh, fieldnames=fieldnames)
			writer.writeheader()
			for row in rows_iter:
				url = (row.get("csv_link") or "").strip()
				row["file_name"] = name_map.get(url, filename_from_url(url))
				writer.writerow(row)
	print(f"Saved with file_name column: {out_path}")

if __name__ == "__main__":
	main()
