# Reviewed fixture workflow

Tests copy a generated blank `review.csv` into a temporary fixture run before inserting explicit
human-like review values. Tests never rewrite a repository run record or interpret fixture values
as real MTL approval.
