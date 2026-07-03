# Bunnyland Hearthsim

Out-of-tree [Bunnyland](https://github.com/thalismind/bunnyland-server) plugin that adds a
Sims-style **cooking & meals** pack. Characters gather tagged ingredients, **cook** them at a
stove into a meal, and **eat** that meal to relieve hunger and pick up a timed buff — and if
they eat with company, it becomes a shared **feast** that warms everyone's bonds. Food is not
forever: cooked dishes track **freshness** and eventually spoil.

This repo intentionally keeps all cooking work outside the main `bunnyland-server` repo.

## Layout

- `server/` - Python Bunnyland plugin package with the ingredient/stove/meal/buff/freshness
  components, the recipe registry, the `cook` and `eat-meal` verbs, the spoilage and
  buff-expiry consequences, feast logic, prompt fragments, a worldgen enrichment hook, spawn
  factories, and tests.

## Server Plugin

The plugin exposes `bunnyland_hearthsim.bunnyland_plugins()` and contributes:

- `IngredientComponent`, `StoveComponent`, `MealComponent`, `BuffComponent`,
  `FreshnessComponent` - the cooking-pack state.
- A module-level **recipe registry** mapping required ingredient tags to a finished meal.
- `cook` - cook at a reachable stove, consuming inventory ingredients into a meal (with exact
  rejection reasons: no stove reachable, missing ingredients, unknown recipe, and so on).
- `eat-meal` - restore hunger via the shared need meter, apply a timed meal buff, and share a
  feast with others in the room. Reuses the core `FoodEatenEvent`/`HungerChangedEvent` path so
  existing mood/projection listeners react as they do for ordinary food.
- `SpoilageConsequence` - decays food freshness over ticks and marks spoiled food (which then
  grants no buff and is unpleasant to eat).
- `BuffExpiryConsequence` - removes meal buffs once their epoch is reached.
- `hearthsim_fragments` - renders buff, stove, and meal-freshness state into human and AI
  prompts.
- `HearthWorldgenHook` - tags generated kitchens as stoves and generated produce/meat/staples
  as ingredients.
- `spawn_ingredient`, `spawn_stove`, `spawn_meal` - spawn factories.

## Running

This package builds no containers. It is loaded into the stock server via `--module`:

```bash
bunnyland serve --module bunnyland_hearthsim
```

`default_enabled=True`, so no `--plugin` flag is required once the module is imported. The
`bunnyland_hearthsim` package must be importable by the server (installed into the server's
environment, or on `PYTHONPATH`).

## Development

Run server tests against a sibling `bunnyland-server` checkout (no install required —
`server/tests/conftest.py` puts both packages on `sys.path`). From `server/`:

```bash
uv run --project ../../bunnyland-server -m pytest
uv run --project ../../bunnyland-server ruff check src tests
```

See [`server/README.md`](server/README.md) for more detail.

## Contributing & Conduct

This plugin follows the Bunnyland project's
[contribution guidelines](CONTRIBUTING.md) and [code of conduct](CODE_OF_CONDUCT.md),
which point back to the `bunnyland-server` repository.

## License

Licensed under the GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
