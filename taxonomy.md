# Week 5 — Failure taxonomy

Recipes & food · 20 traces drawn with seed `42` from 386 real traces · read 2026-09-18 · no code changed while reading

| Failure mode | Count | Freq | Severity | Example trace_id |
| --- | --- | --- | --- | --- |
| Hybrid search answers nothing: fused scores land near 0.03 and the 0.30 gate refuses before the model is called | 6 | 30% | merely annoys the cook — no answer arrives, but nothing wrong is ever said | `e4efb2fa` |
| Citation wrapped in full-width brackets 【 】, so the verifier records no citation at all | 3 | 15% | merely annoys the cook — number and chunk are both right, only the provenance link is lost | `a110140c` |
| Citation padded with spaces, `[ R003-A00 \| R003 ]`, so the verifier records no citation | 3 | 15% | merely annoys the cook — right answer, unverifiable source | `9c9db0d4` |
| Citation copied in the context-header form `[chunk_id: X \| recipe_id: Y]`, so the verifier records no citation | 1 | 5% | merely annoys the cook — right answer, unverifiable source | `6a8e7a17` |
| Refuses a plain ingredient quantity when the ingredients table misses the top 3 | 1 | 5% | merely annoys the cook — a fact printed on the card comes back as "I cannot answer that" | `ccb74140` |
| _no defect seen on reading_ | 6 | 30% | — | `7370504c` |

14 of 20 traces carried a defect. The three citation rows are listed separately because the bracket shapes differ and each needs its own recognition, but they share one consequence — the verifier records no citation — and together they are **7/20 (35%)**.

Not one answered trace in this sample got a quantity wrong: all nine carried the number printed on the card, which is why no row is marked "poisons or ruins the dish". The food editor's report that it "sometimes gets the quantities wrong" is not what these 20 traces show. They show answers that arrive unverifiable, or never arrive at all.

Fix order is the table order: the top row is one mismatched score scale, costs 30% of traces, and is the mode named in the dated prediction.

Sentences, seeds, replay evidence and the prediction: `notes.md`. The prediction was filed 2026-09-18 in commit `2e82edf`, before any fix.
