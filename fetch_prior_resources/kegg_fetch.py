import pandas as pd
import requests
from pathlib import Path

# -----------------------------
# CONFIG
# -----------------------------
OUTPUT_DIR = Path("kegg_matrices")
OUTPUT_DIR.mkdir(exist_ok=True)

BASE_URL = "https://rest.kegg.jp/link"

# Matrix definitions
TASKS = {
    "gene_pathway": "pathway/hsa",
    "gene_ko": "ko/hsa",
    "gene_compound": "compound/hsa",
    "gene_disease": "disease/hsa",
}

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def fetch_kegg_links(endpoint):
    url = f"{BASE_URL}/{endpoint}"
    print(f"Fetching: {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def parse_kegg_response(text, source_prefix, target_prefix):
    pairs = [line.split("\t") for line in text.strip().split("\n")]
    df = pd.DataFrame(pairs, columns=["gene", "target"])

    # Clean IDs
    df["gene"] = df["gene"].str.replace(f"{source_prefix}:", "", regex=False)
    df["target"] = df["target"].str.replace(f"{target_prefix}:", "", regex=False)

    return df


def build_matrix(df):
    matrix = pd.crosstab(df["gene"], df["target"])
    return matrix


# -----------------------------
# MAIN PIPELINE
# -----------------------------
for name, endpoint in TASKS.items():

    # Step 1: fetch
    raw_text = fetch_kegg_links(endpoint)

    # Step 2: determine prefixes
    target_db = endpoint.split("/")[0]

    prefix_map = {
        "pathway": "path",
        "ko": "ko",
        "compound": "cpd",
        "disease": "ds",
    }

    target_prefix = prefix_map[target_db]

    # Step 3: parse
    df = parse_kegg_response(raw_text, "hsa", target_prefix)

    # Step 4: build matrix
    matrix = build_matrix(df)

    # Step 5: save
    out_file = OUTPUT_DIR / f"{name}.csv"
    matrix.to_csv(out_file)

    print(f"Saved: {out_file} | shape = {matrix.shape}")

print("\n✅ All matrices generated!")