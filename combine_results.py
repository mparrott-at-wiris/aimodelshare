import os
import gzip
import json
import argparse

def combine_chunks_streaming(input_dir, output_file):
    print(f"Starting streaming combine from {input_dir} -> {output_file}...")
    
    # Counter for progress logging
    count = 0
    
    with gzip.open(output_file, "wt", encoding="UTF-8") as f_out:
        # Start the single JSON object
        f_out.write("{")
        
        first_entry = True
        
        # Iterate over all chunk files
        files = [f for f in os.listdir(input_dir) if f.endswith(".jsonl.gz")]
        print(f"Found {len(files)} chunk files to merge.")

        for file_name in sorted(files):
            file_path = os.path.join(input_dir, file_name)
            
            try:
                with gzip.open(file_path, "rt", encoding="UTF-8") as f_in:
                    for line in f_in:
                        if line.strip():
                            try:
                                entry = json.loads(line)
                                k = entry["k"]
                                v = entry["v"]
                                
                                # If this isn't the first item, add a comma separator
                                if not first_entry:
                                    f_out.write(",")
                                else:
                                    first_entry = False
                                
                                # Write "key": "value" directly to stream
                                # json.dumps ensures proper escaping of characters
                                f_out.write(f"{json.dumps(k)}:{json.dumps(v)}")
                                
                                count += 1
                                if count % 100000 == 0:
                                    print(f"Processed {count} records...", flush=True)

                            except json.JSONDecodeError:
                                print(f"⚠️ Warning: Skipping malformed line in {file_name}")
                                continue
            except Exception as e:
                print(f"❌ Error reading file {file_name}: {e}")

        # Close the single JSON object
        f_out.write("}")
    
    print(f"✅ Successfully finished. Total records: {count}")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    combine_chunks_streaming(args.input_dir, args.output_file)
