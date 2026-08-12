"""The 8 known-answer questions.

`gold_recipes` / `gold_section` are the labels used for Hit-in-Top-5. `markers`
are exact substrings of the source card, used for a stricter secondary check:
did the retrieved chunk actually carry the answer, not merely the right section?
"""

QUESTIONS = [
    {
        "qid": "Q1",
        "question": "How much heavy cream does the paneer butter masala need?",
        "gold_recipes": ["R001"],
        "gold_section": "Ingredients",
        "type": "table",
        "answer": "60 ml, stirred in off the heat",
        "markers": ["Heavy cream | 60 | ml"],
    },
    {
        "qid": "Q2",
        "question": "How many grams of green curry paste are in the vegan green curry?",
        "gold_recipes": ["R005"],
        "gold_section": "Ingredients",
        "type": "table",
        "answer": "50 g",
        "markers": ["Green curry paste | 50 | g"],
    },
    {
        "qid": "Q3",
        "question": "How many grams of dried chickpeas does chana masala use?",
        "gold_recipes": ["R002"],
        "gold_section": "Ingredients",
        "type": "table",
        "answer": "200 g, soaked 8 hours or overnight",
        "markers": ["Dried chickpeas | 200 | g"],
    },
    {
        "qid": "Q4",
        "question": "How many calories per serving does the margherita pizza have?",
        "gold_recipes": ["R003"],
        "gold_section": "Nutrition",
        "type": "table",
        "answer": "892 kcal per serving",
        "markers": ["Energy | 892 | kcal"],
    },
    {
        "qid": "Q5",
        "question": "What temperature should the oven and stone be preheated to for the pizza?",
        "gold_recipes": ["R003"],
        "gold_section": "Method",
        "type": "prose",
        "answer": "250 C (480 F), held for 45 minutes after the oven reaches temperature",
        "markers": ["250 C"],
    },
    {
        "qid": "Q6",
        "question": "What can I use instead of paneer to make the butter masala vegan?",
        "gold_recipes": ["R001"],
        "gold_section": "Notes",
        "type": "prose",
        "answer": "extra-firm tofu, pressed 30 minutes, with coconut cream for the dairy cream",
        "markers": ["extra-firm tofu"],
    },
    {
        "qid": "Q7",
        "question": "How long does the shakshuka sauce simmer before the eggs go in?",
        "gold_recipes": ["R006"],
        "gold_section": "Method",
        "type": "prose",
        "answer": "15 minutes, uncovered, until thick enough to hold a channel",
        "markers": ["15 minutes"],
    },
    {
        "qid": "Q8",
        "question": "How much curry paste do I need?",
        "gold_recipes": ["R004", "R005"],
        "gold_section": "Ingredients",
        "type": "ambiguous",
        "answer": "ambiguous: 45 g in the chicken curry (R004), 50 g in the vegan curry (R005)",
        "markers": ["Green curry paste | 45 | g", "Green curry paste | 50 | g"],
    },
]

TABLE_QIDS = [q["qid"] for q in QUESTIONS if q["type"] == "table"]
