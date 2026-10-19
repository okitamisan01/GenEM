# GenEM research notes

Reviewed: 2026-10-20. This is a source-based design survey, not an experimental replication.

## Sources

- [Official project, demonstration clips and study descriptions](https://generative-expressive-motion.github.io/)
- [Mahadevan et al., HRI 2024, arXiv:2401.14673v1](https://arxiv.org/html/2401.14673v1)
- [Officially linked Appendices, 12 pages](https://drive.google.com/file/d/1Ny07f0dpc0CJyyag3KTwfpHdv_-CSz_p/view)

## Findings

1. **Purpose:** adaptable, composable expressive behavior from language, rather than a dedicated dataset for every social setting.
2. **Architecture:** human expression planning, embodiment-specific procedure generation, parameterized code generation, and optional feedback processing.
3. **Language grounding:** few-shot prompts connect social instructions to robot capabilities.
4. **Skills:** pre-existing APIs and previously generated reusable functions support composition.
5. **Parameters:** generated functions encode policies with adjustable motion parameters.
6. **Feedback:** revisions can change the procedure and code, or code alone.
7. **LLM:** study generation used GPT-4 `gpt-4-0613`, temperature 0.
8. **Embodiments:** a mobile robot with pan/tilt, base, lights and speech; simulated Spot for transfer experiments.

These findings are supported by paper sections 3–5 and the official project page.
The study results are not validation of this HSR implementation.

9. **Public material:** the site links paper, appendices and embedded video comparisons.
Appendix A documents prompts; Figures 6–7 show the quadruped API. Page 4 was
visually inspected: functions cover pose retrieval/conversion and body translation,
strafe and rotation, with type signatures and docstrings. Appendix A.4 covers
feedback, B study inputs, and C generated samples. These examples do not provide
an independently deployable full robot runtime. No official runtime repository link
was found on the inspected project page; this does not prove none exists elsewhere.
The PDFs and videos are not redistributed in this repository.
10. **HSR adaptation:** replace embodiment APIs, perception assumptions, control
transport and limits. This project's interface and validation policy are newly written;
no original runtime code was imported.

## Deliberate implementation differences

This version uses a bounded JSON/YAML instruction language, a single API call per
initial generation/revision, and a deterministic offline demonstration backend.
There is no generated Python execution, original multi-module prompt replication,
learned-skill library, feedback router, or reproduction of human-subject results.
The previous behavior and user feedback are supplied to each API revision and
saved as provenance. The name “GenEM-inspired” refers to this conceptual workflow.
The implementation's safety constraints and HSR integration scaffold are local design choices.
