"""Substitution / adaptation test cases (Track B: the substitution judge).

`required_facts` are what a correct answer must say; `reference` is the exact
card text the facts come from, shown to the judge so it can also catch invented
details. `expected_behaviour` is "refuse" for the traps: questions that look like
substitutions but whose answer is not on any card, where the right move is to
decline rather than invent a swap.

S1 is the trace T08 failure from week 5: the answer named tofu and stopped,
leaving out the oil and coconut-cream swaps in the same chunk.
"""

R001_NOTES = (
    "To make this dish vegan, replace the paneer with the same weight of extra-firm tofu "
    "pressed for 30 minutes, swap the butter for a neutral oil, and use thick coconut "
    "cream in place of the heavy cream. The cashews are structural rather than optional: "
    "they are what gives the gravy its body, so do not omit them without replacing them "
    "with 2 tablespoons of soaked melon seeds."
)

SUBSTITUTION_CASES = [
    {
        "qid": "S1",
        "question": "What can I use instead of paneer to make the butter masala vegan?",
        "gold_recipes": ["R001"],
        "required_facts": [
            "extra-firm tofu replaces the paneer (same weight, pressed 30 minutes)",
            "a neutral oil replaces the butter",
            "thick coconut cream replaces the heavy cream",
        ],
        "reference": R001_NOTES,
        "expected_behaviour": "answer",
        "from_trace": "T08",
    },
    {
        "qid": "S2",
        "question": "What replaces the fish sauce in the vegan green curry?",
        "gold_recipes": ["R005"],
        "required_facts": ["light soy sauce (2 tbsp) replaces the fish sauce"],
        "reference": "| Light soy sauce | 2 | tbsp | replaces fish sauce |",
        "expected_behaviour": "answer",
    },
    {
        "qid": "S3",
        "question": "How do I make the shakshuka vegan?",
        "gold_recipes": ["R006"],
        "required_facts": [
            "omit the eggs and the feta",
            "add two 400 g tins of drained chickpeas at step 3",
            "simmer for 10 minutes",
        ],
        "reference": (
            "For a vegan version, omit the eggs and feta and add two 400 g tins of drained "
            "chickpeas at step 3, simmering for 10 minutes."
        ),
        "expected_behaviour": "answer",
    },
    {
        "qid": "S4",
        "question": "What can I use instead of amchur in the chana masala?",
        "gold_recipes": ["R002"],
        "required_facts": ["1 tablespoon of lemon juice, added off the heat"],
        "reference": (
            "If you have no amchur, one tablespoon of lemon juice added off the heat gives "
            "a comparable sourness."
        ),
        "expected_behaviour": "answer",
    },
    {
        "qid": "S5",
        "question": "Can I use tinned chickpeas for the chana masala, and what changes?",
        "gold_recipes": ["R002"],
        "required_facts": [
            "two 400 g tins, drained",
            "reduce the final simmer to 8 minutes",
            "mash a few more chickpeas because the sauce is thinner",
        ],
        "reference": (
            "Tinned chickpeas work in a hurry: use two 400 g tins, drained, and reduce the "
            "final simmer to 8 minutes. The sauce will be thinner because you lose the starchy "
            "cooking water, so mash a few more chickpeas to compensate."
        ),
        "expected_behaviour": "answer",
    },
    {
        "qid": "S6",
        "question": "If I use chicken breast instead of thigh, how long do I simmer it?",
        "gold_recipes": ["R004"],
        "required_facts": ["simmer for 7 minutes or it dries out"],
        "reference": "Chicken breast can replace thigh but reduce the simmer to 7 minutes or it will dry out.",
        "expected_behaviour": "answer",
    },
    {
        "qid": "S7",
        "question": "Can I use regular aubergine instead of Thai aubergine in the chicken green curry?",
        "gold_recipes": ["R004"],
        "required_facts": ["yes, regular aubergine cut into 2 cm cubes"],
        "reference": (
            "Regular aubergine cut into 2 cm cubes is a fine substitute for Thai aubergines."
        ),
        "expected_behaviour": "answer",
    },
    {
        "qid": "S8",
        "question": "Can I use tempeh instead of tofu in the vegan green curry?",
        "gold_recipes": ["R005"],
        "required_facts": ["yes, tempeh works in place of tofu", "it needs no pressing"],
        "reference": (
            "Tempeh works in place of tofu and needs no pressing, though the flavour is nuttier."
        ),
        "expected_behaviour": "answer",
    },
    {
        "qid": "S9",
        "question": "My oven only reaches 220 C. Can I still make the margherita pizza?",
        "gold_recipes": ["R003"],
        "required_facts": [
            "yes, but it needs 10 to 12 minutes",
            "the crust will be drier",
            "switch on the grill for the final minute",
        ],
        "reference": (
            "A domestic oven that only reaches 220 C will still work but needs 10 to 12 minutes "
            "and produces a drier crust. Switching on the grill for the final minute helps."
        ),
        "expected_behaviour": "answer",
    },
    {
        "qid": "S10",
        "question": "What can I use if I do not have cashews for the paneer butter masala?",
        "gold_recipes": ["R001"],
        "required_facts": ["2 tablespoons of soaked melon seeds"],
        "reference": R001_NOTES,
        "expected_behaviour": "answer",
    },
    # --- traps: the card has no such substitution, the correct move is to decline ---
    {
        "qid": "S11",
        "question": "Can I use almond milk instead of the coconut milk in the green curry?",
        "gold_recipes": ["R004", "R005"],
        "required_facts": [],
        "reference": "(Neither green curry card lists a substitute for coconut milk.)",
        "expected_behaviour": "refuse",
    },
    {
        "qid": "S12",
        "question": "What can I substitute for makrut lime leaves in the green curry?",
        "gold_recipes": ["R004", "R005"],
        "required_facts": [],
        "reference": "(Neither green curry card lists a substitute for makrut lime leaves.)",
        "expected_behaviour": "refuse",
    },
]
