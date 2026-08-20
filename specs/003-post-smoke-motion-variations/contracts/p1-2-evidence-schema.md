# P1-2 Dry-Run Evidence Schema

The planning dry-run writes `p1-2-dry-run.json` outside approved-source directories. It is
append-only derived evidence and never replaces the Smoke run or its `review.csv`.

```json
{
  "schema_version": "p1-2-motion-variation-plan-v1",
  "stage": "P1-2",
  "mode": "DRY_RUN",
  "live_call": false,
  "paid_calls": 0,
  "motion_smoke_run_id": "LALA-VIDEO-20260820-040258-MOTION-SMOKE-001",
  "motion_smoke_qa": {
    "status": "passed_by_owner_instruction",
    "source_review_copy_unchanged": true,
    "attestation_source": "owner task request"
  },
  "approved_keyframe": {"id": "pilot_home_context", "path": "...", "sha256": "..."},
  "baseline_prompt": {"path": "prompts/home-broll-v3.txt", "sha256": "897c00baabbf51304268c842d811bec1927fafc4e0042ad11bf63867933e69b5", "utf16_units": 892},
  "invariants": {"model": "gen4_turbo", "duration_seconds": 5, "ratio": "1280:720"},
  "variations": [
    {
      "variation_id": "MOTION-VAR-001",
      "prompt_path": "prompts/motion-variation-v1.txt",
      "prompt_sha256": "<variation prompt hash>",
      "prompt_utf16_units": "<measured UTF-16 units>",
      "estimated_runway_credits": 25,
      "expected_risk": "low",
      "qa_acceptance_criteria": ["..."],
      "submission": {"status": "NOT_SUBMITTED", "provider_task_id": null, "output_sha256": null}
    }
  ],
  "budget": {
    "credits_per_second": 5,
    "per_variation_credits": 25,
    "planned_variations": 3,
    "total_estimated_credits": 75,
    "single_live_cap_credits": 25
  },
  "owner_gate": {"variation_plan_approved": false, "live_authorized": false}
}
```

Required evidence for any later real candidate is the same per-variation record plus provider task
ID, submission/download attempts, actual credits, output path/hash, technical media evidence, and
one blank human QA row. A task ID is an idempotency boundary; no automatic resubmission is allowed.
