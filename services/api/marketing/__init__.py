"""The marketing models.

Four things, in the order a planner needs them: what demand will be
(`forecast`), who the customers are (`segments`), where the money should go
(`allocator`), and whether it worked (`uplift`).

None of them calls a language model. That is deliberate: a forecast, a
segmentation, an allocation and a lift estimate are all things with correct
answers and established methods, and routing them through a model would make
them unreproducible without making them better. The crew in Phase C reasons
ABOUT these outputs; it does not produce them.
"""
