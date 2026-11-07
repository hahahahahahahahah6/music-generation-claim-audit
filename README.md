# Documentation claim auditor

An offline, deterministic, standard-library-only Python CLI for checking whether
repository prose agrees with static evidence of song composing. Requires Python
3.9 or newer. No LLM, network, telemetry, or filesystem writes during audits.

## Install and run

```sh
python3 -m pip install .
music-generation-claim-audit audit .
python3 -m music_generation_claim_audit audit . --json
music-generation-claim-audit --version
music-generation-claim-audit --help
```

The repository defaults to the current directory. Repeat `--ignore PREFIX` to
skip relative paths starting with a prefix. `--verbose` reports scope and file
decisions on stderr. JSON output is an array; each finding includes verdict,
message, severity, rule, path, and matched phrase. An empty array means PASS.

Exit status is 0 when no finding reaches the selected threshold, 2 when a finding
reaches it, and 1 for usage or IO errors. The default threshold is HIGH; choose
`--fail-on medium` to also fail on MEDIUM findings. A default successful exit can
therefore include MEDIUM findings.

## Scope and findings

Root README.md and Markdown beneath docs/ supply documentation prose. Triple
backtick fenced blocks are excluded; inline code counts. Python sources throughout
the repository supply module-local AST evidence. Git metadata, bytecode caches,
and virtual environments are excluded. Files under tests/ supply fixture-only
claims at MEDIUM severity when no shipped documentation claim and no evidence
exist. Unsupported syntax or unreadable scanned files produces an IO error.

An affirmative claim without evidence is HIGH. A denial contradicted by evidence
is HIGH. A denial without evidence passes, including a repository without source.
No claims also passes. Findings use these identifiers:

```text
documented-music-generation-claim-false
documented-no-music-generation-claim-false
```

Evidence requires construction and use in the same module for a supported
pipeline, dedicated class, package model, or client. Imports and aliases are
resolved, including assigned and chained forms. Local definitions shadow route
names throughout that module. Feature-named calls also count directly. Mere
imports, strings, comments, references, subprocess commands, and construction
without instance use do not count. Cross-module pairs do not count.

## Differentiation

The following neighbours have distinct boundaries, in order:

```text
audio-generation-claim-audit
text-to-speech-claim-audit
music-transcription-claim-audit
chord-detection-claim-audit
genre-classification-claim-audit
instrument-recognition-claim-audit
mood-recognition-claim-audit
speech-recognition-claim-audit
```

They check, respectively: synthesising any audio; synthesising speech; turning
audio into notes; naming chords; labelling a genre; naming instruments; labelling
a mood; and transcribing spoken audio. This auditor checks composing songs rather
than those adjacent capabilities. Playing, tagging, fingerprinting, separating
stems, and suppressing noise do not establish the checked capability.

## Limitations

This is static pattern matching, not semantic judgement or a runtime quality test.
Matching uses exact case-insensitive substrings, not restatement, stemming, fuzzy
matching, or hyphen normalisation. Denial spans are removed first. Longest-first
matching blanks each matched span, so each occurrence counts once under its
longest phrase.

A text-to-audio pipeline whose literal model string contains “music”, paired with
an instance call, counts as evidence; this alone does not prove the produced audio
is a good song. A construction from the following package paired with instance
use also counts, although it does not prove the resulting audio is music:

```text
audiocraft
```

A generic call on an unrelated object counts because the method name is shared:

```python
unrelated.generate_music()
```

Generic sound synthesis with no “music” in the pipeline model string is excluded:
synthesising generic sound is not composing songs. Dedicated models and package
routes follow fixed patterns; dynamic factories, runtime imports, reassignment,
control flow, and cross-module data flow are not evaluated. Findings may therefore
include false positives or miss real implementations.

Exact substrings can refer to a human composer, listening to machine-made songs,
or a playlist feature. These examples deliberately match despite that ambiguity:

```text
Beethoven was a famous music composer
I listen to ai music while working
our song generation picks the next track for you
```

## Development

```sh
python3 -m unittest discover
python3 -m pip install build
python3 -m build
```

The source archive includes the test suite. MIT licensed.
