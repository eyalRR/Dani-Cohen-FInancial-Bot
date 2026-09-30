"""
Named Finviz filter presets -- but ONLY for filter combinations that are genuinely universal:
useful as a reusable building block across many unrelated callers, not tied to one particular use
case. Each entry's own comment must describe its purpose in its own terms (what it filters for and
why you'd reach for it). Criteria for one particular use case belong in a plain filters JSON file
wherever makes sense for that use case (passed to `run_scan.py --filters <path>`), not registered
here.

**A preset's dict value and a filters JSON file's content are the exact same shape** -- a flat
`{"Finviz filter name": "option value", ...}` dict of strings, nothing else (no nested structures,
no dict comprehensions/unpacking). That means the dict itself is directly copy-pasteable between
the two forms -- but only the `{...}` dict, not any surrounding Python scaffolding: strip the
variable name/assignment, any inline `#` comments, and any trailing comma before pasting into a
`.json` file (Python dict literals tolerate all three; JSON tolerates none of them). Keep every
entry a plain literal dict (no `**{...}` unpacking, which is valid Python but not valid JSON) so
the underlying `{...}` block stays portable either direction.

Currently empty -- no filter combination has been universal enough to earn a spot here yet. Add an
entry only when a combination is clearly reusable as-is by callers that have nothing to do with
each other. Illustration of the format and the bar (NOT currently registered):

    # Baseline liquidity/quality filter, not tied to any one particular use case -- a starting
    # point for narrowing the ~10,000-stock universe down before layering on more specific criteria.
    LIQUID_OPTIONABLE_BASE = {
        "Option/Short": "Optionable and shortable",
        "Average Volume": "Over 1M",
        "Price": "Over $10"
    }
    PRESETS["liquid_optionable_base"] = LIQUID_OPTIONABLE_BASE

The `{...}` block above (no trailing comma, no comments inside it) is what's directly
copy-pasteable into a `.json` file as-is; the surrounding comment/variable-name/`PRESETS[...] = `
lines are Python-only scaffolding for registering it here, not part of the portable shape.
"""

PRESETS: dict[str, dict[str, str]] = {}
