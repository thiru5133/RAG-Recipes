"""The 10 race requests. Mix: scale-only, single allergen, allergen-cascade, cannot.

Cascade = step 3 depends on what get_allergen_profile returned (the substitute
itself carries another allergen, or the swap leaves a second class). The
workflow makes one profile call and misses those. The agent can call again.
"""

REQUESTS = [
    {
        "id": "W01",
        "class": "scale_only",
        "text": "Scale the paneer butter masala to 8 servings. No swaps.",
        "gold_recipe": "R001",
        "servings": 8,
        "primary_allergen": None,
        "forbidden": [],
        "required": ["paneer"],
        "must_warn": False,
    },
    {
        "id": "W02",
        "class": "scale_only",
        "text": "Chana masala for 2 people, as written.",
        "gold_recipe": "R002",
        "servings": 2,
        "primary_allergen": None,
        "forbidden": [],
        "required": ["chickpea"],
        "must_warn": False,
    },
    {
        "id": "W03",
        "class": "scale_only",
        "text": "I need the margherita pizza for 4 (the card is written for 2).",
        "gold_recipe": "R003",
        "servings": 4,
        "primary_allergen": None,
        "forbidden": [],
        "required": ["flour"],
        "must_warn": False,
    },
    {
        "id": "W04",
        "class": "scale_only",
        "text": "Shakshuka for 8, no dietary changes.",
        "gold_recipe": "R006",
        "servings": 8,
        "primary_allergen": None,
        "forbidden": [],
        "required": ["egg"],
        "must_warn": False,
    },
    {
        "id": "W05",
        "class": "single_allergen",
        "text": "Make the paneer butter masala dairy-free for 4.",
        "gold_recipe": "R001",
        "servings": 4,
        "primary_allergen": "dairy",
        "forbidden": ["paneer", "butter", "heavy cream"],
        "required": ["tofu"],
        "must_warn": False,
    },
    {
        "id": "W06",
        "class": "single_allergen",
        "text": "Nut-free paneer butter masala for 4. I can eat dairy.",
        "gold_recipe": "R001",
        "servings": 4,
        "primary_allergen": "nuts",
        "forbidden": ["cashew"],
        "required": ["melon"],
        "must_warn": False,
    },
    {
        "id": "W07",
        "class": "allergen_cascade",
        "text": (
            "Make paneer butter masala vegan AND nut-free for 8. "
            "The dairy swap is not enough if cashews remain."
        ),
        "gold_recipe": "R001",
        "servings": 8,
        "primary_allergen": "dairy",
        "forbidden": ["paneer", "butter", "heavy cream", "cashew"],
        "required": ["tofu", "melon"],
        "must_warn": False,
    },
    {
        "id": "W08",
        "class": "allergen_cascade",
        "text": (
            "Vegan and gluten-free Thai green curry with chicken, 4 servings. "
            "Replacing fish sauce with soy is not enough if soy carries wheat."
        ),
        "gold_recipe": "R004",
        "servings": 4,
        "primary_allergen": "fish",
        "forbidden": ["fish sauce", "chicken thigh"],
        "required": ["tamari"],
        "must_warn": False,
    },
    {
        "id": "W09",
        "class": "allergen_cascade",
        "text": (
            "Make the shakshuka vegan for 4. Dropping feta still leaves the eggs; "
            "both have to go, chickpeas in as the card says."
        ),
        "gold_recipe": "R006",
        "servings": 4,
        "primary_allergen": "dairy",
        "forbidden": ["feta", "egg"],
        "required": ["chickpea"],
        "must_warn": False,
    },
    {
        "id": "W10",
        "class": "cannot_adapt",
        "text": "Gluten-free margherita pizza for 2. I cannot eat wheat.",
        "gold_recipe": "R003",
        "servings": 2,
        "primary_allergen": "gluten",
        "forbidden": [],
        "required": [],
        "must_warn": True,
    },
]
