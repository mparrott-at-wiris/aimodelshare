import itertools
import json

# Define the configuration
ALL_FEATURES = [
    "floor_area", "year_built", "ELEVATION", "heating_degree_days", 
    "cooling_degree_days", "january_min_temp", "july_max_temp", 
    "avg_temp", "april_avg_temp", "october_avg_temp", 
    "facility_type", "building_class", "State_Factor", "Year_Factor"
]
MODEL_TYPES = ["The Balanced Generalist", "The Rule-Maker", "The 'Nearest Neighbor'", "The Deep Pattern-Finder"]
COMPLEXITIES = range(1, 11)  # 1 through 10
DATA_SIZES = ["Small (20%)", "Medium (60%)", "Large (80%)", "Full (100%)"]

def generate_all_tasks():
    all_combos = []
    for r in range(1, len(ALL_FEATURES) + 1):
        all_combos.extend(itertools.combinations(ALL_FEATURES, r))

    tasks = []
    for model in MODEL_TYPES:
        for complexity in COMPLEXITIES:
            for size in DATA_SIZES:
                for features in all_combos:
                    task_key = f"{model}|{complexity}|{size}|{','.join(features)}"
                    tasks.append(task_key)
    return tasks

# Split tasks into `N` chunks
def split_tasks(tasks, num_chunks):
    chunk_size = (len(tasks) + num_chunks - 1) // num_chunks  # Round up
    return [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]

if __name__ == "__main__":
    tasks = generate_all_tasks()
    chunks = split_tasks(tasks, num_chunks=10)  # Split into 10 chunks

    # Write each chunk to a JSON file
    for i, chunk in enumerate(chunks):
        with open(f"task_chunk_{i}.json", "w") as f:
            json.dump(chunk, f)

    print(f"Generated {len(chunks)} task chunks, each with approximately {len(chunks[0])} tasks.")
