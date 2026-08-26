# Governance

EdgeLoom is developed in public. This document explains who makes decisions,
how responsibility is earned, and where the record of a decision lives. The
goal is a process that remains usable while the project is small and can widen
without being redesigned as the community grows.

## Principles

- **Technical evidence over authority.** Decisions should cite tests, device
  reports, security analysis, or documented user needs when those are
  available.
- **Public by default.** Design and governance decisions happen in GitHub
  issues, discussions, and pull requests. Vulnerabilities and conduct reports
  are the necessary exceptions.
- **Compatibility and safety are explicit.** A change that affects generated
  drivers, schemas, credentials, or filesystem writes must describe the impact
  and its validation.
- **Credit follows work.** Authors, reviewers, reporters, and maintainers are
  credited for the work they perform.
- **Roles are earned and revisable.** Access is based on sustained project work,
  not institutional affiliation.

## Roles

### Participants and contributors

Anyone who uses EdgeLoom, opens a discussion, files a device or bug report,
improves documentation, reviews a change, or submits code is a participant or
contributor. No prior permission is required. All participation is governed by
the [Code of Conduct](CODE_OF_CONDUCT.md).

### Reviewers

Reviewers are contributors with demonstrated knowledge of part of the project.
They may triage issues and provide trusted technical reviews, but they do not
merge changes or publish releases unless they are also maintainers.

### Maintainers

Maintainers have repository write access and are responsible for:

- reviewing and merging pull requests;
- keeping CI, releases, documentation, and dependency updates healthy;
- applying the security and conduct processes;
- recording significant decisions and disclosing conflicts of interest; and
- helping contributors reach a clear outcome, including explaining a decline.

The lead maintainer coordinates releases and resolves a decision only after the
normal process has failed to reach consensus. The security steward coordinates
private vulnerability reports. One person may hold more than one role while the
project is small. Current assignments are listed in
[MAINTAINERS.md](MAINTAINERS.md).

## How Decisions Are Made

### Routine changes

Bug fixes, tests, documentation, and bounded enhancements are decided in their
pull requests. CI must pass. The reviewing maintainer may merge when the change
is understood, tested in proportion to its risk, and consistent with the
project scope.

### Substantial changes

A change is substantial when it alters a public CLI or schema, removes
compatibility, changes a trust boundary, adds a platform or major dependency,
or changes governance. Start these changes in a GitHub discussion or issue
before implementation. The proposal should state:

1. the user or ecosystem problem;
2. the proposed change and alternatives;
3. compatibility and migration effects;
4. security and privacy effects; and
5. how the result will be tested.

Substantial proposals normally remain open for comment for at least seven days.
Maintainers seek consensus rather than votes. If material disagreement remains,
the lead maintainer records the decision and rationale in the public thread.

### Security and urgent maintenance

Vulnerabilities follow [SECURITY.md](SECURITY.md) and may be developed privately
until coordinated disclosure. A maintainer may merge an urgent release or CI
repair without the normal discussion window, but must document the reason after
the immediate risk has passed.

## Reviews and Merges

- Authors do not approve their own pull requests.
- A non-trivial change should receive review from a maintainer or designated
  reviewer who did not author it.
- When only one maintainer is available, that maintainer may merge after CI
  passes and the PR has remained public long enough for practical review. The
  exception and rationale should be visible in the PR.
- Generated artifacts, schemas, release configuration, security-sensitive code,
  and GitHub workflows receive explicit maintainer review.
- Merge commits, squash merges, and rebases are selected to preserve useful
  authorship and history; the PR remains the decision record.

## Becoming a Reviewer or Maintainer

A contributor may nominate themselves or another contributor in a public
governance issue. Maintainers consider the quality and consistency of work,
review judgment, communication, knowledge of project boundaries, and adherence
to the Code of Conduct. Contributions may be code, documentation, device
reports, security work, issue triage, or reviews.

Reviewer appointments are recorded in [MAINTAINERS.md](MAINTAINERS.md).
Maintainer nominations remain open for at least seven days and require consensus
of the active maintainers. The decision and its evidence are recorded in the
nomination issue. New maintainers receive the least privilege needed for their
role and expand access as responsibility grows.

## Inactivity, Resignation, and Removal

A reviewer or maintainer may step down at any time. After six months without
project activity, the other maintainers will check in before moving the person
to emeritus status and removing unnecessary access. Returning contributors may
be reappointed through the same public process.

Access may be suspended immediately to protect users, embargoed reports, or the
community. Permanent removal requires a documented maintainer decision, with as
much of the rationale public as privacy, safety, and legal obligations permit.

## Conflicts of Interest

Reviewers and maintainers disclose relationships that could reasonably affect a
decision and recuse themselves when they cannot provide an independent review.
Institutional affiliation, funding, or authorship does not by itself determine
project authority.

## Changing This Document

Governance changes use the substantial-change process above. The accepted pull
request is the authoritative record.
