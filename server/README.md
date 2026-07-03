# bunnyland-hearthsim (server plugin)

The out-of-tree Bunnyland plugin package `bunnyland_hearthsim`.

## Development

Tests run against a sibling `bunnyland-server` checkout without installing anything —
`tests/conftest.py` puts both this package's `src/` and `../bunnyland-server/src` on
`sys.path`. From this `server/` directory:

```bash
# uses the sibling bunnyland-server's virtualenv/deps
uv run --project ../../bunnyland-server -m pytest
# or, if bunnyland + relics are already importable:
python -m pytest
```

Lint:

```bash
uv run ruff check src tests
```

## Loading into the server

```bash
bunnyland serve --module bunnyland_hearthsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported.

## What it contributes

- **Components** — `IngredientComponent`, `StoveComponent`, `MealComponent`, `BuffComponent`,
  `FreshnessComponent`.
- **A recipe registry** (`recipes.py`) mapping required ingredient tags to a finished meal,
  with deterministic matching.
- **Two verbs** — `cook` (ingredients + a reachable stove -> a meal) and `eat-meal` (restore
  hunger, apply a timed buff, and share a feast).
- **Two consequences** — `SpoilageConsequence` (freshness decay) and `BuffExpiryConsequence`
  (buff timers), both derived purely from the world epoch.
- **Feast logic** — eating with others in the room warms social bonds and eases the social
  need, reusing the core social layer.
- **Prompt fragments** rendering buff/stove/meal-freshness state into human and AI prompts.
- **A worldgen hook** tagging generated kitchens and food.
- **Spawn factories** — `spawn_ingredient`, `spawn_stove`, `spawn_meal`.
