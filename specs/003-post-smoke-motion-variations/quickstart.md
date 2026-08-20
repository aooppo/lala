# Quickstart

1. Run the separate bounded smoke preview or, only with owner authorization, the one-result
   `gen4_turbo`/five-second smoke (maximum 25 credits).
2. Copy its blank `review.csv` into `outputs/reviews/` and fill the motion/technical pass fields,
   MTL readiness, reviewer, and timezone-aware review time in the copy.
3. Use `video motion-generate --dry-run` with the smoke run ID, review copy, same keyframe, exact
   smoke prompt provenance, and an explicit cap to inspect zero-call evidence. Start with two
   additional variations; never exceed five.
4. Only after owner authorization, exact video permission, credentials, and reviewed evidence use
   `--live`; select preferred downloaded variations from the generated blank QA sheet.
