from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
import sys
import csv
from tqdm import tqdm

def get_html_dir() -> Path:
	repo_root = Path(__file__).resolve().parent.parent
	return repo_root / "data" / "data_downloader_whole_content" / "htmls"


def get_output_path() -> Path:
	repo_root = Path(__file__).resolve().parent.parent
	out_dir = repo_root / "data" / "data_downloader_whole_content"
	out_dir.mkdir(parents=True, exist_ok=True)
	return out_dir / "links.csv"


def parse_file(path: Path) -> List[Dict[str, str]]:
	text = path.read_text(encoding="utf-8")
	soup = BeautifulSoup(text, "html.parser")
	items = soup.find_all("li", class_="dataset-item")
	rows: List[Dict[str, str]] = []
	for li in items:
		# organization type
		org_type_span = li.find(class_="organization-type")
		org_type = ""
		if org_type_span:
			org_type = org_type_span.get("data-organization-type") or org_type_span.get_text(strip=True)

		# heading
		heading = ""
		h3 = li.find("h3", class_="dataset-heading")
		if h3:
			a = h3.find("a")
			if a:
				heading = a.get_text(strip=True)

		# dataset organization (owner)
		data_org = ""
		p_org = li.find("p", class_="dataset-organization")
		if p_org:
			data_org = p_org.get_text(strip=True).rstrip("—").strip()

		# description: the first <div> inside notes after the <p>
		desc = ""
		notes = li.find("div", class_="notes")
		if notes:
			# prefer the inner <div> that follows the p
			inner_div = notes.find_all("div")
			if inner_div:
				# join textual contents if multiple
				desc = " ".join(d.get_text(strip=True) for d in inner_div)

		# resources: find csv links inside ul.dataset-resources
		resources = li.find("ul", class_="dataset-resources")
		if resources:
			anchors = resources.find_all("a", href=True)
			for a in anchors:
				# skip "more" links or non-resource anchors
				if "more" in a.get("class", []) or a.get("data-format") == "" :
					continue
				fmt = (a.get("data-format") or "").lower()
				href = a["href"].strip()
				# treat as CSV if data-format says csv OR href looks like a csv file or contains ".csv?"
				is_csv = fmt == "csv" or ".csv" in href.lower()
				if is_csv:
					rows.append({
						"csv_link": href,
						"data_organization": data_org,
						"organization_type": org_type,
						"dataset_heading": heading,
						"dataset_description": desc,
					})
	return rows


def gather_all() -> List[Dict[str, str]]:
	html_dir = get_html_dir()
	if not html_dir.exists():
		print(f"HTML directory not found: {html_dir}")
		return []
	rows: List[Dict[str, str]] = []
	files = sorted(html_dir.glob("*.html"))
	for f in tqdm(files):
		try:
			rows.extend(parse_file(f))
		except Exception as e:
			print(f"Failed parsing {f}: {e}", file=sys.stderr)
	return rows


def write_csv(rows: List[Dict[str, str]], out_path: Path) -> None:
	if not rows:
		# still create an empty CSV with headers
		fields = ["csv_link", "data_organization", "organization_type", "dataset_heading", "dataset_description"]
		with out_path.open("w", encoding="utf-8", newline="") as fh:
			writer = csv.DictWriter(fh, fieldnames=fields)
			writer.writeheader()
		return

	# try pandas first for convenience
	try:
		import pandas as pd

		df = pd.DataFrame(rows)
		# ensure column order
		cols = ["csv_link", "data_organization", "organization_type", "dataset_heading", "dataset_description"]
		df = df.reindex(columns=cols)
		df.to_csv(out_path, index=False)
	except Exception:
		# fallback to csv module
		fields = ["csv_link", "data_organization", "organization_type", "dataset_heading", "dataset_description"]
		with out_path.open("w", encoding="utf-8", newline="") as fh:
			writer = csv.DictWriter(fh, fieldnames=fields)
			writer.writeheader()
			for r in rows:
				writer.writerow({k: (r.get(k) or "") for k in fields})


def main() -> int:
	rows = gather_all()
	out_path = get_output_path()
	write_csv(rows, out_path)
	print(f"Wrote {len(rows)} csv links to {out_path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

