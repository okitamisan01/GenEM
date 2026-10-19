# Scope and limitations

| Category | Status |
|---|---|
| Inspired by GenEM | language-to-parameterized skills, composing primitive sequences, language feedback revisions |
| Newly implemented for this project | JSON/YAML grammar, strict validator, mock Skill API, offline fixtures, generic API backend, JSONL provenance, Jazzy Docker packaging, disabled HSR boundary |
| Implemented and verified | CPU Docker build; two ament_python packages; parser/validator/executor/backend tests; five Mock scenarios and feedback loop |
| Implemented but not verified against external systems | live LLM provider integration; optional GPU device exposure; second physical PC workflow |
| Not implemented | working HSR motion adapter, physical robot communication, real speech/perception, base control, collision checking, original staged LLM architecture and feedback router, learned-skill library, user studies |

The HSR class is a scaffold that raises before communication; its presence must not
be reported as successful HSR control. Source limits are not accepted hardware limits.
The mock policy constrains independent logical steps, not real joint trajectories,
acceleration, collision clearance, gaze transforms or timing. Mock completes immediately.

Offline generation is a deterministic fixture selector with limited English keywords;
it does not understand arbitrary requests or represent LLM performance. Unsupported
feedback is an error. Repeated enthusiastic/slower feedback may hit policy bounds
and will be rejected rather than silently adjusted.

API transport tests use fake keys and injected responses. No external provider/model
was selected or charged. The single-call backend does not reproduce the original
multi-stage architecture. There is no claim of equivalent behavioral quality.
Responses must contain plain JSON/YAML; fenced Markdown and arbitrary programs are refused.
A read timeout is not an overall generation deadline; provider-specific rate-limit,
streaming and cancellation logic remains future work.

History is intended for a single CLI process. It contains user language and generated
behaviors, so keep it local as appropriate; no concurrent-writer lock, encryption,
identity tracking or experiment consent workflow is included.

The Docker base digest is pinned, but apt/rosdep dependencies are not snapshot-locked.
Validated host/image architecture is amd64. Other architectures, Docker Desktop,
GPU, actual robot networking and another PC were not tested.

Future work: verified HSR adapter/simulator tests; staged planner comparisons;
persistent user preferences and person grounding; versioned learned skills;
longitudinal HRI evaluation with consent and a reproducible human-feedback protocol.
