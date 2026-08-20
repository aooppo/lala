# CLI Contract

`video motion-smoke-test --keyframe ID [--model gen4_turbo --duration 5 --ratio RATIO
--max-runway-credits N] (--live|--dry-run)`

`video motion-generate --keyframe ID --model MODEL --duration SECONDS --ratio RATIO
--variations N --motion-smoke-run-id RUN --motion-smoke-review-file FILE
--max-runway-credits N (--live|--dry-run)`

`motion-smoke-test --live` is fixed to one `gen4_turbo` result at five seconds and a cap no greater
than 25 credits. Live post-smoke exits with `BLOCKED_EXTERNAL` before provider construction when
any gate fails, including an incomplete/failing human review copy. Dry-run validates the same
provenance and cap rules, exits successfully with `paid_calls: 0`, and writes the standard bundle.
