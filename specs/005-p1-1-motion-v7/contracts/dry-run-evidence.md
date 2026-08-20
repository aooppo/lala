# V7 Dry-Run Evidence Contract

The V7 dry-run stores the following additional fields inside existing run JSON artifacts; it does not add run artifacts.

```json
{
  "action": "motion_v7_dry_run",
  "mode": "DRY_RUN",
  "provider_call_count": 3,
  "submission_count": 0,
  "candidate_metadata": [
    {
      "candidate_id": "v7-a-stability-first",
      "prompt_file": "prompts/p1-1-motion-v7-a-v1.txt",
      "prompt_utf16_units": 0,
      "experiment_level": "stability_first",
      "motion_intent": "...",
      "provider": "runway",
      "estimated_credits": 25,
      "live_allowed": false,
      "provider_task_id": null,
      "live_submission": false
    }
  ],
  "subject_lock_comparison": {
    "measurement_scope": "color_region_proxy",
    "human_qa_authority": "not_automatic",
    "v6": {"x_drift_px": -14.0, "diagnostic_status": "OUTSIDE_THRESHOLD"},
    "v7": {"status": "PENDING"},
    "delta": {"status": "PENDING"}
  }
}
```

The review CSV uses the existing schema. It has exactly one blank human-review row per candidate. It is not a V7 diagnostic or package result.
