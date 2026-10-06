import json
from pathlib import Path

corpus_path = Path("data/corpus.json")
state_path = Path("data/download_state.json")

if state_path.exists() and corpus_path.exists():
    with open(corpus_path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(state_path, "r", encoding="utf-8") as f:
        old_state = json.load(f)

    failed_ids = set(old_state.get("failed", []))
    marked_unavailable = 0

    for pid, paper in corpus.items():
        # Only mark as 'unavailable' if it is currently 'pending' and failed previously
        if pid in failed_ids and paper["local_files"]["status"] == "pending":
            paper["local_files"]["status"] = "unavailable"
            marked_unavailable += 1

    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    # Now safely delete the legacy download_state.json file
    state_path.unlink()
    print(f"Synced {marked_unavailable} previously failed papers as 'unavailable' in data/corpus.json.")
    print("Deleted redundant data/download_state.json!")