"""Week 6 substitution eval set.

27 cases. Each carries one Week-5 taxonomy mode so pass rate is sliced the
same way the error analysis was, not as a single average that can hide an
allergen regression behind a flavour win.

Two cases are regression fixtures: the question and the raw output are copied
verbatim from the Week-5 traces named in notes.md (T08 / T06). They are not
re-generated.

`frozen_text` is the substitution the judge scores. Regenerating it invalidates
the blind labels; `scripts/run_week6.py` hashes this field and checks it against
labels_25.json.
"""

# Week-5 taxonomy.md rows, short names used as the `mode` tag.
HYBRID_SEARCH_GATE = "hybrid_search_gate"
CITATION_FULLWIDTH = "citation_fullwidth"
CITATION_PADDED = "citation_padded"
CITATION_HEADER = "citation_header"
INGREDIENT_TABLE_MISS = "ingredient_table_miss"
NO_DEFECT = "no_defect"

MODES = [
    HYBRID_SEARCH_GATE,
    CITATION_FULLWIDTH,
    CITATION_PADDED,
    CITATION_HEADER,
    INGREDIENT_TABLE_MISS,
    NO_DEFECT,
]

# Extra slice so allergen-safety cannot hide inside a Week-5 mode that is
# mostly flavour swaps. Printed next to pass-rate-by-mode; not a replacement.
ALLERGEN_SAFETY = "allergen_safety"
FLAVOUR_PLAUSIBILITY = "flavour_plausibility"
STRUCTURAL_SWAP = "structural_swap"
RETRIEVAL_REGRESSION = "retrieval_regression"


def _block(constraint, recipe, servings, warning, ingredients, method, oven="none"):
    ing = "\n".join(f"- {line}" for line in ingredients)
    meth = method if isinstance(method, str) else "\n".join(method)
    return (
        f"CONSTRAINT: {constraint}\n"
        f"RECIPE: {recipe}\n"
        f"SERVINGS: {servings}\n"
        f"ALLERGEN_WARNING: {warning}\n"
        f"INGREDIENTS:\n{ing}\n"
        f"METHOD:\n{meth}\n"
        f"OVEN: {oven}\n"
    )


# ── R001 vegan / dairy-free / nut-free ingredient sets ──────────────────────

_R001_VEGAN = [
    "extra-firm tofu | 400 | g | pressed 30 minutes, 2 cm cubes",
    "Ripe tomatoes | 600 | g | roughly chopped",
    "Raw cashews | 20 | g | soaked in hot water 15 minutes",
    "Neutral oil | 50 | g | divided, half for searing",
    "Coconut cream | 60 | ml | stirred in at the end, off the heat",
    "Onion | 1 | medium | finely sliced",
    "Garlic cloves | 4 | cloves | crushed",
    "Fresh ginger | 15 | g | grated",
    "Kashmiri chilli powder | 1.5 | tsp | for colour, not heat",
    "Garam masala | 1 | tsp | added late",
    "Dried fenugreek leaves | 1 | tsp | crushed between the palms",
    "Granulated sugar | 1 | tsp | balances the tomato acidity",
    "Salt | 1.5 | tsp | to taste",
    "Water | 150 | ml | for loosening the gravy",
]

_R001_VEGAN_METHOD = [
    "1. Soak the cashews in hot water for 15 minutes, then drain.",
    "2. Heat half the oil and sear the extra-firm tofu 2 minutes per side; lift out.",
    "3. Soften the onion 8 minutes, then garlic and ginger 2 minutes.",
    "4. Add the tomatoes, chilli powder, sugar and salt; cover 15 minutes.",
    "5. Blend with the drained cashews, sieve back into the pan.",
    "6. Add the water and simmer 20 minutes.",
    "7. Stir in remaining oil, garam masala and fenugreek leaves.",
    "8. Return the extra-firm tofu, warm 3 minutes, take off the heat, stir in the coconut cream.",
]

_R001_NUTFREE = [
    "extra-firm tofu | 400 | g | pressed 30 minutes, 2 cm cubes",
    "Ripe tomatoes | 600 | g | roughly chopped",
    "melon seeds | 2 | tbsp | soaked, replacing cashews",
    "Neutral oil | 50 | g | divided, half for searing",
    "Coconut cream | 60 | ml | stirred in at the end, off the heat",
    "Onion | 1 | medium | finely sliced",
    "Garlic cloves | 4 | cloves | crushed",
    "Fresh ginger | 15 | g | grated",
    "Kashmiri chilli powder | 1.5 | tsp | for colour, not heat",
    "Garam masala | 1 | tsp | added late",
    "Dried fenugreek leaves | 1 | tsp | crushed between the palms",
    "Granulated sugar | 1 | tsp | to taste",
    "Salt | 1.5 | tsp | to taste",
    "Water | 150 | ml | for loosening the gravy",
]

_R001_NUTFREE_METHOD = [
    "1. Soak the melon seeds in hot water for 15 minutes, then drain.",
    "2. Heat half the oil and sear the extra-firm tofu 2 minutes per side; lift out.",
    "3. Soften the onion 8 minutes, then garlic and ginger 2 minutes.",
    "4. Add the tomatoes, chilli powder, sugar and salt; cover 15 minutes.",
    "5. Blend with the drained melon seeds, sieve back into the pan.",
    "6. Add the water and simmer 20 minutes.",
    "7. Stir in remaining oil, garam masala and fenugreek leaves.",
    "8. Return the extra-firm tofu, warm 3 minutes, take off the heat, stir in the coconut cream.",
]


CASES = [
    # ── allergen_safety ─────────────────────────────────────────────────────
    {
        "qid": "S01",
        "mode": NO_DEFECT,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "Make the paneer butter masala nut-free for a cashew allergy.",
        "constraint": "nut-free (cashew allergy)",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": (
            "To make this dish vegan, replace the paneer with extra-firm tofu. "
            "The cashews are structural rather than optional: they are what gives "
            "the gravy its body, so do not omit them without replacing them with "
            "2 tablespoons of soaked melon seeds."
        ),
        "frozen_text": _block(
            "nut-free (cashew allergy)",
            "Paneer Butter Masala (R001)",
            4,
            "contains-nuts (cashews); contains-dairy",
            [
                "extra-firm tofu | 400 | g | pressed 30 minutes, 2 cm cubes",
                "Ripe tomatoes | 600 | g | roughly chopped",
                "Raw cashews | 20 | g | soaked in hot water 15 minutes",
                "Unsalted butter | 50 | g | divided",
                "Heavy cream | 60 | ml | stirred in at the end",
                "Onion | 1 | medium | finely sliced",
                "Garlic cloves | 4 | cloves | crushed",
                "Fresh ginger | 15 | g | grated",
                "Kashmiri chilli powder | 1.5 | tsp |",
                "Garam masala | 1 | tsp |",
                "Dried fenugreek leaves | 1 | tsp |",
                "Granulated sugar | 1 | tsp |",
                "Salt | 1.5 | tsp |",
                "Water | 150 | ml |",
            ],
            [
                "1. Soak the cashews in hot water for 15 minutes, then drain.",
                "2. Melt half the butter and sear the extra-firm tofu; lift out.",
                "3. Soften the onion, garlic and ginger.",
                "4. Cook the tomatoes with chilli powder, sugar and salt.",
                "5. Blend with the drained cashews and sieve.",
                "6. Add the water and simmer 20 minutes.",
                "7. Finish with butter, garam masala, fenugreek leaves, extra-firm tofu and heavy cream.",
            ],
        ),
    },
    {
        "qid": "S02",
        "mode": NO_DEFECT,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "Make paneer butter masala dairy-free but I can eat nuts.",
        "constraint": "dairy-free",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": (
            "To make this dish vegan, replace the paneer with the same weight of "
            "extra-firm tofu pressed for 30 minutes, swap the butter for a neutral "
            "oil, and use thick coconut cream in place of the heavy cream. The "
            "cashews are structural rather than optional."
        ),
        "frozen_text": _block(
            "dairy-free",
            "Paneer Butter Masala (R001)",
            4,
            "contains-nuts (cashews)",
            _R001_VEGAN,
            _R001_VEGAN_METHOD,
        ),
    },
    {
        "qid": "S03",
        "mode": INGREDIENT_TABLE_MISS,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "Vegan substitute for fish sauce in the tofu green curry.",
        "constraint": "vegan (no fish sauce, no shrimp paste)",
        "recipe_id": "R005",
        "recipe_title": "Vegan Thai Green Curry with Tofu",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "basic",
        "k": 3,
        "gold_recipe": "R005",
        "retrieved_recipe_ids": ["R004", "R004", "R001"],
        "context": (
            "Thai Green Curry with Chicken (R004). Servings: 4. "
            "Chicken thigh 500 g, boneless, sliced 1 cm thick. "
            "Green curry paste 45 g, about 3 tablespoons. "
            "Coconut milk 400 ml full fat. Coconut cream 100 ml. "
            "Fish sauce 2 tbsp, the primary salt source. Palm sugar 1.5 tbsp. "
            "Thai aubergines 150 g quartered. Bamboo shoots 100 g drained. "
            "Makrut lime leaves 4 leaves torn. Thai basil 1 handful. "
            "Red chilli 1 whole sliced. Chicken stock 100 ml. "
            "Spoon the thick coconut cream into a hot wok and boil until it splits. "
            "Add the green curry paste and fry for 3 minutes. "
            "Add the chicken and turn it in the paste for 2 minutes. "
            "Pour in the remaining coconut milk and the stock, add the aubergines, "
            "bamboo shoots and lime leaves. Simmer gently for 12 minutes. "
            "Season with the fish sauce and palm sugar. Take off the heat, stir "
            "through the Thai basil. This dish contains fish sauce and is not "
            "suitable for vegetarians or vegans; see the tofu version."
        ),
        "frozen_text": _block(
            "vegan (no fish sauce, no shrimp paste)",
            "Thai Green Curry with Chicken (R004)",
            4,
            "contains-fish",
            [
                "Chicken thigh | 500 | g | boneless, sliced 1 cm thick",
                "Green curry paste | 45 | g | about 3 tablespoons",
                "Coconut milk | 400 | ml | full fat",
                "Coconut cream | 100 | ml | skimmed from the top of the tin",
                "Fish sauce | 2 | tbsp | the primary salt source",
                "Palm sugar | 1.5 | tbsp | shaved",
                "Thai aubergines | 150 | g | quartered",
                "Bamboo shoots | 100 | g | drained",
                "Makrut lime leaves | 4 | leaves | torn",
                "Thai basil | 1 | handful | added off the heat",
                "Red chilli | 1 | whole | sliced",
                "Chicken stock | 100 | ml |",
            ],
            [
                "1. Boil the coconut cream until it splits.",
                "2. Fry the green curry paste 3 minutes.",
                "3. Add the chicken and coat 2 minutes.",
                "4. Pour in coconut milk and chicken stock; add aubergines, bamboo shoots and lime leaves.",
                "5. Simmer gently for 12 minutes.",
                "6. Season with the fish sauce and palm sugar.",
                "7. Take off the heat and stir through Thai basil.",
            ],
        ),
    },
    {
        "qid": "S04",
        "mode": NO_DEFECT,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "Make the shakshuka vegan — no eggs, no feta.",
        "constraint": "vegan (no eggs, no feta)",
        "recipe_id": "R006",
        "recipe_title": "Shakshuka",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R006",
        "retrieved_recipe_ids": ["R006", "R006", "R006"],
        "context": (
            "For a vegan version, omit the eggs and feta and add two 400 g tins "
            "of drained chickpeas at step 3, simmering for 10 minutes. Servings: 4."
        ),
        "frozen_text": _block(
            "vegan (no eggs, no feta)",
            "Shakshuka (R006)",
            4,
            "none",
            [
                "chickpeas | 800 | g | two 400 g tins, drained",
                "Red bell peppers | 2 | whole | sliced into strips",
                "Ripe tomatoes | 600 | g | chopped",
                "Onion | 1 | large | sliced",
                "Garlic cloves | 4 | cloves | sliced",
                "Sweet paprika | 2 | tsp |",
                "Ground cumin | 1 | tsp |",
                "Caraway seeds | 0.5 | tsp | lightly crushed",
                "Cayenne pepper | 0.25 | tsp | optional",
                "Olive oil | 3 | tbsp |",
                "Fresh parsley | 1 | handful | chopped",
                "Salt | 1 | tsp | to taste",
            ],
            [
                "1. Heat the olive oil and cook the onion and peppers 12 minutes.",
                "2. Add garlic, paprika, cumin, caraway and cayenne; fry 1 minute.",
                "3. Add the tomatoes, salt and the chickpeas; simmer 10 minutes until thick.",
                "4. Scatter over the parsley and serve.",
            ],
        ),
    },
    {
        "qid": "S05",
        "mode": CITATION_PADDED,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "I cannot eat gluten. Rewrite the margherita pizza gluten-free.",
        "constraint": "gluten-free",
        "recipe_id": "R003",
        "recipe_title": "Classic Margherita Pizza",
        "servings_expected": 2,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R003",
        "retrieved_recipe_ids": ["R003", "R003", "R003"],
        "context": (
            "This recipe contains gluten and dairy and cannot be made gluten-free "
            "without changing the dough entirely. Preheat to 250 C (480 F). Servings: 2."
        ),
        "frozen_text": _block(
            "gluten-free",
            "Classic Margherita Pizza (R003)",
            2,
            "contains-dairy",
            [
                "rice flour | 500 | g | 1:1 swap for Type 00 flour",
                "Water | 325 | ml | at 20 C",
                "Fine sea salt | 12 | g |",
                "Fresh yeast | 3 | g |",
                "San Marzano tomatoes | 400 | g | tinned whole",
                "Fresh mozzarella | 250 | g | torn and drained 30 minutes",
                "Fresh basil leaves | 12 | leaves |",
                "Extra virgin olive oil | 2 | tbsp |",
                "rice flour | 2 | tbsp | for launching, replacing semolina",
            ],
            [
                "1. Mix the rice flour, water and yeast; rest 20 minutes. Add salt and knead 8 minutes. [ R003-B03 | R003 ]",
                "2. Bulk ferment 2 hours, divide, refrigerate 24 hours.",
                "3. Preheat the oven and stone to 250 C (480 F) for 45 minutes.",
                "4. Stretch, sauce, mozzarella; bake 6 to 8 minutes.",
                "5. Finish with basil leaves and olive oil.",
            ],
            oven="250 C (480 F)",
        ),
    },
    {
        "qid": "S06",
        "mode": NO_DEFECT,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "Keep the vegan green curry vegan — I only have supermarket green curry paste.",
        "constraint": "vegan (paste must not contain shrimp or fish sauce)",
        "recipe_id": "R005",
        "recipe_title": "Vegan Thai Green Curry with Tofu",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R005",
        "retrieved_recipe_ids": ["R005", "R005", "R005"],
        "context": (
            "Read the curry paste label carefully. Most supermarket green curry "
            "pastes contain shrimp paste or fish sauce and are not vegan. "
            "Light soy sauce 2 tbsp replaces fish sauce, plus 1 tsp white miso."
        ),
        "frozen_text": _block(
            "vegan (paste must not contain shrimp or fish sauce)",
            "Vegan Thai Green Curry with Tofu (R005)",
            4,
            "none",
            [
                "Extra-firm tofu | 400 | g | pressed 30 minutes, cubed",
                "vegan green curry paste | 50 | g | certified vegan, no shrimp paste",
                "Coconut milk | 400 | ml | full fat",
                "Coconut cream | 100 | ml | skimmed from the top of the tin",
                "Light soy sauce | 2 | tbsp | replaces fish sauce",
                "White miso paste | 1 | tsp | for savoury depth",
                "Palm sugar | 1.5 | tbsp | shaved",
                "Thai aubergines | 150 | g | quartered",
                "Bamboo shoots | 100 | g | drained",
                "Makrut lime leaves | 4 | leaves | torn",
                "Thai basil | 1 | handful |",
                "Vegetable stock | 100 | ml |",
                "Neutral oil | 2 | tbsp | for searing the tofu",
            ],
            [
                "1. Press the extra-firm tofu 30 minutes, cube it.",
                "2. Sear the extra-firm tofu in the oil; lift out.",
                "3. Boil the coconut cream until it splits.",
                "4. Fry the vegan green curry paste 3 minutes; whisk in white miso paste.",
                "5. Add coconut milk, vegetable stock, aubergines, bamboo shoots, lime leaves.",
                "6. Simmer 10 minutes, return extra-firm tofu 5 minutes.",
                "7. Season with light soy sauce and palm sugar; add Thai basil off the heat.",
            ],
        ),
    },
    {
        "qid": "S07",
        "mode": NO_DEFECT,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "Nut-free AND vegan paneer butter masala. I have melon seeds.",
        "constraint": "vegan and nut-free",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": (
            "Replace paneer with extra-firm tofu, butter with oil, cream with "
            "coconut cream. Do not omit cashews without replacing them with "
            "2 tablespoons of soaked melon seeds."
        ),
        "frozen_text": _block(
            "vegan and nut-free",
            "Paneer Butter Masala (R001)",
            4,
            "none",
            _R001_NUTFREE,
            _R001_NUTFREE_METHOD,
        ),
    },
    # ── flavour_plausibility ────────────────────────────────────────────────
    {
        "qid": "S08",
        "mode": NO_DEFECT,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "No amchur — what do I substitute in the chana masala?",
        "constraint": "replace amchur, keep the sour finish",
        "recipe_id": "R002",
        "recipe_title": "Chana Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R002",
        "retrieved_recipe_ids": ["R002", "R002", "R002"],
        "context": (
            "If you have no amchur, one tablespoon of lemon juice added off the "
            "heat gives a comparable sourness. Servings: 4. Vegan, nut-free."
        ),
        "frozen_text": _block(
            "replace amchur, keep the sour finish",
            "Chana Masala (R002)",
            4,
            "none",
            [
                "Dried chickpeas | 200 | g | soaked 8 hours",
                "Onion | 2 | medium | finely chopped",
                "Ripe tomatoes | 400 | g | grated",
                "Garlic cloves | 5 | cloves | minced",
                "Fresh ginger | 20 | g | julienned",
                "Green chillies | 2 | whole | slit lengthways",
                "Cumin seeds | 1 | tsp | toasted whole",
                "Coriander powder | 2 | tsp |",
                "lemon juice | 1 | tbsp | off the heat, replaces amchur",
                "Turmeric | 0.5 | tsp |",
                "Garam masala | 1 | tsp |",
                "Neutral oil | 3 | tbsp |",
                "Salt | 2 | tsp |",
                "Fresh coriander | 1 | handful |",
            ],
            [
                "1. Boil the chickpeas 45 to 55 minutes. Reserve 250 ml cooking liquid.",
                "2. Toast cumin seeds in the oil 30 seconds.",
                "3. Fry the onion 10 minutes, then garlic, ginger and green chillies.",
                "4. Add tomatoes, turmeric, coriander powder and salt; cook 12 minutes.",
                "5. Add chickpeas and cooking liquid; simmer 15 minutes.",
                "6. Finish with garam masala, lemon juice off the heat, and fresh coriander.",
            ],
        ),
    },
    {
        "qid": "S09",
        "mode": CITATION_FULLWIDTH,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "If I use chicken breast instead of thigh, how do I rewrite the green curry?",
        "constraint": "chicken breast instead of thigh",
        "recipe_id": "R004",
        "recipe_title": "Thai Green Curry with Chicken",
        "servings_expected": 4,
        "search_mode": "bm25",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R004",
        "retrieved_recipe_ids": ["R004", "R004", "R004"],
        "context": (
            "Chicken breast can replace thigh but reduce the simmer to 7 minutes "
            "or it will dry out. Simmer gently for 12 minutes is the thigh time."
        ),
        "frozen_text": _block(
            "chicken breast instead of thigh",
            "Thai Green Curry with Chicken (R004)",
            4,
            "contains-fish",
            [
                "Chicken breast | 500 | g | boneless, sliced 1 cm thick",
                "Green curry paste | 45 | g | about 3 tablespoons",
                "Coconut milk | 400 | ml | full fat",
                "Coconut cream | 100 | ml |",
                "Fish sauce | 2 | tbsp |",
                "Palm sugar | 1.5 | tbsp |",
                "Thai aubergines | 150 | g | quartered",
                "Bamboo shoots | 100 | g | drained",
                "Makrut lime leaves | 4 | leaves |",
                "Thai basil | 1 | handful |",
                "Red chilli | 1 | whole |",
                "Chicken stock | 100 | ml |",
            ],
            [
                "1. Split the coconut cream in a hot wok.",
                "2. Fry the green curry paste 3 minutes.",
                "3. Coat the chicken breast in the paste 2 minutes.",
                "4. Add coconut milk, chicken stock, aubergines, bamboo shoots, lime leaves.",
                "5. Simmer gently for 7 minutes so the chicken breast does not dry out. 【R004-B04 | R004】",
                "6. Season with fish sauce and palm sugar; finish with Thai basil.",
            ],
        ),
    },
    {
        "qid": "S10",
        "mode": CITATION_PADDED,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "I only have tinned chickpeas for the chana masala.",
        "constraint": "tinned chickpeas instead of dried",
        "recipe_id": "R002",
        "recipe_title": "Chana Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R002",
        "retrieved_recipe_ids": ["R002", "R002", "R002"],
        "context": (
            "Tinned chickpeas work in a hurry: use two 400 g tins, drained, and "
            "reduce the final simmer to 8 minutes. Mash a few more chickpeas."
        ),
        "frozen_text": _block(
            "tinned chickpeas instead of dried",
            "Chana Masala (R002)",
            4,
            "none",
            [
                "tinned chickpeas | 800 | g | two 400 g tins, drained",
                "Onion | 2 | medium | finely chopped",
                "Ripe tomatoes | 400 | g | grated",
                "Garlic cloves | 5 | cloves | minced",
                "Fresh ginger | 20 | g | julienned",
                "Green chillies | 2 | whole | slit",
                "Cumin seeds | 1 | tsp |",
                "Coriander powder | 2 | tsp |",
                "Amchur | 1 | tsp |",
                "Turmeric | 0.5 | tsp |",
                "Garam masala | 1 | tsp |",
                "Neutral oil | 3 | tbsp |",
                "Salt | 2 | tsp |",
                "Fresh coriander | 1 | handful |",
            ],
            [
                "1. Skip the dried soak. Drain the tinned chickpeas. [ R002-B03 | R002 ]",
                "2. Toast cumin seeds in the oil; fry onion, garlic, ginger, green chillies.",
                "3. Cook tomatoes with turmeric, coriander powder and salt 12 minutes.",
                "4. Add tinned chickpeas and simmer 8 minutes, mashing extra chickpeas to thicken.",
                "5. Finish with garam masala, amchur and fresh coriander.",
            ],
        ),
    },
    {
        "qid": "S11",
        "mode": CITATION_HEADER,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "No Thai aubergines — substitute in the chicken green curry.",
        "constraint": "regular aubergine for Thai aubergines",
        "recipe_id": "R004",
        "recipe_title": "Thai Green Curry with Chicken",
        "servings_expected": 4,
        "search_mode": "bm25",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R004",
        "retrieved_recipe_ids": ["R004", "R004", "R004"],
        "context": (
            "Regular aubergine cut into 2 cm cubes is a fine substitute for Thai "
            "aubergines. Chicken thigh 500 g. Servings: 4."
        ),
        "frozen_text": _block(
            "regular aubergine for Thai aubergines",
            "Thai Green Curry with Chicken (R004)",
            4,
            "contains-fish",
            [
                "Chicken thigh | 500 | g | boneless, sliced 1 cm thick",
                "Green curry paste | 45 | g |",
                "Coconut milk | 400 | ml |",
                "Coconut cream | 100 | ml |",
                "Fish sauce | 2 | tbsp |",
                "Palm sugar | 1.5 | tbsp |",
                "aubergine | 150 | g | regular, cut into 2 cm cubes",
                "Bamboo shoots | 100 | g |",
                "Makrut lime leaves | 4 | leaves |",
                "Thai basil | 1 | handful |",
                "Red chilli | 1 | whole |",
                "Chicken stock | 100 | ml |",
            ],
            [
                "1. Split coconut cream; fry green curry paste.",
                "2. Coat chicken thigh; add coconut milk and chicken stock.",
                "3. Add the aubergine cubes, bamboo shoots and lime leaves.",
                "4. Simmer gently for 12 minutes. [chunk_id: R004-B03 | recipe_id: R004]",
                "5. Season with fish sauce and palm sugar; finish with Thai basil.",
            ],
        ),
    },
    {
        "qid": "S12",
        "mode": CITATION_PADDED,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "No amchur for chana masala — just use more garam masala.",
        "constraint": "replace amchur, keep the sour finish",
        "recipe_id": "R002",
        "recipe_title": "Chana Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R002",
        "retrieved_recipe_ids": ["R002", "R002", "R002"],
        "context": (
            "If you have no amchur, one tablespoon of lemon juice added off the "
            "heat gives a comparable sourness. Garam masala is already in the dish "
            "as a finishing spice, not a souring agent."
        ),
        "frozen_text": _block(
            "replace amchur, keep the sour finish",
            "Chana Masala (R002)",
            4,
            "none",
            [
                "Dried chickpeas | 200 | g | soaked 8 hours",
                "Onion | 2 | medium |",
                "Ripe tomatoes | 400 | g |",
                "Garlic cloves | 5 | cloves |",
                "Fresh ginger | 20 | g |",
                "Green chillies | 2 | whole |",
                "Cumin seeds | 1 | tsp |",
                "Coriander powder | 2 | tsp |",
                "Turmeric | 0.5 | tsp |",
                "Garam masala | 3 | tsp | extra, replacing amchur",
                "Neutral oil | 3 | tbsp |",
                "Salt | 2 | tsp |",
                "Fresh coriander | 1 | handful |",
            ],
            [
                "1. Boil the chickpeas; reserve cooking liquid.",
                "2. Fry cumin seeds, onion, garlic, ginger, green chillies.",
                "3. Cook tomatoes with turmeric, coriander powder and salt.",
                "4. Simmer chickpeas 15 minutes.",
                "5. Finish with the extra garam masala and fresh coriander. [ R002-B03 | R002 ]",
            ],
        ),
    },
    {
        "qid": "S13",
        "mode": HYBRID_SEARCH_GATE,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "I have an unfamiliar brand of green curry paste — how should I rewrite the chicken curry?",
        "constraint": "unfamiliar curry paste brand, do not over-heat",
        "recipe_id": "R004",
        "recipe_title": "Thai Green Curry with Chicken",
        "servings_expected": 4,
        "search_mode": "hybrid",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R004",
        "retrieved_recipe_ids": ["R004", "R004", "R004"],
        "context": (
            "The heat of commercial green curry pastes varies enormously between "
            "brands. Start with 30 g if you are using an unfamiliar paste and add "
            "more after tasting at step 6."
        ),
        "frozen_text": _block(
            "unfamiliar curry paste brand, do not over-heat",
            "Thai Green Curry with Chicken (R004)",
            4,
            "contains-fish",
            [
                "Chicken thigh | 500 | g |",
                "Green curry paste | 30 | g | start here; add more after tasting",
                "Coconut milk | 400 | ml |",
                "Coconut cream | 100 | ml |",
                "Fish sauce | 2 | tbsp |",
                "Palm sugar | 1.5 | tbsp |",
                "Thai aubergines | 150 | g |",
                "Bamboo shoots | 100 | g |",
                "Makrut lime leaves | 4 | leaves |",
                "Thai basil | 1 | handful |",
                "Red chilli | 1 | whole |",
                "Chicken stock | 100 | ml |",
            ],
            [
                "1. Split coconut cream; fry the 30 g green curry paste 3 minutes.",
                "2. Coat chicken thigh; add coconut milk, chicken stock, aubergines, bamboo shoots, lime leaves.",
                "3. Simmer 12 minutes.",
                "4. Season with fish sauce and palm sugar; taste and add more green curry paste only now.",
                "5. Finish with Thai basil.",
            ],
        ),
    },
    {
        "qid": "S14",
        "mode": CITATION_HEADER,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "Use tempeh instead of tofu in the vegan green curry.",
        "constraint": "tempeh instead of tofu",
        "recipe_id": "R005",
        "recipe_title": "Vegan Thai Green Curry with Tofu",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R005",
        "retrieved_recipe_ids": ["R005", "R005", "R005"],
        "context": (
            "Tempeh works in place of tofu and needs no pressing, though the "
            "flavour is nuttier. This version is free of dairy, gluten and nuts."
        ),
        "frozen_text": _block(
            "tempeh instead of tofu",
            "Vegan Thai Green Curry with Tofu (R005)",
            4,
            "none",
            [
                "tempeh | 400 | g | no pressing, cubed",
                "Green curry paste | 50 | g | check the label for shrimp",
                "Coconut milk | 400 | ml |",
                "Coconut cream | 100 | ml |",
                "Light soy sauce | 2 | tbsp |",
                "White miso paste | 1 | tsp |",
                "Palm sugar | 1.5 | tbsp |",
                "Thai aubergines | 150 | g |",
                "Bamboo shoots | 100 | g |",
                "Makrut lime leaves | 4 | leaves |",
                "Thai basil | 1 | handful |",
                "Vegetable stock | 100 | ml |",
                "Neutral oil | 2 | tbsp |",
            ],
            [
                "1. Skip pressing. Cube the tempeh.",
                "2. Sear the tempeh in the oil; lift out.",
                "3. Split coconut cream; fry green curry paste; whisk in white miso paste.",
                "4. Add coconut milk, vegetable stock, aubergines, bamboo shoots, lime leaves.",
                "5. Simmer 10 minutes, return tempeh 5 minutes. [chunk_id: R005-B03 | recipe_id: R005]",
                "6. Season with light soy sauce and palm sugar; Thai basil off the heat.",
            ],
        ),
    },
    # ── hybrid_search_gate (incl. regression T06) ───────────────────────────
    {
        "qid": "S15",
        "mode": HYBRID_SEARCH_GATE,
        "slice": RETRIEVAL_REGRESSION,
        "regression": True,
        "trace_id": "fdceede3-57db-4b22-b1f2-76b5e03d9a8f",
        "request": "I have an unfamiliar brand of curry paste, how much should I start with?",
        "constraint": "unfamiliar curry paste brand, do not over-heat",
        "recipe_id": "R004",
        "recipe_title": "Thai Green Curry with Chicken",
        "servings_expected": 4,
        "search_mode": "hybrid",
        "strategy": "basic",
        "k": 5,
        "gold_recipe": "R004",
        "retrieved_recipe_ids": ["R004", "R005", "R001"],
        "context": (
            "R004 notes chunk carrying the 30 g advice ranked first at 0.0323. "
            "Reply recorded as score_threshold with no model call."
        ),
        "frozen_text": "I cannot answer that from the provided recipe cards.",
    },
    {
        "qid": "S16",
        "mode": HYBRID_SEARCH_GATE,
        "slice": STRUCTURAL_SWAP,
        "regression": False,
        "trace_id": None,
        "request": "What can I use instead of paneer to make the butter masala vegan?",
        "constraint": "vegan",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "hybrid",
        "strategy": "structured",
        "k": 3,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": (
            "To make this dish vegan, replace the paneer with the same weight of "
            "extra-firm tofu pressed for 30 minutes, swap the butter for a neutral "
            "oil, and use thick coconut cream in place of the heavy cream."
        ),
        "frozen_text": _block(
            "vegan",
            "Paneer Butter Masala (R001)",
            4,
            "contains-nuts (cashews)",
            _R001_VEGAN,
            _R001_VEGAN_METHOD,
        ),
    },
    {
        "qid": "S17",
        "mode": HYBRID_SEARCH_GATE,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "Can I use tinned chickpeas in the chana masala, and how much?",
        "constraint": "tinned chickpeas instead of dried",
        "recipe_id": "R002",
        "recipe_title": "Chana Masala",
        "servings_expected": 4,
        "search_mode": "hybrid",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R002",
        "retrieved_recipe_ids": ["R002", "R002", "R002"],
        "context": (
            "Tinned chickpeas: two 400 g tins, drained; reduce the final simmer "
            "to 8 minutes."
        ),
        "frozen_text": _block(
            "tinned chickpeas instead of dried",
            "Chana Masala (R002)",
            4,
            "none",
            [
                "tinned chickpeas | 800 | g | two 400 g tins, drained",
                "Onion | 2 | medium |",
                "Ripe tomatoes | 400 | g |",
                "Garlic cloves | 5 | cloves |",
                "Fresh ginger | 20 | g |",
                "Green chillies | 2 | whole |",
                "Cumin seeds | 1 | tsp |",
                "Coriander powder | 2 | tsp |",
                "Amchur | 1 | tsp |",
                "Turmeric | 0.5 | tsp |",
                "Garam masala | 1 | tsp |",
                "Neutral oil | 3 | tbsp |",
                "Salt | 2 | tsp |",
                "Fresh coriander | 1 | handful |",
            ],
            [
                "1. Drain the tinned chickpeas; skip the 45 minute boil.",
                "2. Fry cumin seeds, onion, garlic, ginger, green chillies in the oil.",
                "3. Cook tomatoes with turmeric, coriander powder, salt.",
                "4. Add tinned chickpeas; simmer 8 minutes, mashing extra chickpeas.",
                "5. Finish with garam masala, amchur, fresh coriander.",
            ],
        ),
    },
    {
        "qid": "S18",
        "mode": HYBRID_SEARCH_GATE,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "If I use chicken breast instead of thigh, how long do I simmer it?",
        "constraint": "chicken breast instead of thigh",
        "recipe_id": "R004",
        "recipe_title": "Thai Green Curry with Chicken",
        "servings_expected": 4,
        "search_mode": "hybrid",
        "strategy": "structured",
        "k": 3,
        "gold_recipe": "R004",
        "retrieved_recipe_ids": ["R004", "R004", "R004"],
        "context": "Chicken breast can replace thigh but reduce the simmer to 7 minutes.",
        "frozen_text": _block(
            "chicken breast instead of thigh",
            "Thai Green Curry with Chicken (R004)",
            4,
            "contains-fish",
            [
                "Chicken breast | 500 | g |",
                "Green curry paste | 45 | g |",
                "Coconut milk | 400 | ml |",
                "Coconut cream | 100 | ml |",
                "Fish sauce | 2 | tbsp |",
                "Palm sugar | 1.5 | tbsp |",
                "Thai aubergines | 150 | g |",
                "Bamboo shoots | 100 | g |",
                "Makrut lime leaves | 4 | leaves |",
                "Thai basil | 1 | handful |",
                "Red chilli | 1 | whole |",
                "Chicken stock | 100 | ml |",
            ],
            [
                "1. Split coconut cream; fry green curry paste.",
                "2. Coat chicken breast.",
                "3. Add coconut milk, chicken stock, aubergines, bamboo shoots, lime leaves.",
                "4. Simmer gently for 7 minutes.",
                "5. Season with fish sauce and palm sugar; Thai basil off the heat.",
            ],
        ),
    },
    {
        "qid": "S19",
        "mode": HYBRID_SEARCH_GATE,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "sourdough starter schedule for this pizza — substitute the yeast",
        "constraint": "sourdough starter instead of yeast",
        "recipe_id": "R003",
        "recipe_title": "Classic Margherita Pizza",
        "servings_expected": 2,
        "search_mode": "hybrid",
        "strategy": "basic",
        "k": 3,
        "gold_recipe": "R003",
        "retrieved_recipe_ids": ["R003", "R001", "R006"],
        "context": (
            "Type 00 flour 500 g, water 325 ml, fresh yeast 3 g or 1 g instant "
            "dried yeast, refrigerate for 24 hours. No sourdough starter, no "
            "levain schedule."
        ),
        "frozen_text": _block(
            "sourdough starter instead of yeast",
            "Classic Margherita Pizza (R003)",
            2,
            "contains-gluten; contains-dairy",
            [
                "Type 00 flour | 500 | g |",
                "Water | 280 | ml | reduced to make room for starter",
                "sourdough starter | 100 | g | 100 percent hydration, 3-day build",
                "Fine sea salt | 12 | g |",
                "San Marzano tomatoes | 400 | g |",
                "Fresh mozzarella | 250 | g |",
                "Fresh basil leaves | 12 | leaves |",
                "Extra virgin olive oil | 2 | tbsp |",
                "Semolina flour | 2 | tbsp |",
            ],
            [
                "1. Feed the sourdough starter for 3 days until it doubles in 4 hours.",
                "2. Mix Type 00 flour, water and sourdough starter; rest 20 minutes; add salt.",
                "3. Bulk ferment 4 hours at room temperature, then cold-proof 48 hours.",
                "4. Preheat the oven to 250 C (480 F) for 45 minutes.",
                "5. Bake 6 to 8 minutes; finish with basil leaves and olive oil.",
            ],
            oven="250 C (480 F)",
        ),
    },
    # ── citation modes (incl. regression T08) ───────────────────────────────
    {
        "qid": "S20",
        "mode": CITATION_FULLWIDTH,
        "slice": RETRIEVAL_REGRESSION,
        "regression": True,
        "trace_id": "d04bc002-0f49-40a1-a96c-f031cab89303",
        "request": "What can I use instead of paneer to make the butter masala vegan?",
        "constraint": "vegan",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 3,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": (
            "To make this dish vegan, replace the paneer with the same weight of "
            "extra-firm tofu pressed for 30 minutes, swap the butter for a neutral "
            "oil, and use thick coconut cream in place of the heavy cream."
        ),
        # Verbatim shape recorded in notes.md T08: tofu-only, oil and coconut
        # cream omitted, full-width citation brackets.
        "frozen_text": (
            "To make the paneer butter masala vegan, replace the paneer with the "
            "same weight of extra-firm tofu pressed for 30 minutes"
            "【R001-B05 | R001】."
        ),
    },
    {
        "qid": "S21",
        "mode": CITATION_FULLWIDTH,
        "slice": STRUCTURAL_SWAP,
        "regression": False,
        "trace_id": None,
        "request": "What can I use instead of paneer to make the butter masala vegan?",
        "constraint": "vegan",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": (
            "Replace the paneer with extra-firm tofu pressed 30 minutes, butter "
            "for neutral oil, heavy cream for coconut cream."
        ),
        "frozen_text": _block(
            "vegan",
            "Paneer Butter Masala (R001)",
            4,
            "contains-nuts (cashews)",
            _R001_VEGAN,
            _R001_VEGAN_METHOD + ["Citation: 【R001-B05 | R001】"],
        ),
    },
    {
        "qid": "S22",
        "mode": CITATION_PADDED,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "vegan substitute for fish sauce in the tofu curry",
        "constraint": "vegan (no fish sauce)",
        "recipe_id": "R005",
        "recipe_title": "Vegan Thai Green Curry with Tofu",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R005",
        "retrieved_recipe_ids": ["R005", "R005", "R005"],
        "context": (
            "Light soy sauce 2 tbsp plus 1 tsp white miso replaces the savoury "
            "depth that fish sauce would normally provide."
        ),
        "frozen_text": _block(
            "vegan (no fish sauce)",
            "Vegan Thai Green Curry with Tofu (R005)",
            4,
            "none",
            [
                "Extra-firm tofu | 400 | g | pressed 30 minutes",
                "Green curry paste | 50 | g | vegan-certified",
                "Coconut milk | 400 | ml |",
                "Coconut cream | 100 | ml |",
                "Light soy sauce | 2 | tbsp | replaces fish sauce",
                "White miso paste | 1 | tsp |",
                "Palm sugar | 1.5 | tbsp |",
                "Thai aubergines | 150 | g |",
                "Bamboo shoots | 100 | g |",
                "Makrut lime leaves | 4 | leaves |",
                "Thai basil | 1 | handful |",
                "Vegetable stock | 100 | ml |",
                "Neutral oil | 2 | tbsp |",
            ],
            [
                "1. Press and sear the extra-firm tofu in the oil. [ R005-B01 | R005 ]",
                "2. Split coconut cream; fry green curry paste; whisk in white miso paste.",
                "3. Add coconut milk, vegetable stock, aubergines, bamboo shoots, lime leaves.",
                "4. Simmer, return extra-firm tofu.",
                "5. Season with light soy sauce and palm sugar; Thai basil off the heat.",
            ],
        ),
    },
    {
        "qid": "S23",
        "mode": CITATION_HEADER,
        "slice": STRUCTURAL_SWAP,
        "regression": False,
        "trace_id": None,
        "request": "How do I make the shakshuka vegan?",
        "constraint": "vegan (no eggs, no feta)",
        "recipe_id": "R006",
        "recipe_title": "Shakshuka",
        "servings_expected": 4,
        "search_mode": "bm25",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R006",
        "retrieved_recipe_ids": ["R006", "R006", "R006"],
        "context": (
            "For a vegan version, omit the eggs and feta and add two 400 g tins "
            "of drained chickpeas at step 3, simmering for 10 minutes."
        ),
        "frozen_text": _block(
            "vegan (no eggs, no feta)",
            "Shakshuka (R006)",
            4,
            "none",
            [
                "chickpeas | 800 | g | two 400 g tins, drained",
                "Red bell peppers | 2 | whole |",
                "Ripe tomatoes | 600 | g |",
                "Onion | 1 | large |",
                "Garlic cloves | 4 | cloves |",
                "Sweet paprika | 2 | tsp |",
                "Ground cumin | 1 | tsp |",
                "Caraway seeds | 0.5 | tsp |",
                "Cayenne pepper | 0.25 | tsp |",
                "Olive oil | 3 | tbsp |",
                "Fresh parsley | 1 | handful |",
                "Salt | 1 | tsp |",
            ],
            [
                "1. Cook onion and peppers in olive oil 12 minutes.",
                "2. Add garlic, paprika, cumin, caraway, cayenne.",
                "3. Add tomatoes, salt and chickpeas; simmer 10 minutes. "
                "[chunk_id: R006-B04 | recipe_id: R006]",
                "4. Finish with parsley.",
            ],
        ),
    },
    # ── ingredient_table_miss ───────────────────────────────────────────────
    {
        "qid": "S24",
        "mode": INGREDIENT_TABLE_MISS,
        "slice": ALLERGEN_SAFETY,
        "regression": False,
        "trace_id": None,
        "request": "Make paneer butter masala vegan — I did not retrieve the ingredients table.",
        "constraint": "vegan",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 3,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": (
            "Method, nutrition and notes only. Notes mention extra-firm tofu, oil "
            "and coconut cream. Ingredient quantities are not in the top 3."
        ),
        "frozen_text": _block(
            "vegan",
            "Paneer Butter Masala (R001)",
            4,
            "contains-nuts (cashews)",
            [
                "extra-firm tofu | 500 | g | guessed weight",
                "Ripe tomatoes | 600 | g |",
                "Raw cashews | 20 | g |",
                "Neutral oil | 50 | g |",
                "Onion | 1 | medium |",
                "Garlic cloves | 4 | cloves |",
                "Fresh ginger | 15 | g |",
                "Garam masala | 1 | tsp |",
                "Salt | 1.5 | tsp |",
                "Water | 150 | ml |",
            ],
            [
                "1. Soak the cashews; sear the extra-firm tofu in the oil.",
                "2. Cook onion, garlic, ginger, tomatoes.",
                "3. Blend with cashews; add water; simmer.",
                "4. Finish with garam masala, extra-firm tofu and heavy cream off the heat.",
            ],
        ),
    },
    {
        "qid": "S25",
        "mode": INGREDIENT_TABLE_MISS,
        "slice": STRUCTURAL_SWAP,
        "regression": False,
        "trace_id": None,
        "request": "how many grams of paneer do I need if I swap it for tofu in butter masala",
        "constraint": "same-weight tofu for paneer",
        "recipe_id": "R001",
        "recipe_title": "Paneer Butter Masala",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 5,
        "gold_recipe": "R001",
        "retrieved_recipe_ids": ["R001", "R001", "R001"],
        "context": "Paneer | 400 | g | cut into 2 cm cubes. Same weight of extra-firm tofu.",
        "frozen_text": _block(
            "same-weight tofu for paneer",
            "Paneer Butter Masala (R001)",
            4,
            "contains-nuts (cashews); contains-dairy",
            [
                "extra-firm tofu | 400 | g | same weight as the paneer row",
                "Ripe tomatoes | 600 | g |",
                "Raw cashews | 20 | g |",
                "Unsalted butter | 50 | g |",
                "Heavy cream | 60 | ml |",
                "Onion | 1 | medium |",
                "Garlic cloves | 4 | cloves |",
                "Fresh ginger | 15 | g |",
                "Kashmiri chilli powder | 1.5 | tsp |",
                "Garam masala | 1 | tsp |",
                "Dried fenugreek leaves | 1 | tsp |",
                "Granulated sugar | 1 | tsp |",
                "Salt | 1.5 | tsp |",
                "Water | 150 | ml |",
            ],
            [
                "1. Soak cashews. Sear extra-firm tofu in butter; lift out.",
                "2. Cook onion, garlic, ginger, tomatoes with chilli powder, sugar, salt.",
                "3. Blend with cashews; add water; simmer 20 minutes.",
                "4. Finish with butter, garam masala, fenugreek leaves, extra-firm tofu, heavy cream.",
            ],
        ),
    },
    {
        "qid": "S26",
        "mode": INGREDIENT_TABLE_MISS,
        "slice": FLAVOUR_PLAUSIBILITY,
        "regression": False,
        "trace_id": None,
        "request": "How many grams of green curry paste should I use in the vegan green curry if I substitute a milder paste?",
        "constraint": "milder vegan curry paste, vegan curry quantities",
        "recipe_id": "R005",
        "recipe_title": "Vegan Thai Green Curry with Tofu",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "basic",
        "k": 3,
        "gold_recipe": "R005",
        "retrieved_recipe_ids": ["R004", "R003", "R001"],
        "context": (
            "Chicken curry ingredients (R004): Green curry paste | 45 | g. "
            "Vegan ingredients table not in top 3. R005 uses 50 g."
        ),
        "frozen_text": _block(
            "milder vegan curry paste, vegan curry quantities",
            "Vegan Thai Green Curry with Tofu (R005)",
            4,
            "none",
            [
                "Extra-firm tofu | 400 | g |",
                "Green curry paste | 45 | g | copied from the chicken card",
                "Coconut milk | 400 | ml |",
                "Coconut cream | 100 | ml |",
                "Light soy sauce | 2 | tbsp |",
                "White miso paste | 1 | tsp |",
                "Palm sugar | 1.5 | tbsp |",
                "Thai aubergines | 150 | g |",
                "Bamboo shoots | 100 | g |",
                "Makrut lime leaves | 4 | leaves |",
                "Thai basil | 1 | handful |",
                "Vegetable stock | 100 | ml |",
                "Neutral oil | 2 | tbsp |",
            ],
            [
                "1. Press and sear extra-firm tofu in the oil.",
                "2. Split coconut cream; fry green curry paste; add white miso paste.",
                "3. Add coconut milk, vegetable stock, aubergines, bamboo shoots, lime leaves.",
                "4. Simmer; return extra-firm tofu.",
                "5. Season with light soy sauce and palm sugar; Thai basil off the heat.",
            ],
        ),
    },
    {
        "qid": "S27",
        "mode": CITATION_FULLWIDTH,
        "slice": STRUCTURAL_SWAP,
        "regression": False,
        "trace_id": None,
        "request": "How do I make the shakshuka vegan?",
        "constraint": "vegan (no eggs, no feta)",
        "recipe_id": "R006",
        "recipe_title": "Shakshuka",
        "servings_expected": 4,
        "search_mode": "semantic",
        "strategy": "structured",
        "k": 3,
        "gold_recipe": "R006",
        "retrieved_recipe_ids": ["R006", "R006", "R002"],
        "context": (
            "For a vegan version, omit the eggs and feta and add two 400 g tins "
            "of drained chickpeas at step 3, simmering for 10 minutes."
        ),
        "frozen_text": _block(
            "vegan (no eggs, no feta)",
            "Shakshuka (R006)",
            4,
            "none",
            [
                "chickpeas | 800 | g | two 400 g tins, drained",
                "Red bell peppers | 2 | whole |",
                "Ripe tomatoes | 600 | g |",
                "Onion | 1 | large |",
                "Garlic cloves | 4 | cloves |",
                "Sweet paprika | 2 | tsp |",
                "Ground cumin | 1 | tsp |",
                "Caraway seeds | 0.5 | tsp |",
                "Cayenne pepper | 0.25 | tsp |",
                "Olive oil | 3 | tbsp |",
                "Fresh parsley | 1 | handful |",
                "Salt | 1 | tsp |",
            ],
            [
                "1. Cook onion and peppers in olive oil.",
                "2. Add garlic, paprika, cumin, caraway, cayenne.",
                "3. Add tomatoes, salt and chickpeas; simmer 10 minutes. 【R006-B04 | R006】",
                "4. Finish with parsley.",
            ],
        ),
    },
]


assert len(CASES) == 27, len(CASES)
assert all(c["mode"] in MODES for c in CASES)
assert sum(1 for c in CASES if c["regression"]) >= 2
assert len({c["qid"] for c in CASES}) == len(CASES)


def frozen_payload():
    """JSON-serialisable snapshot of the 27 frozen substitutions."""
    return {
        "n": len(CASES),
        "items": [
            {
                "qid": c["qid"],
                "mode": c["mode"],
                "slice": c["slice"],
                "regression": c["regression"],
                "trace_id": c["trace_id"],
                "request": c["request"],
                "constraint": c["constraint"],
                "recipe_id": c["recipe_id"],
                "recipe_title": c["recipe_title"],
                "servings_expected": c["servings_expected"],
                "search_mode": c["search_mode"],
                "strategy": c["strategy"],
                "k": c["k"],
                "gold_recipe": c["gold_recipe"],
                "retrieved_recipe_ids": c["retrieved_recipe_ids"],
                "context": c["context"],
                "substitution": c["frozen_text"],
            }
            for c in CASES
        ],
    }
