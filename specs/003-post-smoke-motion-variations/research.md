# Research Notes

- The existing `RunwayMotionProvider` already translates image-to-video requests, polls by task
  ID, downloads MP4 output, and records estimated credits. Reusing it keeps SDK details outside
  orchestration.
- `VideoRunStorage` defines the immutable thirteen-artifact evidence contract and
  `load_external_review_row` defines the modern reviewed-copy boundary. A narrow legacy motion
  review adapter is needed for the already completed real smoke run's historical QA header.
- Verified Runway configuration prices `gen4_turbo` at five credits/second; therefore the fixed
  five-second smoke ceiling is 25 credits and post-smoke estimates are
  `5 * duration_seconds * variations` for that model. A request must state an explicit cap and is
  rejected before provider construction when the estimate is above it. Other configured models
  use their own verified per-second rate.
