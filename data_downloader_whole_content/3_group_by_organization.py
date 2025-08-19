from pathlib import Path
from collections import Counter
import csv
import sys
from typing import List, Tuple


def get_links_path() -> Path:
	repo_root = Path(__file__).resolve().parent.parent
	return repo_root / "data" / "data_downloader_whole_content" / "links.csv"


def get_output_path() -> Path:
	repo_root = Path(__file__).resolve().parent.parent
	out_dir = repo_root / "data" / "data_downloader_whole_content"
	out_dir.mkdir(parents=True, exist_ok=True)
	return out_dir / "org_counts.csv"


def count_by_org_with_pandas(path: Path) -> List[Tuple[str, int]]:
	import pandas as pd

	df = pd.read_csv(path)
	if "data_organization" not in df.columns:
		raise KeyError("Expected column 'data_organization' in CSV")
	counts = df["data_organization"].fillna("").astype(str).value_counts()
	return list(counts.items())


def count_by_org_fallback(path: Path) -> List[Tuple[str, int]]:
	cnt = Counter()
	with path.open("r", encoding="utf-8", newline="") as fh:
		reader = csv.DictReader(fh)
		for row in reader:
			org = (row.get("data_organization") or "").strip()
			cnt[org] += 1
	return cnt.most_common()


def main(save: bool = False, top: int = 50) -> int:
	links_path = get_links_path()
	if not links_path.exists():
		print(f"links.csv not found at {links_path}")
		return 2

	try:
		counts = count_by_org_with_pandas(links_path)
	except Exception:
		counts = count_by_org_fallback(links_path)

	# print results (show all)
	print(f"Found {len(counts)} organizations (showing all)")
	for i, (org, c) in enumerate(counts, start=1):
		print(f"{i:3d}. {org!s:60s} {c}")

	# saving disabled by default per user request

	return 0


if __name__ == "__main__":
	# simple CLI: optional first arg is number of top rows to show
	top_n = 50
	if len(sys.argv) >= 2:
		try:
			top_n = int(sys.argv[1])
		except Exception:
			pass
	raise SystemExit(main(top=top_n))

