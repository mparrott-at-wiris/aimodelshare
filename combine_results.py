import os
import gzip
import json
from glob import glob

def combine_chunks(input_dir, output_file):
    final_cache = {}

    # Iterate through artifacts
    for file in glob(os.path.join(input_dir, "*.jsonl.gz")):
        print(f"Processing {file}...")
        with gzip.open(file, "rt", encoding="UTF-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    final_cache[entry["k"]] = entry["v"]

    # Save the final combined results
    with gzip.open(output_file, "wt", encoding="UTF-8") as f:
        json.dump(final_cache, f)

    print(f"Final combined results saved at {output_file}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, help="Directory of partial artifacts")
    parser.add_argument("--output-file", required=True, help="File path for final merged JSON")
    args = parser.parse_args()

    combine_chunks(args.input_dir, args.output_file)
