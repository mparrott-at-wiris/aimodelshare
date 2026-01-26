import os
import gzip
import json

def combine_chunks(input_dir, output_file):
    final_cache = {}

    for file in os.listdir(input_dir):
        if file.endswith(".jsonl.gz"):
            with gzip.open(os.path.join(input_dir, file), "rt", encoding="UTF-8") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        final_cache[entry["k"]] = entry["v"]

    with gzip.open(output_file, "wt", encoding="UTF-8") as f:
        json.dump(final_cache, f)

    print(f"Combined results saved at: {output_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, help="Directory containing partial results")
    parser.add_argument("--output-file", required=True, help="Filename for the final combined output file")
    args = parser.parse_args()

    combine_chunks(args.input_dir, args.output_file)
