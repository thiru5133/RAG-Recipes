"""Cases for the rule-based assertion checks on generated answers.

`must_contain` is any-of: the generated answer has to state at least one of the
tokens. `refuse` cases are the unanswerable and off-topic questions; the correct
behaviour is the fixed refusal sentence, from either gate.
"""

ANSWER_CASES = [
    {"qid": "Q1", "question": "How much heavy cream does the paneer butter masala need?",
     "gold_recipes": ["R001"], "must_contain": ["60"]},
    {"qid": "Q2", "question": "How many grams of green curry paste are in the vegan green curry?",
     "gold_recipes": ["R005"], "must_contain": ["50"]},
    {"qid": "Q3", "question": "How many grams of dried chickpeas does chana masala use?",
     "gold_recipes": ["R002"], "must_contain": ["200"]},
    {"qid": "Q4", "question": "How many calories per serving does the margherita pizza have?",
     "gold_recipes": ["R003"], "must_contain": ["892"]},
    {"qid": "Q5", "question": "What temperature should the oven and stone be preheated to for the pizza?",
     "gold_recipes": ["R003"], "must_contain": ["250"]},
    {"qid": "Q7", "question": "How long does the shakshuka sauce simmer before the eggs go in?",
     "gold_recipes": ["R006"], "must_contain": ["15 minutes", "15 min"]},
]

REFUSE_CASES = [
    {"qid": "U1", "question": "How long should I cook the beef wellington for, and at what temperature?"},
    {"qid": "U2", "question": "Which wine pairs best with the paneer butter masala?"},
    {"qid": "U3", "question": "How many days does the sourdough starter need before the pizza dough is ready?"},
    {"qid": "OT1", "question": "What kitchen scale should I buy?"},
]
