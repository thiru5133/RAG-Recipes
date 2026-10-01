# Requirement 5 — same failing call, old vs new docstring/error

Request: `Scale the shakshuka to 6 servings.`  
Injected failing call (identical in every trial): `scale_recipe({"recipe_id": "shakshuka", "servings": 6})` — a guessed dish name instead of an id.

| | tool description the model saw | error text the model saw |
|---|---|---|
| **before** (`week9-server-one`) | `Scale a recipe to a number of servings.` | `Error 3` |
| **after** (working tree) | docstring rewritten as a prompt (see `recipe_server.py`) | `No recipe has id 'shakshuka'. Valid ids are R001, R002, R003, R004, R005, R006; a dish name is not an id. Call search_recipes with the dish name (e.g. query='shakshuka') to get its id, then call scale_recipe again with that id.` |

## Recovery rate over 5 trials (recovered = a later `scale_recipe` succeeded on R006)

| condition | before | after |
|---|---:|---:|
| no allergen matrix attached (isolates the error text) | 5/5 | 5/5 |
| allergen matrix attached as a resource | 5/5 | 5/5 |

## Transcript — before, matrix not attached (trial 1)

1. user: Scale the shakshuka to 6 servings.
2. model -> `scale_recipe({"recipe_id": "shakshuka", "servings": 6})`
3. tool: `ERROR: Error 3`
4. model -> `search_recipes({"query": "shakshuka"})` -> ok
5. model -> `scale_recipe({"recipe_id": "R006", "servings": 6})` -> ok
6. model answer: Shakshuka scaled to 6 servings: 9 eggs, 3 bell peppers, 900 g tomatoes, 1.5 onions, 6 garlic cloves, 3 tsp paprika, 1.5 tsp cumin, 0.75 tsp caraway, 0.38 tsp cayenne, 4.5 tbsp olive oil, 150 g feta, 1.5 handful parsley, 1.5 tsp salt. Follow the method steps as listed.  
   _stopped_by=completed, tokens=2072_

## Transcript — after, matrix not attached (trial 1)

1. user: Scale the shakshuka to 6 servings.
2. model -> `scale_recipe({"recipe_id": "shakshuka", "servings": 6})`
3. tool: `ERROR: No recipe has id 'shakshuka'. Valid ids are R001, R002, R003, R004, R005, R006; a dish name is not an id. Call search_recipes with the dish name (e.g. query='shakshuka') to get its id, then call scale_recipe again with that id.`
4. model -> `search_recipes({"query": "shakshuka"})` -> ok
5. model -> `scale_recipe({"recipe_id": "R006", "servings": 6})` -> ok
6. model answer: **Shakshuka – 6 servings**

**Ingredients**

- 9 large eggs (room temperature)  
- 3 whole red bell peppers, sliced into strips  
- 900 g ripe tomatoes (chopped, or one 400 g tin + 200 g fresh)  
- 1.5 large onions, sliced  
- 6 garlic cloves, sliced  
- 3 tsp sweet paprika  
- 1.5 tsp ground cumin  
- 0.75 tsp caraway seeds, lightly crushed  
- 0.38 tsp cayenne pepper (optional)  
- 4.5 tbsp olive oil  
- 150 g feta cheese, crumbled (for topping)  
- 1.5 handfuls fresh parsley, chopped (for garnish)  
- 1.5 tsp salt, to taste  

**Method**

1. Heat olive oil in a wide, shallow pan. Cook onion and peppers over medium heat for 12 min until soft and beginning to colour.  
2. Add garlic, paprika, cumin, caraway, and cayenne; fry 1 min until fragrant.  
3. Stir in tomatoes and salt; simmer 15 min, uncovered, until sauce thickens enough to hold a channel when you drag a spoon through it.  
4. Make six wells in the sauce and crack one egg into each.  
5. Cover and cook 6–8 min, until whites are set but yolks still runny.  
6. Sprinkle with feta and parsley, then serve straight from the pan with flatbread.  
   _stopped_by=completed, tokens=2780_

## Transcript — before, matrix attached (trial 1)

1. user: Scale the shakshuka to 6 servings.
2. model -> `scale_recipe({"recipe_id": "shakshuka", "servings": 6})`
3. tool: `ERROR: Error 3`
4. model -> `scale_recipe({"recipe_id": "R006", "servings": 6})` -> ok
5. model answer: **Shakshuka – 6 servings**

*Ingredients*  
- 9 large eggs (at room temperature)  
- 3 whole red bell peppers, sliced into strips  
- 900 g ripe tomatoes (chopped, or one 400 g tin plus 200 g fresh)  
- 1.5 large onions, sliced  
- 6 garlic cloves, sliced  
- 3 tsp sweet paprika  
- 1.5 tsp ground cumin  
- 0.75 tsp caraway seeds, lightly crushed  
- 0.38 tsp cayenne pepper (optional)  
- 4.5 tbsp olive oil  
- 150 g feta cheese, crumbled (to sprinkle on top)  
- 1.5 handfuls fresh parsley, chopped  
- 1.5 tsp salt, to taste  

*Method*  
1. Heat the olive oil in a wide, shallow pan and cook the onion and peppers over medium heat for 12 min until soft and beginning to colour.  
2. Add the garlic, paprika, cumin, caraway and cayenne and fry for 1 min until fragrant.  
3. Add the tomatoes and salt, then simmer for 15 min, uncovered, until the sauce is thick enough to hold a channel when you drag a spoon through it.  
4. Make six wells in the sauce with the back of a spoon and crack one egg into each.  
5. Cover the pan and cook for 6–8 min, until the whites are set but the yolks still move when you shake the pan.  
6. Scatter over the crumbled feta and parsley and serve straight from the pan with flatbread.  
   _stopped_by=completed, tokens=2189_

## Transcript — after, matrix attached (trial 1)

1. user: Scale the shakshuka to 6 servings.
2. model -> `scale_recipe({"recipe_id": "shakshuka", "servings": 6})`
3. tool: `ERROR: No recipe has id 'shakshuka'. Valid ids are R001, R002, R003, R004, R005, R006; a dish name is not an id. Call search_recipes with the dish name (e.g. query='shakshuka') to get its id, then call scale_recipe again with that id.`
4. model -> `search_recipes({"query": "shakshuka"})` -> ok
5. model -> `scale_recipe({"recipe_id": "R006", "servings": 6})` -> ok
6. model answer: **Shakshuka – 6 servings**

**Ingredients**

- 9 Large eggs (room temperature)  
- 3 Red bell peppers, sliced into strips  
- 900 g ripe tomatoes (chopped, or one 400 g tin + 200 g fresh)  
- 1.5 Large onions, sliced  
- 6 Garlic cloves, sliced  
- 3 tsp sweet paprika  
- 1.5 tsp ground cumin  
- 0.75 tsp caraway seeds, lightly crushed  
- 0.38 tsp cayenne pepper (optional)  
- 4.5 tbsp olive oil  
- 150 g feta cheese, crumbled (for topping)  
- 1.5 handful fresh parsley, chopped  
- 1.5 tsp salt, to taste  

**Method**

1. Heat olive oil in a wide, shallow pan. Cook onion and peppers over medium heat for 12 min until soft and beginning to colour.  
2. Add garlic, paprika, cumin, caraway, and cayenne; fry 1 min until fragrant.  
3. Add tomatoes and salt; simmer 15 min, uncovered, until sauce thickens enough to hold a channel when you drag a spoon through it.  
4. Make six wells in the sauce with the back of a spoon and crack one egg into each.  
5. Cover and cook 6–8 min, until whites are set but yolks still move when shaken.  
6. Scatter crumbled feta and parsley over the top and serve straight from the pan with flatbread.  
   _stopped_by=completed, tokens=3386_

## What the numbers say (5 trials per cell, openai/gpt-oss-20b, temperature 0)

| condition | recovered | model searched first | mean tokens | follow-up calls |
|---|---:|---:|---:|---:|
| before, no matrix | 5/5 | 5/5 | 2072 | 2 |
| after, no matrix | 5/5 | 5/5 | 2799 | 2 |
| before, matrix attached | 5/5 | 0/5 | 2195 | 1 |
| after, matrix attached | 5/5 | 5/5 | 3380 | 2 |

- **Recovery rate did not move (5/5 -> 5/5).** On this model and this failure, "Error 3" was already recoverable: a failed `scale_recipe` plus an available `search_recipes` is enough. I cannot claim the rewrite fixed a failure that was not there. A weaker model, or a case with no obvious next tool, is where the opaque error would bite.
- **Cost went up ~35% (2072 -> 2799 tokens, no matrix).** The longer docstring is re-sent on every lap. The cost of docstring-as-prompt is real and is paid on every call, not just on failures.
- **Behaviour became prescribed, not just recoverable.** With the matrix attached, the old model skipped `search_recipes` (0/5) and read R006 straight from the matrix: faster, and equally correct. The new error tells it to search, and it always does (5/5): one extra call and ~1200 more tokens. The rewrite trades a shortcut for a deterministic path.
- Not fixed on purpose (one error path only): `get_allergen_profile` still returns `Error 4`.
