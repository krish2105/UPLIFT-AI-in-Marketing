"""Creative composition and compliance checking.

Both are DETERMINISTIC and neither calls a language model.

For compliance that is the whole point: a rule engine whose verdict depends on a
model's mood cannot be audited, and the claim this application makes is that
every verdict cites the clause it came from. The rules are in the brand kit, the
matching is regex over normalised text, and the same creative gets the same
verdict every time.

For composition it is a reproducibility requirement: the persona panel scores
these creatives, and a panel score is only meaningful if the thing being scored
is stable. Phase C adds a language model to WRITE variants; these compose and
check them.
"""
