"""Labelled answers used to validate the substitution judge.

The judge is not trusted until it agrees with a human on these. Each entry is an
answer to one SUBSTITUTION_CASES question, with the label a careful human reader
gives it by the rubric in `src/judge.py`: PASS only if every required fact is
present, nothing is contradicted or invented, and refusal cases decline.

IMPORTANT: the `label` values below are a DRAFT written against the card text.
Regrade them yourself with `python scripts/validate_judge.py --label`, which
writes eval/judge_labels_user.json; validation uses your labels when that file
exists. The mix is deliberate: clean passes, reworded passes, incomplete
answers, wrong numbers, invented swaps, and refusals both right and wrong.
"""

REFUSAL = "I cannot answer that from the provided recipe cards."

JUDGE_LABELS = [
    # S1 - vegan paneer (three required swaps)
    {"id": "L01", "qid": "S1", "label": "PASS", "why": "all three swaps",
     "answer": "Replace the paneer with the same weight of extra-firm tofu pressed for 30 minutes, swap the butter for a neutral oil, and use thick coconut cream in place of the heavy cream. [R001-B05 | R001]"},
    {"id": "L02", "qid": "S1", "label": "FAIL", "why": "incomplete: tofu only (the T08 failure)",
     "answer": "Use extra-firm tofu of the same weight, pressed for 30 minutes. [R001-B05 | R001]"},
    {"id": "L03", "qid": "S1", "label": "FAIL", "why": "wrong swap, keeps butter",
     "answer": "Use cottage cheese instead of paneer and keep the butter and cream as they are. [R001-B05 | R001]"},
    {"id": "L04", "qid": "S1", "label": "PASS", "why": "reworded but complete",
     "answer": "Swap the paneer for an equal weight of extra-firm tofu (pressed for half an hour), the butter for neutral oil, and the heavy cream for thick coconut cream. [R001-B05 | R001]"},
    {"id": "L05", "qid": "S1", "label": "FAIL", "why": "complete but invents nutritional yeast",
     "answer": "Use extra-firm tofu pressed 30 minutes, neutral oil for the butter, thick coconut cream for the cream, and add 2 tablespoons of nutritional yeast for cheesiness. [R001-B05 | R001]"},
    # S2 - fish sauce
    {"id": "L06", "qid": "S2", "label": "PASS", "why": "correct",
     "answer": "Light soy sauce, 2 tbsp, replaces the fish sauce. [R005-B01 | R005]"},
    {"id": "L07", "qid": "S2", "label": "FAIL", "why": "wrong ingredient",
     "answer": "Use Worcestershire sauce in place of the fish sauce. [R005-B01 | R005]"},
    {"id": "L08", "qid": "S2", "label": "FAIL", "why": "refuses an answerable question",
     "answer": REFUSAL},
    # S3 - vegan shakshuka
    {"id": "L09", "qid": "S3", "label": "PASS", "why": "all three facts",
     "answer": "Omit the eggs and feta, add two 400 g tins of drained chickpeas at step 3, and simmer for 10 minutes. [R006-B05 | R006]"},
    {"id": "L10", "qid": "S3", "label": "FAIL", "why": "missing the 10 minute simmer",
     "answer": "Leave out the eggs and feta and add two 400 g tins of drained chickpeas at step 3. [R006-B05 | R006]"},
    {"id": "L11", "qid": "S3", "label": "FAIL", "why": "wrong quantity and time",
     "answer": "Omit the eggs and feta, add one 400 g tin of chickpeas at step 3 and simmer for 15 minutes. [R006-B05 | R006]"},
    # S4 - amchur
    {"id": "L12", "qid": "S4", "label": "PASS", "why": "correct",
     "answer": "Add one tablespoon of lemon juice off the heat. [R002-B05 | R002]"},
    {"id": "L13", "qid": "S4", "label": "FAIL", "why": "wrong amount",
     "answer": "Add one teaspoon of lemon juice at the start of cooking. [R002-B05 | R002]"},
    {"id": "L14", "qid": "S4", "label": "FAIL", "why": "invented swap",
     "answer": "Use a spoonful of tamarind paste instead of amchur. [R002-B05 | R002]"},
    # S5 - tinned chickpeas
    {"id": "L15", "qid": "S5", "label": "PASS", "why": "all three facts",
     "answer": "Yes: use two 400 g tins, drained, cut the final simmer to 8 minutes, and mash a few more chickpeas because the sauce will be thinner. [R002-B05 | R002]"},
    {"id": "L16", "qid": "S5", "label": "FAIL", "why": "missing the mashing advice",
     "answer": "Yes, use two 400 g tins, drained, and reduce the final simmer to 8 minutes. [R002-B05 | R002]"},
    {"id": "L17", "qid": "S5", "label": "FAIL", "why": "wrong simmer time",
     "answer": "Yes, use two 400 g tins, drained, simmer for 15 minutes and mash a few more chickpeas. [R002-B05 | R002]"},
    # S6 - chicken breast
    {"id": "L18", "qid": "S6", "label": "PASS", "why": "correct",
     "answer": "Simmer breast for only 7 minutes or it will dry out. [R004-A04 | R004]"},
    {"id": "L19", "qid": "S6", "label": "FAIL", "why": "wrong time",
     "answer": "Simmer breast for 10 minutes. [R004-A04 | R004]"},
    # S7 - aubergine
    {"id": "L20", "qid": "S7", "label": "PASS", "why": "correct",
     "answer": "Yes, regular aubergine cut into 2 cm cubes is a fine substitute. [R004-A04 | R004]"},
    {"id": "L21", "qid": "S7", "label": "FAIL", "why": "refuses an answerable question",
     "answer": REFUSAL},
    # S8 - tempeh
    {"id": "L22", "qid": "S8", "label": "PASS", "why": "both facts",
     "answer": "Yes, tempeh works in place of tofu and needs no pressing. [R005-A04 | R005]"},
    {"id": "L23", "qid": "S8", "label": "FAIL", "why": "contradicts the card on pressing",
     "answer": "Yes, but press the tempeh for 30 minutes first. [R005-A04 | R005]"},
    # S9 - 220 C oven
    {"id": "L24", "qid": "S9", "label": "PASS", "why": "all three facts",
     "answer": "Yes, it still works but needs 10 to 12 minutes and gives a drier crust; switching on the grill for the final minute helps. [R003-A04 | R003]"},
    {"id": "L25", "qid": "S9", "label": "FAIL", "why": "contradicts the card",
     "answer": "No, the pizza needs the oven to reach 250 C or it will not cook. [R003-A04 | R003]"},
    # S10 - cashews
    {"id": "L26", "qid": "S10", "label": "PASS", "why": "correct",
     "answer": "Replace them with 2 tablespoons of soaked melon seeds. [R001-B05 | R001]"},
    {"id": "L27", "qid": "S10", "label": "FAIL", "why": "contradicts the card",
     "answer": "Just leave them out; they are optional. [R001-B05 | R001]"},
    # S11 / S12 - traps, the correct behaviour is to decline
    {"id": "L28", "qid": "S11", "label": "PASS", "why": "exact refusal",
     "answer": REFUSAL},
    {"id": "L29", "qid": "S11", "label": "FAIL", "why": "invents a substitution",
     "answer": "Yes, almond milk works well, use the same 400 ml. [R005-B01 | R005]"},
    {"id": "L30", "qid": "S11", "label": "PASS", "why": "declines with an explanation",
     "answer": "The recipe cards do not list a substitute for coconut milk, so I cannot say whether almond milk would work."},
    {"id": "L31", "qid": "S12", "label": "PASS", "why": "exact refusal",
     "answer": REFUSAL},
    {"id": "L32", "qid": "S12", "label": "FAIL", "why": "invents a substitution",
     "answer": "Use a little grated lime zest in place of the makrut lime leaves. [R004-B01 | R004]"},
]
