# AI Jarvis workforce production pilot

**AI Jarvis and the Empowered Human Workforce — Chapter 6 companion**

The Evolutionary Evolutions Creative Creations Studios of Intergalactic Corporate Services LLC.

This checked-in teaching example gives the studio a substantive first project for the local production planner: an original chapter, an abridged narration, a short-video script, and a video-book storyboard. The examples are deliberately public, synthetic, and free of private business records. They exercise the software contract and provide a candidate lesson for later editorial and reader review.

## What exists

| File | Purpose and current state |
|---|---|
| [production-brief.json](production-brief.json) | Filled assignment, exact source hashes, and direct parent relationships |
| [assets/chapter-06.md](assets/chapter-06.md) | Original chapter on delegation, acceptance criteria, source changes, and recovery |
| [assets/narration.md](assets/narration.md) | Eight-section abridged spoken adaptation; text only |
| [assets/video-script.md](assets/video-script.md) | Short educational script and six planned scenes; text only |
| [assets/video-book-storyboard.md](assets/video-book-storyboard.md) | Eight-scene chapter adaptation tied to both manuscript and narration |
| [distribution-drafts.md](distribution-drafts.md) | Candidate educational copy for the six intended destinations; not sent |
| [economics.json](economics.json) | Four explicitly hypothetical demand scenarios using the same cost assumptions |
| [pilot-experiment.md](pilot-experiment.md) | Reader-trial design, observations, production sequence, and stop/revise decisions |

The book title and Chapter 6 subject continue the prior Book One plan. The existing October 9, 2026 development installment was a separate manuscript edition. This new companion does not replace it or claim to finish the 350+ page book target. Actual page counts depend on later editing and typesetting.

Project owner: Charles Earl Lipshay / lippytm.AI. Draft preparation: original AI-assisted work in this development session, with no copied private manuscript passages, customer records, or third-party media. The fictional workplace is a teaching device. Source, rights, editorial, accessibility, and reader checks for a finished edition remain separate work; the supplied text does not claim authenticated authorship or completed rights clearance.

## Build a real local project packet

From the repository root, with Python 3.11 or newer:

```sh
PYTHONPATH=src python3 -m jarvis studio-plan \
  examples/studio-workforce-pilot/production-brief.json \
  --output /tmp/jarvis-workforce-pilot --json
PYTHONPATH=src python3 -m jarvis verify-studio-plan \
  /tmp/jarvis-workforce-pilot --json
PYTHONPATH=src python3 -m jarvis studio-economics \
  examples/studio-workforce-pilot/economics.json --json
```

Use a fresh output directory each time. Existing output directories are refused. These commands operate before Control Tower initialization and need no provider key. They do not initialize a task ledger, send handoffs, render media, approve a release, or publish to an account.

The production packet contains actual copies of the four supplied text assets, the exact brief/config/profile snapshots, a derived production plan, and three local workspace handoff briefs. Keep its returned manifest hash with the source revision or review record. Standalone verification checks that packet's internal consistency; it does not re-open the original working directory to prove the sources remain current.

An asset can be prepared for review while the overall release remains blocked. This distinction is intentional: the planner has evidence about source consistency, not a recording, audience study, account connection, or authenticated human decision. The older `creative_studio_package` catalog workflow continues to produce fixed intake templates. This new command consumes a filled brief and real local source drafts; the catalog still contains eight workflows.

## How the adaptations stay traceable

The chapter is the canonical source for the narration and short video. The storyboard uses both the chapter and the narration. Each child records the precise hash of every declared direct parent. A source mismatch, stale parent reference, missing asset, or applicable request for changes prevents affected work from being treated as prepared for review.

After editing a source, inspect the dependent text before updating parent references. Recalculating a hash cannot determine whether the adaptation is still accurate. Keep the old packet and create a new output directory for the revised brief. The walkthrough and state definitions are in [the production contract](../../docs/STUDIO_PRODUCTION.md).

The included `reviews` array is empty. No human review is invented. A future review record is only a supplied assertion tied to an asset hash; it cannot grant publishing authority. A separate reviewer should inspect the actual sources and record the scope of any decision outside this local tool's unauthenticated inputs.

## Business experiment, not an active offer

The illustrative economics model considers a future edited digital edition at $9, with $60 fixed cash cost, four hours valued at $20/hour, $0.50 per-unit delivery cost, and a 5% variable-fee assumption. These values were chosen for a teaching calculation. They are not current provider fees, owner-approved spending, observed sales, or a price published on a sales page.

The supplied scenarios assume 0, 10, 25, and 50 units. The model separately reports cash results and results after valuing production labor. It excludes any costs not entered, including taxes, refunds, acquisition costs, a separate fixed transaction charge, and ongoing support. See [the economics contract](../../docs/STUDIO_ECONOMICS.md) and [the pilot experiment](pilot-experiment.md) for interpretation and the observations still needed.

## Evidence and next production unit

The dedicated Studio production check runs the filled public example, verifies its packet, evaluates the scenarios, and uploads their bounded outputs as a GitHub Actions artifact. Unit tests also exercise changed sources, lineage errors, packet tampering, and CLI isolation. Those checks establish software behavior for the checked source revision, not educational effectiveness or finished media quality.

The next editorial unit is a review of the chapter and its adaptations against the reader outcome. A small opt-in reader trial can then test whether the explanation works. Actual audio/video production and Hostinger or social publishing need the relevant account, source, media, and release evidence. No existing customer or platform account is modified by this example.
