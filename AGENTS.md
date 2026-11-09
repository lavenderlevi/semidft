# AGENTS.md — Semiconductor DFT Workflow (`semidft`)

This file defines behavioral, engineering, and research-quality rules for all AI coding agents working in this repository. It combines conservative coding practices with the project-specific direction of a research-oriented, CLI-first semiconductor DFT workflow.

These instructions apply to the entire repository unless a more specific `AGENTS.md` exists in a subdirectory. A nested instruction file may add detail for its subtree, but must not silently weaken the scientific-integrity requirements in this file.

The behavioral baseline in this file is adapted from [andrej-karpathy-skills `CLAUDE.md`](https://github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md), with additional rules for this semiconductor DFT research codebase.

---

## 1. Mandatory Project Context: Read Before Acting

**Do not start implementation until you have inspected the project documentation and the current repository state.**

At the beginning of every task:

1. Read `docs/Instruction-plan for semidft.md` in full. Treat it as the primary project-specific instruction and planning document.
2. Inspect the complete `docs/` tree. Read every document relevant to the requested task, including technical specifications, research notes, implementation plans, decisions, and validation criteria.
3. Read the repository's current `README.md`, `pyproject.toml`, `pixi.toml`, lockfile, relevant source modules, tests, and CI configuration where present.
4. Search for other `AGENTS.md` files that apply to the files being changed.
5. Inspect `git status`, the current branch, and the relevant recent history before editing. Do not overwrite or discard pre-existing user changes.

### Documentation precedence

Use the following order when interpreting requirements:

1. The user's current task and explicit constraints.
2. This `AGENTS.md` for agent behavior and engineering discipline.
3. `docs/Instruction-plan for semidft.md` for project-specific intent, scope, requirements, and priorities.
4. Other relevant documents under `docs/` for detailed scientific and technical specifications.
5. Existing implementation and tests for established behavior not contradicted by the higher-priority sources.

If two authoritative documents conflict, do not silently choose one. Identify the exact conflict, explain its impact, and ask for clarification when the decision materially affects scientific validity, public interfaces, data formats, dependencies, or project scope. For a low-risk implementation detail, choose the least surprising option, state the assumption, and keep the change easy to revise.

If the required project documents are missing or inaccessible in the agent's environment, stop before making project-specific implementation changes. Report which files could not be read. Do not pretend that prior conversation context is a substitute for the current repository documentation.

---

## 2. Project Mission and Scope

`semidft` is a **research-oriented, CLI-first Python toolkit** for automating semiconductor crystal-structure preparation, Density Functional Theory (DFT) calculations using Quantum ESPRESSO (QE), scientific post-processing, validation, and computational provenance.

The goal is not merely to convert CIF files into QE input files. The project should help produce calculations that are scientifically interpretable, numerically checked, traceable, and reproducible.

The project direction established so far is:

- Primary domain: semiconductor materials and computational materials science.
- Primary DFT engine: Quantum ESPRESSO.
- Primary interface: command-line interface (CLI), with reusable Python APIs underneath.
- Environment management: Pixi, with a committed lockfile.
- Crystal-structure tooling: ASE, pymatgen, and spglib where justified by the documented architecture.
- Initial validation materials discussed: Si, Ge, and GaAs; additional semiconductor families are introduced only according to the project documents and completed validation stages.
- Research priorities: crystallographic correctness, consistent pseudopotential and DFT settings, numerical convergence, correct electronic-structure analysis, and provenance.

These are project-direction statements, not permission to add every mentioned feature immediately. **The current documentation and milestone scope determine what is in scope for a particular task.** Do not implement future-phase features unless requested or required by the active milestone.

### Scope-control rules

- Prefer a correct, tested, narrow implementation over a broad but weakly validated framework.
- Do not add a GUI, web service, distributed architecture, machine-learning subsystem, general-purpose workflow platform, or database server unless the project documents or user explicitly require it.
- Do not introduce speculative abstractions for hypothetical future DFT engines or material classes.
- Keep the CLI as an interface layer. Scientific and workflow logic belongs in importable Python modules.
- Do not replace Quantum ESPRESSO, ASE, pymatgen, or another documented component without presenting the reason and migration impact first.

---

## 3. Think Before Coding

**Do not assume. Do not hide confusion. Surface trade-offs before implementation.**

Before changing code:

- Restate the task as concrete outcomes when the task is non-trivial.
- Identify assumptions about input data, physical models, units, numerical settings, software versions, and expected behavior.
- Check whether the request has multiple plausible interpretations.
- Prefer an existing project capability or a simpler implementation when it meets the requirement.
- Explain meaningful alternatives and trade-offs instead of silently choosing one.
- Ask a focused clarification question when a missing decision could change scientific meaning or create expensive rework.

Do not ask questions whose answers can be determined from the repository or its documentation. Do not block on trivial details: choose a conservative default, disclose it, and make it configurable only when configuration is genuinely needed.

For multi-step tasks, provide a short plan with verification criteria before implementation:

```text
1. [Action] → verify: [observable check]
2. [Action] → verify: [observable check]
3. [Action] → verify: [observable check]
```

---

## 4. Simplicity First

**Implement the minimum code that correctly satisfies the requirement.**

- Do not add features beyond the task or active milestone.
- Do not introduce abstractions for one-off operations without a demonstrated need.
- Do not add configuration options “for flexibility” unless there is a real use case.
- Do not add dependencies when the standard library or an existing project dependency is sufficient.
- Do not add defensive handling for impossible states; validate realistic external inputs and failure modes instead.
- Avoid premature parallelism, caching, plugin systems, service layers, and generic frameworks.
- Avoid large functions, but do not fragment straightforward logic into excessive wrappers.
- If a small, direct implementation solves the problem, use it.

Before adding an abstraction, answer: **What concrete duplication, complexity, or correctness risk does this abstraction remove today?** If there is no clear answer, do not add it.

---

## 5. Surgical Changes

**Change only what is necessary for the requested outcome.**

When editing existing code:

- Read the target module and its callers before modifying it.
- Match the existing naming, formatting, typing, and error-handling conventions unless they are demonstrably broken or contradicted by project standards.
- Do not refactor adjacent code, rewrite comments, rename unrelated symbols, or reformat entire files as collateral work.
- Do not remove pre-existing code merely because it appears unused. Mention unrelated issues separately.
- Remove only imports, variables, functions, and files made obsolete by your own changes.
- Preserve backward compatibility unless a breaking change is explicitly requested or approved.
- Do not overwrite user-generated structures, calculation outputs, pseudopotential files, or local configuration.

Every changed line should be traceable to the task, a required test, or a documented correctness fix.

Before editing, inspect `git diff` and `git status`. After editing, inspect the diff again and ensure it contains no unrelated changes.

---

## 6. Research and Scientific Integrity

Scientific correctness takes priority over convenience, speed, or attractive output.

### 6.1 Do not fabricate scientific information

- Never invent calculation results, benchmark values, convergence thresholds, pseudopotential metadata, literature values, or citations.
- Clearly distinguish measured/computed values, published reference values, illustrative examples, and assumptions.
- Do not report a calculation as successful merely because a process exited with code zero.
- Do not describe a result as converged unless the relevant convergence criteria were actually checked.
- Do not claim experimental agreement based on a comparison with a different functional, pseudopotential, temperature, structure, or physical definition without explaining the mismatch.
- Preserve raw outputs. Derived or normalized results must not silently replace source data.

### 6.2 Preserve physical meaning

For crystal structures and transformations:

- Preserve composition, species identity, lattice geometry, periodicity, and atomic positions under format conversion, within documented numerical tolerances.
- Track primitive/conventional-cell changes and all non-trivial cell transformations. Record transformation matrices and relevant standardization settings.
- Do not silently reduce cells, reorder sites in a way that breaks species/pseudopotential mapping, symmetrize structures, remove atoms, or modify occupancies.
- Treat disordered or partially occupied CIF structures explicitly. Reject unsupported cases with a clear explanation rather than silently converting them into an arbitrary ordered structure.
- Validate malformed cells, non-finite coordinates, duplicate sites, implausible short distances, and missing species data where appropriate. Do not label every unusual structure as invalid without a defensible criterion.
- Store the original input structure separately from standardized, transformed, and relaxed structures.

For DFT calculations:

- Keep the exchange-correlation functional, pseudopotential dataset, relativistic treatment, valence configuration, and numerical parameters explicit.
- Do not mix pseudopotentials with incompatible exchange-correlation functionals or incompatible physical assumptions.
- Verify element-to-pseudopotential mapping before generating QE input.
- Record pseudopotential source, version, type, metadata, filename, and cryptographic checksum where available.
- Do not download, redistribute, or commit pseudopotential files without checking the source, license, and project policy.
- Never guess `ecutwfc`, `ecutrho`, k-point meshes, smearing, number of bands, or convergence thresholds and present them as validated settings. A proposed starting value must be labeled as provisional and checked against the pseudopotential recommendations and convergence tests.
- Apply unit conversions explicitly. Never pass a bare numeric value between modules when its unit or convention is ambiguous.
- Keep QE-specific units and syntax at the engine boundary; use the project's documented internal unit convention elsewhere.
- Record relevant software versions, compiler/MPI details when available, input parameters, pseudopotential checksums, and workflow definitions.

### 6.3 Convergence and calculation state

- Treat process completion and scientific convergence as separate states.
- Parse and verify QE's actual convergence indicators, not only the process exit code or presence of an output file.
- For relaxations, check the documented force and, where relevant, stress/cell convergence criteria.
- Evaluate cutoff and k-point convergence for the property being studied; convergence of total energy alone does not automatically establish convergence of band edges, forces, stress, or defect energies.
- Do not use one fixed k-point mesh for cells of different sizes without considering reciprocal-space density.
- Preserve all convergence runs and settings so the final choice can be justified.
- Do not automatically continue downstream workflows using failed, unconverged, or unparsable upstream results.

### 6.4 Electronic-structure analysis

- Distinguish Kohn–Sham band gaps from experimental, hybrid-functional, and GW-corrected gaps.
- Do not assume a high-symmetry band path necessarily contains the global VBM and CBM.
- Distinguish direct and indirect gaps using the k-space locations of the relevant band extrema.
- Account for spin, spin-orbit coupling, occupations, metallicity, and band indexing when relevant to the material and requested analysis.
- Do not infer physical conclusions from plots alone when the underlying numerical data can be inspected.

### 6.5 External scientific claims

When a task requires external scientific or software facts, consult primary sources where practical: official QE documentation, official ASE/pymatgen/spglib documentation, pseudopotential library documentation, and relevant peer-reviewed literature. Record the source and version/date in project documentation when the decision affects a scientific protocol.

---

## 7. Units, Data Models, and Interfaces

- Follow the unit conventions documented in `docs/` and existing core models.
- Use explicit names or unit-aware types for physical quantities (for example, `ecutwfc_ry`, `force_ev_per_angstrom`). Avoid ambiguous names such as `energy`, `cutoff`, or `length` at interfaces where units matter.
- Centralize conversion constants and conversion functions. Do not duplicate conversion factors across modules.
- Validate configuration and external data at system boundaries.
- Keep internal models independent of CLI presentation and QE text formatting.
- Use stable, versioned serialization schemas for manifests and result files when required by the project.
- When changing a data model or serialized schema, add compatibility/migration handling or explicitly document the breaking change.
- Do not silently discard metadata that may affect scientific interpretation or reproducibility.

---

## 8. Python Engineering Standards

Follow the conventions already established in the repository. If no convention exists, use these defaults:

- Target the Python version specified by `pyproject.toml` and `pixi.toml`; do not independently change it.
- Use type hints for public functions and important data structures.
- Add docstrings to public APIs and functions implementing non-obvious scientific logic. Explain physical assumptions, units, and references where relevant.
- Prefer small, cohesive functions with explicit inputs and outputs.
- Use domain-specific exceptions for expected project errors; do not swallow exceptions or catch `Exception` broadly without a clear boundary-level reason.
- Avoid mutable global state.
- Use `pathlib.Path` for filesystem paths.
- Use `subprocess.run` with argument lists, explicit working directories, captured/redirected output, and checked return codes. Do not use `shell=True` for QE execution.
- Avoid hard-coded machine-specific paths. QE executable paths and resource settings must come from documented configuration or explicit CLI options.
- Do not make network access, pseudopotential downloads, or external database queries happen implicitly during normal calculations.
- Keep logging useful and deterministic. Send progress/diagnostics to stderr where appropriate and preserve machine-readable output on stdout when the CLI supports it.
- Return meaningful non-zero exit codes for failed commands.

Do not introduce a dependency unless it is needed for the task. When adding or changing dependencies, update the appropriate project metadata and Pixi lockfile using the repository's established process.

---

## 9. CLI and Workflow Behavior

- CLI commands should be predictable, composable, and documented with examples.
- Avoid interactive prompts by default; support explicit arguments/configuration so agents and scripts can run non-interactively.
- Validate user input before launching an expensive calculation.
- Provide a dry-run or input-validation path where appropriate, but do not claim it validates scientific convergence.
- Keep CLI commands thin: delegate to tested Python APIs.
- Use explicit calculation IDs and isolated run directories.
- Do not overwrite an existing calculation directory or raw output unless the user explicitly requests it. Prefer a new run ID or an explicit, validated resume operation.
- Separate immutable input artifacts, raw engine output, parsed results, and derived analysis products.
- Preserve the exact QE input used for every run.
- Make retries explicit. Do not silently modify calculation parameters after a failure.
- Apply cleanup only to known temporary files and only when no downstream calculation depends on them.

---

## 10. Testing and Verification

**Define success criteria, test them, and continue until verified or blocked.**

Use the test categories already defined by the repository. If they do not yet exist, distinguish at least:

1. **Unit tests:** parsing, validation, transformations, unit conversions, hashing, configuration, and analysis algorithms; no QE executable required.
2. **Integration tests:** real QE input generation and small QE runs; clearly mark tests that require QE, MPI, or pseudopotentials.
3. **Scientific validation tests:** known structures and properties with method-consistent reference values and documented tolerances.
4. **Regression tests:** fixed fixtures for parser behavior, serialized outputs, and established workflows.
5. **Property/invariant tests:** composition preservation, volume relations, coordinate equivalence modulo periodicity, deterministic serialization, and other physical/data invariants.

Testing rules:

- Add or update tests with every bug fix and behavior change.
- For a bug, first add a test that reproduces it when practical; then fix the implementation.
- Do not weaken tolerances merely to make tests pass. Explain the physical or numerical basis for tolerances.
- Keep fast tests separate from expensive DFT integration tests.
- Do not require a user's private pseudopotential files in the default unit-test suite.
- Use small, documented test structures and minimal calculations for integration tests.
- Test failure paths: missing executable, missing pseudopotential, malformed input, QE non-zero exit, unconverged output, parser failure, and interrupted execution where practical.
- Run targeted tests first, then the relevant broader suite.
- Run linting, formatting checks, and type checks that are configured in the repository.
- Inspect the final diff and test output before reporting completion.

Never claim a check passed unless it was actually run and its result observed. If a test could not be run because QE, MPI, a pseudopotential, or hardware was unavailable, state that limitation precisely.

---

## 11. Pixi and Environment Management

- Treat `pixi.toml` and the committed `pixi.lock` as the authoritative project environment definition unless the project documentation specifies otherwise.
- Do not install project dependencies ad hoc with system `pip` or modify the user's global Python environment.
- Run project Python commands through the documented Pixi environment, normally `pixi run ...`.
- Do not update the entire environment or lockfile for an unrelated task.
- When a dependency change is necessary, explain why, update the manifest, regenerate the lockfile intentionally, and verify environment installation.
- Do not mix incompatible MPI implementations or binary stacks without an explicit, tested reason.
- QE may be installed or built outside Pixi if that is the documented project arrangement. Respect the repository's actual QE installation strategy; do not relocate or rebuild QE as an incidental change.
- Record the active QE executable/version and relevant MPI configuration in calculation provenance.

---

## 12. Git and Collaboration Safety

- Inspect the current branch and working tree before edits.
- Never reset, clean, force-checkout, rebase, or discard user changes unless explicitly requested.
- Do not commit, push, create branches, open pull requests, or modify remote repositories unless the user explicitly asks.
- Do not stage unrelated files.
- Avoid concurrent edits to the same files by multiple agents. Assign clear file/module ownership when parallel agents are used.
- Before integrating another agent's work, inspect its diff and run the relevant tests.
- Treat generated QE outputs, pseudopotentials, large datasets, and local machine configuration according to `.gitignore` and project documentation. Do not commit them merely because they appear in the working tree.
- If a task requires a migration or broad refactor, first identify the complete affected surface and propose a staged plan.

---

## 13. Documentation Requirements

Update documentation when a change affects:

- User-visible CLI commands or options.
- Public Python APIs.
- Structure or result schemas.
- Supported material types or CIF handling rules.
- Pseudopotential selection or validation policy.
- DFT protocols, convergence criteria, or physical assumptions.
- QE execution, MPI/OpenMP configuration, or restart behavior.
- Reproducibility and provenance.
- Installation or environment setup.

Scientific-method changes must explain **what changed, why it is scientifically justified, what assumptions apply, and how it was validated**.

Do not duplicate large specifications across multiple documents. Update the authoritative document and add concise links/references from related documentation.

---

## 14. Multi-Agent Task Delegation

When several agents work on the project:

- Give each agent a bounded task with explicit files/modules, interfaces, and acceptance tests.
- Have agents inspect the same project instructions before starting.
- Avoid assigning overlapping write ownership unless the agents are explicitly coordinating.
- Define shared data contracts before parallel implementation.
- Require each agent to report changed files, decisions, tests run, and unresolved issues.
- Review integrated changes as one system; individually passing tests do not guarantee compatible interfaces.
- Do not let agents independently invent conflicting units, schemas, naming conventions, or workflow states.

A task handoff should specify:

```text
Objective:
Scope / files owned:
Relevant documentation:
Assumptions:
Required behavior:
Acceptance criteria:
Tests to run:
Out of scope:
```

---

## 15. Required Task Completion Report

At the end of every implementation task, report concisely:

1. **Implemented:** what changed and why.
2. **Files changed:** the relevant paths.
3. **Verification:** exact commands run and observed outcomes.
4. **Scientific validation:** relevant checks, assumptions, tolerances, and reference basis.
5. **Limitations:** tests not run, unavailable dependencies/resources, and unresolved risks.
6. **Follow-up:** only necessary next steps; do not invent additional scope.

If no code was changed, say so. If implementation is blocked, state the blocker and the precise information or resource needed.

---

## 16.Scientific Correctness Requirements

Scientific correctness takes priority over implementation convenience.

1. Never equate process completion with scientific convergence.
2. Never infer physical convergence from an exit code alone.
3. Every calculation type must have explicit validation criteria.
4. Never silently change pseudopotentials, exchange-correlation
   functionals, cutoffs, k-point meshes, or physical parameters.
5. Preserve original structures and all relevant transformations.
6. Never assume a high-symmetry band path captures global band extrema.
7. Distinguish numerical convergence, methodological error,
   and experimental disagreement.
8. All reported material properties must include their computational
   method, units, and relevant provenance.
9. Never delete calculation artifacts while downstream workflows
   still depend on them.
10. Scientific tests must compare equivalent computational methods
    and clearly document reference data.

Before implementing a scientific feature:

- Identify the relevant physical equations.
- Identify the numerical method.
- Identify all required input parameters and units.
- Define physically meaningful validation criteria.
- Write tests for the expected physical invariants.

If the scientific interpretation is uncertain, stop and explain
the uncertainty instead of implementing an unsupported assumption.

## 17. Final Operating Rule

**Be conservative with code, explicit with assumptions, rigorous with physics, and honest about verification.**

A small implementation with validated scientific behavior is preferable to a large implementation whose assumptions and results cannot be trusted.
