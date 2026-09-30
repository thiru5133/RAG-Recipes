# Week 6 — how to prove it on screen

The Recipe RAG page does not prove this week. That screen retrieves chunks and writes an answer. The judge never runs there.

The proof is one command, then three files.

```bash
python scripts/run_week6.py
```

Do not add `--force`. The saved results are the proof. A fresh model call can change the verdicts.

## What to point at in the terminal

| Line | What it proves |
| --- | --- |
| `cases: 27  assertions: 5  judged criteria: 1` | Code checks units, servings, and warnings. The model is asked one question. |
| `agreement_before: 92.6% (25/27)` | Judge v1 does not match the hand labels. |
| `S05: human=FAIL  judge=PASS` and the same for `S19` | The two mismatches. |
| `agreement_after: 100.0% (27/27)` | Judge v2, with those two cases written into the prompt, matches every label. |
| `S03: faithfulness=1.0  context_precision=0.0` | The rewrite copied the chicken curry. The gold card was the tofu curry. |

## Then open these three files, in this order

1. `eval/week6/labels_25.json` — S05 and S19 are already `human: FAIL`. The file time is 16:10:10Z, before either judge run. That is the blind label.
2. `eval/week6/judge_v1_results.json` — S05 says `VERDICT: PASS` because rice flour "eliminates gluten." S19 does the same for the sourdough starter. The card forbids both.
3. `eval/week6/judge_v2_results.json` — both of those verdicts are `FAIL`. `eval/week6/summary.json` is the scoreboard: 25/27, then 27/27.

While S05 is on screen: the card says the margherita cannot be made gluten-free without changing the dough. v1 trusted general cooking knowledge. v2 was shown that exact mistake and now follows the card. The published pass rate drops from 20/27 to 18/27 because those two free passes are gone.
