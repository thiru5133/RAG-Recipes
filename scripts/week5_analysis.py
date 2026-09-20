"""week5_analysis.py — checks the arithmetic behind taxonomy.md and notes.md.

taxonomy.md and notes.md are written by hand, because they are an argument rather
than a report. This file holds the two things in them that a reader should be
able to verify instead of trust: which trace each observation belongs to, and
which traces each mode is counted from.

The order this file is written in is the order the work was done in, and it
refuses to pass if that order was violated:

1. OPEN_CODES holds one observation sentence per sampled trace, written while
   reading, before any grouping existed. It fails if a sampled trace has no
   sentence, or if a sentence names a trace that was never sampled.
2. MODES groups those trace ids afterwards. Every count and percentage printed
   here is computed from the memberships, so a number typed into taxonomy.md
   that does not match shows up when the two are read side by side. It fails if
   the groups overlap or do not account for all 20 traces.
3. The prediction is a constant here, committed before any fix.

    python scripts/week5_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sampling import (  # noqa: E402
    DEMO_SAMPLE_SEED,
    DEMO_SAMPLE_SIZE,
    RANDOM_SAMPLE_SEED,
    RANDOM_SAMPLE_SIZE,
    draw_demo_sample,
    draw_random_sample,
    load_traces,
    population_fingerprint,
    population_report,
)

ANALYSIS_DATE = "2026-09-18"

# Hash of the commit that filed the prediction; see notes.md section 5.
PREDICTION_COMMIT = "2e82edf"

ANNOYS = "merely annoys the cook"

# ── step 1: open coding ──────────────────────────────────────────────────────
# One sentence per trace, describing what was on the screen. Written while
# reading, before any mode existed. No categories, no diagnoses, no fixes, and
# no code was changed between the first sentence and the last. Keyed by the first
# 8 characters of the trace_id, which the checker resolves against the sample so
# a sentence can never drift onto the wrong trace.
OPEN_CODES = {
    "7370504c": (
        "Asked which wine to serve with the shakshuka; the three chunks returned were "
        "R006's method, ingredient and nutrition sections at 0.55 to 0.59, none of them "
        "mentioning a drink, and the reply was the fixed refusal sentence."
    ),
    "a110140c": (
        "The reply reads 'The Shakshuka provides 298 kcal per serving【R006-B06 | R006】', "
        "which is the figure on R006's nutrition table, and the brackets around the "
        "citation are the full-width pair, with the trace's citation list empty and "
        "citation_check valid false."
    ),
    "e4efb2fa": (
        "Asked how much chickpea cooking liquid to reserve; the top chunk was the R002 "
        "method chunk that contains '250 ml', it scored 0.0325, and the reply was the "
        "fixed refusal sentence recorded as score_threshold with no model call made."
    ),
    "8d3a3a6a": (
        "Asked for the butter masala simmering time; five chunks came back scoring 0.0164 "
        "to 0.0323 including R001's method chunk, the reply was the fixed refusal sentence "
        "recorded as score_threshold, and model_params is null because no call happened."
    ),
    "ccb74140": (
        "Asked how many grams of paneer; the three chunks returned were R001's method, "
        "nutrition and notes sections at 0.74 to 0.78, the ingredients table was not among "
        "them, and the model replied with the fixed refusal sentence."
    ),
    "fdceede3": (
        "Asked how much of an unfamiliar paste brand to start with; R004's notes chunk, the "
        "one carrying the 30 g advice, was ranked first at 0.0323 and the reply was the "
        "fixed refusal sentence recorded as score_threshold."
    ),
    "ac25b5bd": (
        "The reply gives 6 to 8 minutes with the detail about the whites being set and the "
        "yolks still moving, cites [R006-A03 | R006] in plain square brackets, and the "
        "citation check passed."
    ),
    "d04bc002": (
        "The reply names extra-firm tofu of the same weight pressed for 30 minutes and stops "
        "there, leaving out the oil-for-butter and coconut-cream swaps written in the same "
        "chunk, and its citation 【R001-B05 | R001】 uses full-width brackets."
    ),
    "2338da4d": (
        "Asked for calories per serving without naming a dish; three nutrition and notes "
        "chunks from three different recipes came back at 0.0164 to 0.0323 and the reply was "
        "the fixed refusal sentence recorded as score_threshold."
    ),
    "9c9db0d4": (
        "The reply reads 'The dough uses 325 ml of water [ R003-A00 | R003 ]'; 325 ml is the "
        "figure on the card, R003-A00 does contain the water row, and each bracket carries a "
        "space inside it, with no citation recorded on the trace."
    ),
    "6a8e7a17": (
        "The reply gives 30 minutes and writes its citation as "
        "[chunk_id: R005-B01 | recipe_id: R005], the same shape as the header line in the "
        "context block, and the trace recorded no citation."
    ),
    "760b9e64": (
        "Asked how much paneer; all five chunks were R001's, scoring 0.0308 to 0.0328 with "
        "the ingredients table at rank 2, and the reply was the fixed refusal sentence "
        "recorded as score_threshold."
    ),
    "f051e419": (
        "Asked which kitchen scale to buy; BM25 returned three recipe chunks scoring 2.55 to "
        "2.96 and two more scoring exactly 0.0000, and the model replied with the fixed "
        "refusal sentence."
    ),
    "fdcb0d08": (
        "The reply gives 2 tablespoons of fish sauce, which matches R004's ingredient table, "
        "and cites [ R004-B01 | R004 ] with a space inside each bracket; no citation was "
        "recorded on the trace."
    ),
    "bf0e4580": (
        "The reply says to simmer breast for only 7 minutes to avoid drying it out and cites "
        "[R004-A04 | R004], which is the notes chunk that says exactly that; the citation "
        "check passed."
    ),
    "a2ee7a80": (
        "Asked for a sourdough starter schedule; five R003 and R006 chunks came back at 0.32 "
        "to 0.59, none of them mentioning a starter, and the reply was the fixed refusal "
        "sentence."
    ),
    "a0425747": (
        "The reply reads 'The recipe calls for **50 g of green curry paste**"
        "【R005-B01 | R005】', with markdown asterisks around the quantity and full-width "
        "brackets around the citation, and no citation was recorded on the trace."
    ),
    "59947af2": (
        "The reply gives 200 g of dried chickpeas and cites [ R002‑A00 | R002 ], where the "
        "brackets are padded with spaces and the hyphen inside the chunk id is a non-ASCII "
        "character rather than a plain one; no citation was recorded."
    ),
    "1197eca6": (
        "The same butter masala simmering question as an earlier trace but with three chunks "
        "instead of five; R001's method chunk sat at rank 2 with 0.0323 and the reply was the "
        "fixed refusal sentence recorded as score_threshold."
    ),
    "b87a58ef": (
        "Asked which wine to serve with the shakshuka; the three chunks returned were R004's "
        "and R001's at 0.27 to 0.32 with no shakshuka chunk at all, and the reply was the "
        "fixed refusal sentence."
    ),
}

# ── step 2: clustering, done after all 20 sentences existed ──────────────────
MODES = [
    {
        "name": (
            "Hybrid search answers nothing: fused scores land near 0.03 and the 0.30 "
            "gate refuses before the model is called"
        ),
        "severity": ANNOYS,
        "members": ["e4efb2fa", "8d3a3a6a", "fdceede3", "2338da4d", "760b9e64", "1197eca6"],
        "example": "e4efb2fa",
    },
    {
        "name": (
            "Citation wrapped in full-width brackets 【 】, so the verifier records no "
            "citation at all"
        ),
        "severity": ANNOYS,
        "members": ["a110140c", "d04bc002", "a0425747"],
        "example": "a110140c",
    },
    {
        "name": (
            "Citation padded with spaces, [ R003-A00 | R003 ], so the verifier records no "
            "citation"
        ),
        "severity": ANNOYS,
        "members": ["9c9db0d4", "fdcb0d08", "59947af2"],
        "example": "9c9db0d4",
    },
    {
        "name": (
            "Citation copied in the context-header form [chunk_id: X | recipe_id: Y], so "
            "the verifier records no citation"
        ),
        "severity": ANNOYS,
        "members": ["6a8e7a17"],
        "example": "6a8e7a17",
    },
    {
        "name": (
            "Refuses a plain ingredient quantity when the ingredients table misses the "
            "top 3"
        ),
        "severity": ANNOYS,
        "members": ["ccb74140"],
        "example": "ccb74140",
    },
]

# Traces where reading turned up nothing wrong. Listed so the modes above plus
# this list must add to 20.
CLEAN = ["7370504c", "ac25b5bd", "f051e419", "bf0e4580", "a2ee7a80", "b87a58ef"]

# ── bonus: the curated demo sample ───────────────────────────────────────────
DEMO_OPEN_CODES = {
    "b7446b8c": (
        "The review question about the oven and stone: five R003 chunks came back with the "
        "two method chunks that carry 250 C at the top, all scoring 0.0299 to 0.0325, and "
        "the reply was the fixed refusal sentence."
    ),
    "bcbc2761": (
        "The reply gives 892 kcal per serving and cites 【R003-B06 | R003】 in full-width "
        "brackets; R003-B06 is the nutrition chunk and no citation was recorded."
    ),
    "e28b0f08": (
        "Asked how much dried chana; five R002 chunks came back scoring 0.0310 to 0.0318 and "
        "the reply was the fixed refusal sentence recorded as score_threshold."
    ),
    "df915db5": (
        "The reply gives 892 kcal citing 【R003-A05 | R003】; that window does contain the "
        "892 row, the brackets are full-width, and no citation was recorded."
    ),
    "8808f714": (
        "Asked how hot to get the stone and for how long; R003's two method chunks ranked "
        "first and second at 0.0328 and 0.0320 and the reply was the fixed refusal sentence."
    ),
    "eaf2e670": (
        "The same calories question as the k=3 run with the same top three chunks plus two "
        "more; the reply is worded 'contains 892 kcal per serving' instead of 'provides', "
        "again with full-width brackets and no recorded citation."
    ),
    "a6cc04ae": (
        "Asked how much curry paste without naming a dish; the vegan ingredients chunk ranked "
        "first at 0.0325 and the chicken one third at 0.0315, and the reply was the fixed "
        "refusal sentence."
    ),
    "3edb4cd3": (
        "The reply gives 200 g of dried chickpeas and cites [ R002-B01 | R002 ] with padded "
        "brackets; R002-B01 holds the 200 g row and no citation was recorded."
    ),
    "156fbe2a": (
        "The reply gives 50 g of green curry paste in markdown bold with a "
        "【R005-A01 | R005】 citation; BM25 scored the top chunk 10.81 and no citation was "
        "recorded."
    ),
    "1585ae45": (
        "The review question about the shakshuka sauce simmer; R006's method chunk ranked "
        "first at 0.0325 and the reply was the fixed refusal sentence."
    ),
}

# Same modes as the taxonomy, by index into MODES.
DEMO_MEMBERS = {
    0: ["b7446b8c", "e28b0f08", "8808f714", "a6cc04ae", "1585ae45"],
    1: ["bcbc2761", "df915db5", "eaf2e670", "156fbe2a"],
    2: ["3edb4cd3"],
}
DEMO_CLEAN: list[str] = []

PREDICTION = {
    "date": ANALYSIS_DATE,
    "mode": MODES[0]["name"],
    "change": (
        "Stop comparing three score scales against one number. The 0.30 gate in "
        "guardrails.below_threshold was calibrated on cosine similarity, but retrieve._rrf_fuse "
        "hands it Reciprocal Rank Fusion scores whose ceiling is 1/(60+1) = 0.0164 per list, so "
        "in hybrid mode the gate can never be cleared. Carry the top hit's cosine similarity "
        "through fusion and gate on that, leaving the 0.30 value untouched."
    ),
    "numbers": (
        "Traces refused at the score gate in hybrid mode drop from 6/20 (30%) to 0/20, and "
        "refusals of answerable questions across all modes drop from 7/20 (35%) to under "
        "3/20 (15%)."
    ),
    "measured_on": (
        "20 traces drawn with random.Random(43).sample(...) from traces collected after the "
        "change, same question bank and same config grid as this run."
    ),
    "falsified_if": (
        "any hybrid-mode trace in that draw is still refused by score_threshold, or 3 or more "
        "answerable questions in the draw are refused by either gate."
    ),
}


def resolve(prefix: str, sample: list[dict], label: str) -> str:
    matches = [t["trace_id"] for t in sample if t["trace_id"].startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(
            f"{label}: prefix {prefix!r} matches {len(matches)} traces in the sample"
        )
    return matches[0]


def check(sample: list[dict], codes: dict[str, str], members: list[list[str]],
          clean: list[str], label: str) -> None:
    prefixes = {t["trace_id"][:8] for t in sample}

    missing = sorted(p for p in prefixes if p not in codes)
    if missing:
        raise SystemExit(f"{label}: no observation sentence for {missing}")

    stray = sorted(p for p in codes if p not in prefixes)
    if stray:
        raise SystemExit(f"{label}: observation for a trace that was not sampled: {stray}")

    seen: dict[str, int] = {}
    for i, group in enumerate(members):
        for p in group:
            resolve(p, sample, label)
            if p in seen:
                raise SystemExit(f"{label}: {p} is in two modes ({seen[p]} and {i})")
            seen[p] = i

    for p in clean:
        resolve(p, sample, label)
        if p in seen:
            raise SystemExit(f"{label}: {p} is listed clean and also in mode {seen[p]}")

    if len(seen) + len(clean) != len(sample):
        raise SystemExit(
            f"{label}: modes ({len(seen)}) + clean ({len(clean)}) = "
            f"{len(seen) + len(clean)}, but the sample holds {len(sample)}"
        )

    if not 4 <= len(members) <= 7:
        raise SystemExit(f"{label}: {len(members)} modes; the brief asks for 4 to 7")


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:.0f}%"


def main() -> None:
    traces = load_traces()
    sample = draw_random_sample(traces)
    demo = draw_demo_sample(traces)

    check(sample, OPEN_CODES, [m["members"] for m in MODES], CLEAN, "random sample")

    # The demo sample is coded against the same modes, so it is checked for
    # complete, non-overlapping membership but not for the 4-to-7 mode count.
    demo_groups = list(DEMO_MEMBERS.values())
    prefixes = {t["trace_id"][:8] for t in demo}
    if sorted(prefixes) != sorted(DEMO_OPEN_CODES):
        raise SystemExit("demo sample: sentences and sampled traces do not line up")
    flat = [p for g in demo_groups for p in g]
    if len(flat) != len(set(flat)) or len(flat) + len(DEMO_CLEAN) != len(demo):
        raise SystemExit("demo sample: modes overlap or do not account for every trace")
    for p in flat:
        resolve(p, demo, "demo sample")

    fp = population_fingerprint()
    rep = population_report()
    n, dn = len(sample), len(demo)

    print(f"population   : {rep['population']} traces "
          f"({rep['records_in_file']} records, {rep['failed_calls_excluded']} failed calls "
          f"excluded)")
    print(f"file sha256  : {fp['sha256']}")
    print(f"random sample: seed {RANDOM_SAMPLE_SEED}, n={RANDOM_SAMPLE_SIZE}")
    print(f"demo sample  : seed {DEMO_SAMPLE_SEED}, n={DEMO_SAMPLE_SIZE}")
    print()

    rows = sorted(
        (
            {
                "i": i,
                "count": len(m["members"]),
                "severity": m["severity"],
                "example": resolve(m["example"], sample, "modes")[:8],
                "name": m["name"],
            }
            for i, m in enumerate(MODES)
        ),
        key=lambda r: -r["count"],
    )

    print(f"{'count':>5} {'freq':>5}  {'demo':>7}  example    mode")
    for r in rows:
        dcount = len(DEMO_MEMBERS.get(r["i"], []))
        demo_cell = f"{dcount}/{dn}" if r["i"] in DEMO_MEMBERS else "-"
        print(f"{r['count']:>5} {pct(r['count'], n):>5}  {demo_cell:>7}  {r['example']}   "
              f"{r['name'][:64]}")
    print(f"{len(CLEAN):>5} {pct(len(CLEAN), n):>5}  {f'{len(DEMO_CLEAN)}/{dn}':>7}  "
          f"{resolve(CLEAN[0], sample, 'clean')[:8]}   no defect seen on reading")
    print()

    defective = sum(r["count"] for r in rows)
    citation = sum(len(MODES[i]["members"]) for i in (1, 2, 3))
    answered = [t for t in sample if not t["refused"]]
    refused_answerable = [
        t for t in sample
        if t["refused"] and (t.get("question_meta") or {}).get("class") == "answerable"
    ]
    print(f"defective            : {defective}/{n} ({pct(defective, n)})")
    print(f"citation modes (1-3) : {citation}/{n} ({pct(citation, n)})")
    print(f"answered             : {len(answered)}/{n}")
    print(f"answerable & refused : {len(refused_answerable)}/{n} "
          f"({pct(len(refused_answerable), n)})")
    print(f"severities used      : {sorted({m['severity'] for m in MODES})}")
    print()
    print("checks passed. taxonomy.md and notes.md must match the numbers above.")
    if PREDICTION_COMMIT == "PENDING":
        print("\nNOTE: PREDICTION_COMMIT is still PENDING; set it once the prediction "
              "is committed.")


if __name__ == "__main__":
    main()
