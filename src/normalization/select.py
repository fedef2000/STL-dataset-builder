"""
The choice of the formulas that go to stl-nl, among those normalized ok: a formula whose normalized text is the same as
an earlier one is left out (duplicate), and at most `max_per_template` formulas of each template are kept, taken from the
papers in turn (template_cap). Sets `selection` (kept, duplicate, template_cap; None for the other statuses) and
`duplicate_of` on each manifest line.
"""
import collections
import random


def paper_of(line: dict) -> str:
    return line["id"].rsplit(":", 1)[0]


def spread_over_papers(lines: list[dict], limit: int, rng: random.Random) -> list[dict]:
    """`limit` of `lines`, one from each paper in turn: the papers and the formulas of each paper in random order."""
    by_paper = collections.defaultdict(list)
    for line in lines:
        by_paper[paper_of(line)].append(line)
    queues = list(by_paper.values())
    rng.shuffle(queues)
    for queue in queues:
        rng.shuffle(queue)
    chosen = []
    while len(chosen) < limit:
        for queue in queues:
            if queue and len(chosen) < limit:
                chosen.append(queue.pop())
    return chosen


def select(lines: list[dict], max_per_template: int, seed: str):
    """Marks the lines (see the module). `max_per_template` 0: no cap. The seed of a template is `<seed>:<template>`."""
    first_with_text, by_template = {}, collections.defaultdict(list)
    for line in lines:
        line["selection"], line["duplicate_of"] = None, None
        if line["status"] != "ok":
            continue
        if line["normalized"] in first_with_text:
            line["selection"], line["duplicate_of"] = "duplicate", first_with_text[line["normalized"]]
        else:
            first_with_text[line["normalized"]] = line["id"]
            by_template[line["template"]].append(line)
    for template, candidates in by_template.items():
        if max_per_template and len(candidates) > max_per_template:
            chosen = spread_over_papers(candidates, max_per_template, random.Random(f"{seed}:{template}"))
        else:
            chosen = candidates
        chosen_ids = {line["id"] for line in chosen}
        for line in candidates:
            line["selection"] = "kept" if line["id"] in chosen_ids else "template_cap"
