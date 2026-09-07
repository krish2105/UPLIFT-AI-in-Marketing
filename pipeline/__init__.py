"""The ETLs.

Four pipelines — weather, calendar, events, footfall — each runnable on its own
and each with a `--verify` mode that re-checks its own output and writes the
result to docs/results/. Verification is part of the pipeline rather than a
separate test because the thing being checked is the DATA, and data goes stale
in ways code does not.
"""
