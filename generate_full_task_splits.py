import itertools
import json
import random

# Configuration
NUM_CHUNKS = 40  
DATA_SIZE = "Full (100%)"

ALL_FEATURES = [
    "floor_area", "year_built", "ELEVATION", "heating_degree_days",
    "cooling_degree_days", "january_min_temp", "july_max_temp",
    "avg_temp", "april_avg_temp", "october_avg_temp",
    "facility_type", "building_class", "State_Factor", "Year_Factor"
]

# Note: We include Majority Vote here because we want to calculate it in parallel too
MODEL_TYPES = [
    "The Balanced Generalist", 
    "The Rule-Maker",
    "The 'Nearest Neighbor'", 
    "The Deep Pattern-Finder",
    "The Majority Vote" 
]
COMPLEXITIES = range(1, 11)

def generate_all_tasks():
    all_combos = []
    for r in range(1, len(ALL_FEATURES) + 1):
        all_combos.extend(itertools.combinations(ALL_FEATURES, r))

    tasks = []
    for model in MODEL_TYPES:
        for complexity in COMPLEXITIES:
            # We only do Full (100%) in this pipeline
            for features in all_combos:
                task_key = f"{model}|{complexity}|{DATA_SIZE}|{','.join(features)}"
                tasks.append(task_key)
    return tasks

def split_tasks(tasks, num_chunks):
    chunk_size = (len(tasks) + num_chunks - 1) // num_chunks
    return [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]

if __name__ == "__main__":
    print("Generating FULL dataset task splits...")
    tasks = generate_all_tasks()
    print(f"Total tasks generated: {len(tasks)}")

    print("Shuffling tasks to distribute load...")
    random.seed(99) # Different seed than previous pipeline just in case
    random.shuffle(tasks)

    chunks = split_tasks(tasks, NUM_CHUNKS)
    for i, chunk in enumerate(chunks):
        with open(f"full_task_chunk_{i}.json", "w") as f:
            json.dump(chunk, f)
        print(f"Chunk {i} saved with {len(chunk)} tasks.")
    
    print(f"Successfully created {len(chunks)} chunk files.")
