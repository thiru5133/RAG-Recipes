"""The question bank the trace log is generated from.

Three classes of question, all phrased the way a cook types rather than the way
an eval is written:

- `answerable`  the card contains the answer; `gold_answer` is copied from it
- `unanswerable` the dish is in the corpus but the fact is not on the card
- `off_topic`   nothing in the corpus could answer it

`gold_answer` is only ever used when reading traces afterwards, never at
generation time — the pipeline is not told what the right answer is.
"""

QUESTION_BANK = [
    # ── R001 Paneer Butter Masala ────────────────────────────────────────────
    {
        "qid": "R001-cream",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Ingredients",
        "gold_answer": "60 ml heavy cream, stirred in off the heat",
        "phrasings": [
            "How much heavy cream does the paneer butter masala need?",
            "how much cream goes in paneer butter masala",
        ],
    },
    {
        "qid": "R001-paneer",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Ingredients",
        "gold_answer": "400 g paneer, cut into 2 cm cubes",
        "phrasings": [
            "How much paneer is in the butter masala?",
            "how many grams of paneer do I need for butter masala",
        ],
    },
    {
        "qid": "R001-cashew-soak",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Method",
        "gold_answer": "15 minutes in hot water",
        "phrasings": [
            "How long do the cashews soak for the paneer butter masala?",
            "cashew soaking time butter masala",
        ],
    },
    {
        "qid": "R001-sear",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Method",
        "gold_answer": "2 minutes per side",
        "phrasings": [
            "How long do I sear the paneer cubes on each side?",
            "paneer searing time per side",
        ],
    },
    {
        "qid": "R001-vegan-sub",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Notes",
        "gold_answer": "extra-firm tofu pressed 30 minutes, oil for butter, coconut cream for cream",
        "phrasings": [
            "What can I use instead of paneer to make the butter masala vegan?",
            "how do I make paneer butter masala vegan",
        ],
    },
    {
        "qid": "R001-simmer",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Method",
        "gold_answer": "20 minutes uncovered",
        "phrasings": [
            "How long does the butter masala gravy simmer uncovered?",
            "butter masala simmering time after adding water",
        ],
    },
    {
        "qid": "R001-kcal",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Nutrition",
        "gold_answer": "512 kcal per serving",
        "phrasings": [
            "How many calories per serving does the paneer butter masala have?",
            "calories in paneer butter masala per serving",
        ],
    },
    {
        "qid": "R001-leftovers",
        "class": "answerable",
        "gold_recipes": ["R001"],
        "gold_section": "Notes",
        "gold_answer": "3 days refrigerated, cream may separate on reheating",
        "phrasings": [
            "How long do paneer butter masala leftovers keep?",
            "how many days can I keep the butter masala in the fridge",
        ],
    },
    # ── R002 Chana Masala ────────────────────────────────────────────────────
    {
        "qid": "R002-chickpeas",
        "class": "answerable",
        "gold_recipes": ["R002"],
        "gold_section": "Ingredients",
        "gold_answer": "200 g dried chickpeas, soaked 8 hours or overnight",
        "phrasings": [
            "How many grams of dried chickpeas does the chana masala use?",
            "how much dried chana for chana masala",
        ],
    },
    {
        "qid": "R002-boil",
        "class": "answerable",
        "gold_recipes": ["R002"],
        "gold_section": "Method",
        "gold_answer": "45 to 55 minutes",
        "phrasings": [
            "How long do the dried chickpeas boil for the chana masala?",
            "chickpea boiling time chana masala",
        ],
    },
    {
        "qid": "R002-tinned",
        "class": "answerable",
        "gold_recipes": ["R002"],
        "gold_section": "Notes",
        "gold_answer": "two 400 g tins drained, final simmer reduced to 8 minutes",
        "phrasings": [
            "Can I use tinned chickpeas in the chana masala, and how much?",
            "tinned chickpea substitute for chana masala",
        ],
    },
    {
        "qid": "R002-liquid",
        "class": "answerable",
        "gold_recipes": ["R002"],
        "gold_section": "Method",
        "gold_answer": "250 ml of the cooking liquid",
        "phrasings": [
            "How much chickpea cooking liquid should I reserve?",
            "how much cooking water do I keep for the chana masala",
        ],
    },
    {
        "qid": "R002-amchur",
        "class": "answerable",
        "gold_recipes": ["R002"],
        "gold_section": "Notes",
        "gold_answer": "one tablespoon of lemon juice off the heat",
        "phrasings": [
            "What can I use instead of amchur in the chana masala?",
            "no amchur what do I substitute chana masala",
        ],
    },
    {
        "qid": "R002-kcal",
        "class": "answerable",
        "gold_recipes": ["R002"],
        "gold_section": "Nutrition",
        "gold_answer": "341 kcal per serving",
        "phrasings": [
            "How many calories per serving is the chana masala?",
            "chana masala calories per serving",
        ],
    },
    # ── R003 Margherita Pizza ────────────────────────────────────────────────
    {
        "qid": "R003-mozzarella",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Ingredients",
        "gold_answer": "250 g fresh mozzarella, torn and drained 30 minutes",
        "phrasings": [
            "How much fresh mozzarella is needed for the margherita pizza?",
            "mozzarella quantity for the margherita",
        ],
    },
    {
        "qid": "R003-preheat",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Method",
        "gold_answer": "250 C (480 F), stone held 45 minutes after the oven reaches temperature",
        "phrasings": [
            "What temperature should the oven and stone be preheated to for the pizza?",
            "how hot do I get the pizza stone and for how long",
        ],
    },
    {
        "qid": "R003-fridge",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Method",
        "gold_answer": "24 hours",
        "phrasings": [
            "How long is the pizza dough refrigerated for?",
            "pizza dough cold ferment how long",
        ],
    },
    {
        "qid": "R003-bake",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Method",
        "gold_answer": "6 to 8 minutes",
        "phrasings": [
            "How long does the margherita pizza bake?",
            "pizza baking time margherita",
        ],
    },
    {
        "qid": "R003-basil",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Method",
        "gold_answer": "after baking, once the pizza leaves the oven",
        "phrasings": [
            "When are the basil leaves added to the margherita pizza?",
            "do I put basil on before or after baking",
        ],
    },
    {
        "qid": "R003-kcal",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Nutrition",
        "gold_answer": "892 kcal per serving",
        "phrasings": [
            "How many calories per serving does the margherita pizza have?",
            "margherita pizza calories per serving",
        ],
    },
    {
        "qid": "R003-water",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Ingredients",
        "gold_answer": "325 ml water at 20 C for a 65 percent hydration dough",
        "phrasings": [
            "How much water goes in the pizza dough?",
            "pizza dough hydration how much water",
        ],
    },
    {
        "qid": "R003-cool-oven",
        "class": "answerable",
        "gold_recipes": ["R003"],
        "gold_section": "Notes",
        "gold_answer": "10 to 12 minutes in an oven that only reaches 220 C",
        "phrasings": [
            "My oven only reaches 220 C, how long do I bake the pizza?",
            "pizza bake time in a domestic oven that will not hit 250",
        ],
    },
    # ── R004 Thai Green Curry with Chicken ───────────────────────────────────
    {
        "qid": "R004-paste",
        "class": "answerable",
        "gold_recipes": ["R004"],
        "gold_section": "Ingredients",
        "gold_answer": "45 g green curry paste, about 3 tablespoons",
        "phrasings": [
            "How much green curry paste is in the chicken green curry?",
            "grams of curry paste for the thai green curry with chicken",
        ],
    },
    {
        "qid": "R004-simmer",
        "class": "answerable",
        "gold_recipes": ["R004"],
        "gold_section": "Method",
        "gold_answer": "12 minutes at a bare simmer",
        "phrasings": [
            "How long does the chicken curry simmer after the vegetables go in?",
            "simmer time chicken green curry",
        ],
    },
    {
        "qid": "R004-breast",
        "class": "answerable",
        "gold_recipes": ["R004"],
        "gold_section": "Notes",
        "gold_answer": "reduce the simmer to 7 minutes",
        "phrasings": [
            "If I use chicken breast instead of thigh, how long do I simmer it?",
            "chicken breast substitute simmer time green curry",
        ],
    },
    {
        "qid": "R004-fish-sauce",
        "class": "answerable",
        "gold_recipes": ["R004"],
        "gold_section": "Ingredients",
        "gold_answer": "2 tbsp fish sauce",
        "phrasings": [
            "How much fish sauce does the chicken green curry use?",
            "fish sauce quantity thai green curry chicken",
        ],
    },
    {
        "qid": "R004-unfamiliar-paste",
        "class": "answerable",
        "gold_recipes": ["R004"],
        "gold_section": "Notes",
        "gold_answer": "start with 30 g and add more after tasting at step 6",
        "phrasings": [
            "I have an unfamiliar brand of curry paste, how much should I start with?",
            "new curry paste brand how much to use green curry",
        ],
    },
    {
        "qid": "R004-kcal",
        "class": "answerable",
        "gold_recipes": ["R004"],
        "gold_section": "Nutrition",
        "gold_answer": "486 kcal per serving",
        "phrasings": [
            "How many calories per serving is the chicken green curry?",
            "calories thai green curry with chicken",
        ],
    },
    # ── R005 Vegan Thai Green Curry with Tofu ────────────────────────────────
    {
        "qid": "R005-paste",
        "class": "answerable",
        "gold_recipes": ["R005"],
        "gold_section": "Ingredients",
        "gold_answer": "50 g green curry paste",
        "phrasings": [
            "How many grams of green curry paste are in the vegan green curry?",
            "curry paste amount for the tofu green curry",
        ],
    },
    {
        "qid": "R005-press",
        "class": "answerable",
        "gold_recipes": ["R005"],
        "gold_section": "Ingredients",
        "gold_answer": "pressed 30 minutes",
        "phrasings": [
            "How long is the tofu pressed for the vegan green curry?",
            "tofu pressing time vegan thai curry",
        ],
    },
    {
        "qid": "R005-fish-sauce-sub",
        "class": "answerable",
        "gold_recipes": ["R005"],
        "gold_section": "Ingredients",
        "gold_answer": "2 tbsp light soy sauce, plus 1 tsp white miso for depth",
        "phrasings": [
            "What replaces the fish sauce in the vegan green curry?",
            "vegan substitute for fish sauce in the tofu curry",
        ],
    },
    {
        "qid": "R005-simmer",
        "class": "answerable",
        "gold_recipes": ["R005"],
        "gold_section": "Method",
        "gold_answer": "10 minutes, then 5 minutes more after the tofu returns",
        "phrasings": [
            "How long does the vegan green curry simmer before and after the tofu goes back in?",
            "simmer time vegan green curry tofu",
        ],
    },
    {
        "qid": "R005-kcal",
        "class": "answerable",
        "gold_recipes": ["R005"],
        "gold_section": "Nutrition",
        "gold_answer": "412 kcal per serving",
        "phrasings": [
            "How many calories per serving is the vegan green curry?",
            "calories vegan thai green curry with tofu",
        ],
    },
    # ── R006 Shakshuka ───────────────────────────────────────────────────────
    {
        "qid": "R006-eggs",
        "class": "answerable",
        "gold_recipes": ["R006"],
        "gold_section": "Ingredients",
        "gold_answer": "6 large eggs at room temperature",
        "phrasings": [
            "How many eggs does the shakshuka use?",
            "number of eggs in shakshuka",
        ],
    },
    {
        "qid": "R006-sauce-simmer",
        "class": "answerable",
        "gold_recipes": ["R006"],
        "gold_section": "Method",
        "gold_answer": "15 minutes uncovered, until it holds a channel",
        "phrasings": [
            "How long does the shakshuka sauce simmer before the eggs go in?",
            "how long do I reduce the shakshuka sauce",
        ],
    },
    {
        "qid": "R006-eggs-covered",
        "class": "answerable",
        "gold_recipes": ["R006"],
        "gold_section": "Method",
        "gold_answer": "6 to 8 minutes covered",
        "phrasings": [
            "How long are the shakshuka eggs cooked after covering the pan?",
            "shakshuka egg cooking time with the lid on",
        ],
    },
    {
        "qid": "R006-feta",
        "class": "answerable",
        "gold_recipes": ["R006"],
        "gold_section": "Ingredients",
        "gold_answer": "100 g feta, crumbled over at the end",
        "phrasings": [
            "How much feta goes on the shakshuka?",
            "feta quantity shakshuka",
        ],
    },
    {
        "qid": "R006-vegan",
        "class": "answerable",
        "gold_recipes": ["R006"],
        "gold_section": "Notes",
        "gold_answer": "omit eggs and feta, add two 400 g tins of chickpeas at step 3, simmer 10 minutes",
        "phrasings": [
            "How do I make the shakshuka vegan?",
            "vegan version of shakshuka",
        ],
    },
    {
        "qid": "R006-kcal",
        "class": "answerable",
        "gold_recipes": ["R006"],
        "gold_section": "Nutrition",
        "gold_answer": "298 kcal per serving",
        "phrasings": [
            "How many calories per serving does the shakshuka have?",
            "shakshuka calories per serving",
        ],
    },
    # ── under-specified questions: two cards answer them differently ─────────
    {
        "qid": "AMB-paste",
        "class": "answerable",
        "gold_recipes": ["R004", "R005"],
        "gold_section": "Ingredients",
        "gold_answer": "ambiguous: 45 g in the chicken curry (R004), 50 g in the vegan curry (R005)",
        "phrasings": [
            "How much curry paste do I need?",
            "how many grams of green curry paste",
        ],
    },
    {
        "qid": "AMB-kcal",
        "class": "answerable",
        "gold_recipes": ["R001", "R002", "R003", "R004", "R005", "R006"],
        "gold_section": "Nutrition",
        "gold_answer": "ambiguous: six cards, 298 to 892 kcal per serving",
        "phrasings": [
            "How many calories per serving?",
            "what is the calorie count per serving",
        ],
    },
    {
        "qid": "AMB-simmer",
        "class": "answerable",
        "gold_recipes": ["R004", "R005"],
        "gold_section": "Method",
        "gold_answer": "ambiguous: 12 minutes for the chicken curry, 10 plus 5 for the vegan one",
        "phrasings": [
            "How long do I simmer the green curry?",
            "green curry simmering time",
        ],
    },
    # ── unanswerable: the dish is in the corpus, the fact is not ─────────────
    {
        "qid": "UNANS-wine",
        "class": "unanswerable",
        "why_unanswerable": "no card carries drink pairings",
        "phrasings": [
            "What wine should I serve with the shakshuka?",
            "which wine goes with shakshuka",
        ],
    },
    {
        "qid": "UNANS-freeze",
        "class": "unanswerable",
        "why_unanswerable": "R001 gives 3 days refrigerated and says nothing about freezing",
        "phrasings": [
            "Can I freeze the paneer butter masala?",
            "is the butter masala freezer friendly",
        ],
    },
    {
        "qid": "UNANS-no-yeast",
        "class": "unanswerable",
        "why_unanswerable": "R003 is a commercial-yeast dough; no yeast-free method exists on the card",
        "phrasings": [
            "How do I make the pizza dough without yeast?",
            "yeast free pizza dough version of this recipe",
        ],
    },
    {
        "qid": "UNANS-sourdough",
        "class": "unanswerable",
        "why_unanswerable": "R003 uses fresh yeast and a 24 hour cold ferment; no starter is mentioned",
        "phrasings": [
            "How many days does the sourdough starter need before the pizza dough is ready?",
            "sourdough starter schedule for this pizza",
        ],
    },
    {
        "qid": "UNANS-beef",
        "class": "unanswerable",
        "why_unanswerable": "there is no beef recipe in the corpus at all",
        "phrasings": [
            "How long should I cook the beef wellington and at what temperature?",
            "beef wellington cooking time and temperature",
        ],
    },
    {
        "qid": "UNANS-keto",
        "class": "unanswerable",
        "why_unanswerable": "cards carry dietary tags but say nothing about keto suitability",
        "phrasings": [
            "Is the chana masala keto friendly?",
            "can I eat the chana masala on keto",
        ],
    },
    {
        "qid": "UNANS-paste-shelf",
        "class": "unanswerable",
        "why_unanswerable": "R004 and R005 discuss paste brands and heat, never shelf life",
        "phrasings": [
            "How long does an opened tub of green curry paste keep?",
            "shelf life of green curry paste once opened",
        ],
    },
    # ── off topic: nothing in the corpus could answer it ─────────────────────
    {
        "qid": "OT-cast-iron",
        "class": "off_topic",
        "why_unanswerable": "pan care is not in the corpus",
        "phrasings": [
            "How do I season a cast iron pan?",
            "seasoning a cast iron skillet properly",
        ],
    },
    {
        "qid": "OT-knife",
        "class": "off_topic",
        "why_unanswerable": "equipment brands are not in the corpus",
        "phrasings": [
            "What is the best chef's knife brand?",
            "which chef knife should I buy",
        ],
    },
    {
        "qid": "OT-italian-history",
        "class": "off_topic",
        "why_unanswerable": "the corpus is six recipe cards, not culinary history",
        "phrasings": [
            "Tell me about the history of Italian cuisine.",
            "history of italian food",
        ],
    },
    {
        "qid": "OT-scale",
        "class": "off_topic",
        "why_unanswerable": "equipment purchasing is not in the corpus",
        "phrasings": [
            "What kitchen scale should I buy?",
            "recommend a digital kitchen scale",
        ],
    },
]


def phrasing_count() -> int:
    return sum(len(e["phrasings"]) for e in QUESTION_BANK)
