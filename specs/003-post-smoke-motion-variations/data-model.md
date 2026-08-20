# Data Model

`MotionVideoRequest` remains the provider-neutral request entity. A motion variation run records
the smoke run/review-copy IDs and digests, approved keyframe digest, prompt path/text/digest,
model, duration, ratio, variation index, credit estimate/cap, provider task ID, output hash, and
one blank QA row per output. Motion-only runs mark script/audio evidence not applicable without
altering any approved source. The smoke run's original `review.csv` is append-only and blank;
human decisions live only in the external copy under `outputs/reviews/`. A narrow adapter maps the
known historical motion-only header to the current decision names, while unknown headers fail
closed.
