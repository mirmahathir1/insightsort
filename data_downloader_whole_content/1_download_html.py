import os
import time
import random
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://catalog.data.gov/dataset/?res_format=CSV&page={i}"
START_PAGE = 1
END_PAGE = 1468  # inclusive


def get_output_dir() -> Path:
	# Save into semantic-sort/data/data_downloader_whole_content
	repo_root = Path(__file__).resolve().parent.parent
	out_dir = repo_root / "data" / "data_downloader_whole_content"
	out_dir.mkdir(parents=True, exist_ok=True)
	return out_dir


def fetch_html(session: requests.Session, url: str, retries: int = 5, timeout: int = 30) -> Optional[str]:
	backoff = 1.5
	for attempt in range(1, retries + 1):
		try:
			resp = session.get(url, timeout=timeout)
			if resp.status_code == 200:
				return resp.text
			# Handle common transient statuses with backoff
			if resp.status_code in {429, 500, 502, 503, 504}:
				sleep_s = backoff ** attempt + random.uniform(0, 0.5)
				time.sleep(sleep_s)
				continue
			# Non-retryable status
			print(f"Non-OK status {resp.status_code} for {url}")
			return None
		except requests.RequestException as e:
			sleep_s = backoff ** attempt + random.uniform(0, 0.5)
			print(f"Request error on attempt {attempt} for {url}: {e}")
			time.sleep(sleep_s)
	return None


def extract_dataset_list(html: str) -> Optional[str]:
	soup = BeautifulSoup(html, "html.parser")
	elems = soup.find_all(class_="dataset-list")
	if not elems:
		return None
	# Join all matching elements (in case there are multiple)
	return "\n".join(str(e) for e in elems)


def crawl_and_save(start: int = START_PAGE, end: int = END_PAGE) -> None:
	out_dir = get_output_dir()
	session = requests.Session()
	session.headers.update(
		{
			"User-Agent": (
				"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
				"(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
			)
		}
	)

	from tqdm import tqdm
	total = end - start + 1
	# Filter out already downloaded pages
	pages_to_download = []
	for i in range(start, end + 1):
		out_path = out_dir / f"page_{i:04d}.html"
		if not (out_path.exists() and out_path.stat().st_size > 0):
			pages_to_download.append(i)

	with tqdm(pages_to_download, desc="Crawling pages", unit="page") as pbar:
		for i in pbar:
			url = BASE_URL.format(i=i)
			out_path = out_dir / f"page_{i:04d}.html"

			pbar.set_postfix_str(f"Fetching page {i}")
			html = fetch_html(session, url)
			if html is None:
				pbar.set_postfix_str(f"Failed to fetch page {i}")
				continue

			snippet = extract_dataset_list(html)
			if snippet is None:
				pbar.set_postfix_str(f"No .dataset-list on page {i}")
				snippet = ""

			out_path.write_text(snippet, encoding="utf-8")
			pbar.set_postfix_str(f"Saved {out_path.name}")

			# Polite delay with slight jitter
			time.sleep(1)



import sys

if __name__ == "__main__":
	start = int(os.getenv("CRAWL_START", START_PAGE))
	end = int(os.getenv("CRAWL_END", END_PAGE))
	try:
		crawl_and_save(start, end)
	except Exception as e:
		print(f"Fatal error: {e}", file=sys.stderr)
		sys.exit(1)

