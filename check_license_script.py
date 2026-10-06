import json

with open("stl_expanded_corpus.json", "r", encoding="utf-8") as f:
    corpus = json.load(f)
with open("./dataset_raw/download_state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

downloaded_ids = set(state["latex"]) | set(state["pdf"])

strict_permissive = []  # cc0, cc-by, cc-by-sa
non_commercial_cc = []  # cc-by-nc, cc-by-nc-sa, cc-by-nc-nd
custom_or_unknown = []  # arXiv default license / HAL / university repo

for paper in corpus:
    wid = paper["openalex_id"].split("/")[-1]
    if wid not in downloaded_ids:
        continue

    lics = set(paper.get("licenses") or [])
    if lics & {"cc0", "cc-by", "cc-by-sa"}:
        strict_permissive.append(wid)
    elif any(l.startswith("cc-") for l in lics):
        non_commercial_cc.append(wid)
    else:
        custom_or_unknown.append(wid)

print(f"Total Downloaded: {len(downloaded_ids)}")
print(f"1. Strictly Permissive (CC0 / CC-BY / CC-BY-SA): {len(strict_permissive)}")
print(f"2. Academic / Non-Commercial (CC-BY-NC*):        {len(non_commercial_cc)}")
print(f"3. Custom arXiv / Repo License (Needs TDM/Paraphrasing): {len(custom_or_unknown)}")