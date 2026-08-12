"""Three questions the corpus cannot answer.

All three are recipe-shaped on purpose, so the retriever still returns plausible
neighbours. A refusal is only meaningful when there was something to hallucinate
from.
"""

UNANSWERABLE = [
    {
        "qid": "U1",
        "question": "How long should I cook the beef wellington for, and at what temperature?",
        "why": "No beef wellington card exists; the corpus has no beef recipe at all.",
    },
    {
        "qid": "U2",
        "question": "Which wine pairs best with the paneer butter masala?",
        "why": "R001 exists but contains no wine-pairing information in any section.",
    },
    {
        "qid": "U3",
        "question": "How many days does the sourdough starter need before the pizza dough is ready?",
        "why": "R003 uses a commercial-yeast dough with a 24 hour cold ferment; no starter is mentioned.",
    },
]
