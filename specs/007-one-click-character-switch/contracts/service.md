# Service Contract: Character Application Layer

## CharacterService

The UI and CLI construct one `CharacterService(project_root, preview_backend=...)`. Public methods
return typed domain values or redacted user-safe errors; they never print or execute shell commands.

### `list_characters() -> CharacterRegistry`

Read-only. Validates registry invariants and current profile hashes. Creates no migration unless the
service is explicitly initialized with bootstrap enabled.

### `show(character_id) -> CharacterView`

Read-only. Returns current registry/profile/build/preview evidence. Unknown or unsafe IDs fail.

### `import_character(inputs, display_name=None, created_by) -> CharacterProfile`

`inputs` must contain exactly the three required roles plus supported optional roles. Validation
occurs before registration. The method copies bytes to canonical storage, writes provenance and one
profile snapshot, then registers a non-active entry. It never invokes preview providers.

### `build(character_id) -> CharacterBuild`

Revalidates profile and source hashes, creates deterministic selected-reference/preflight evidence,
and returns/builds `READY_FOR_GENERATION`. Active character is not mutated.

### `preview(character_id, mode, budgets=None) -> CharacterBuild`

Requires a staging profile. `offline` records a plan and returns `READY_FOR_GENERATION` with no media
or provider calls. `live` delegates to injected provider-neutral preview operations backed by the
existing runners; it requires one static and one motion result. Partial results are retained and the
character remains non-activatable.

### `approve_and_activate(character_id, expected_revision=None) -> ActivationEvent`

Revalidates profile required sources, both preview media/hashes, and current registry. Copies exact
sources into approved anchors if necessary, writes new old/new profile snapshots, then atomically
replaces the registry under lock only if expected revision/active match. Returns the durable event.

### `reject(character_id, expected_revision=None) -> CharacterProfile`

Writes a rejected snapshot and atomic registry update; current active ID cannot change.

## Preview operations

`StaticCharacterPreviewOperation` and `MotionCharacterPreviewOperation` are provider-neutral
protocols. Fakes may write validated local fixture media in tests. Production implementations call
the existing runners and return only normalized `PreviewArtifact` data.

## Error contract

Errors expose a stable code, affected role/character when safe, and ordinary-language message.
Technical cause text is recursively redacted. UI mapping includes:

- missing/corrupt/unsupported/oversized photo;
- unsafe path or filename ignored;
- incomplete or hash-changed character;
- preview not authorized or failed;
- character not ready for activation;
- registry changed in another session;
- registry/profile integrity failure.

No method fabricates a reviewer, provider task ID, prompt provenance, or approval timestamp.
