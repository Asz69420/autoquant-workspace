# Quandalf Latest Response

**Timestamp:** 2026-03-05 18:24:12 AEST
**Prompt:** The pipeline is only doing Claude strategies now it is 100% Claude so why would we kill it?...
**Status:** COMPLETE

---

There it is. The pipeline is **not** 100% Claude strategies. Here's the actual breakdown:

**Today: 271 specs generated, only 18 have "claude" in the name.**

The other 253 are pipeline-generated thesis/directive specs. And look at the entry conditions on those:

```
"Require candidate signal confidence >= 0.60"
"Require thesis regime match before long entry"
"Use signal: alignment_entry"
```

These are **not executable rule conditions**. `confidence`, `alignment_entry`, `thesis regime match` â€” none of these are real dataframe columns. That's why they produce 0 trades. The pipeline takes Claude's research cards as raw material but then wraps them in its own directive/variant layer that generates formally invalid specs.

The **PROMOTED_INDEX being 100% Claude** means something different â€” it means only the specs I (Quandalf) designed by hand ever actually work. The pipeline's spec-writing process is what breaks them, not the research input.

So the issue was never "kill the pipeline's research intake" â€” it's that the pipeline's **spec generation layer** (directives, variants, thesis-to-spec conversion) produces structurally invalid strategies that can never fire a trade. It's burning 1800+ backtests/day testing specs that reference non-existent columns.

The research cards and recombine are fine as inspiration sources. The problem is the layer that converts them into strategy specs.