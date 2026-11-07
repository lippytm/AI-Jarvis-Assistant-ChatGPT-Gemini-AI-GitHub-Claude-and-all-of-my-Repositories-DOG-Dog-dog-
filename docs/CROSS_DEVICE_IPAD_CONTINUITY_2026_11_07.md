# iPad and cross-device continuity boundary

The owner works from iPhone, iPad and an ASUS laptop. This record states what that means for this repository and what remains unverified.

## What is already specified elsewhere

- `docs/HOSTINGER_PARALLEL_PLATFORM.md` requires responsive layouts and cloud-backed state so one account can continue on iPhone, iPad or laptop, and lists mobile-first navigation as an acceptance check.
- `lippytm/Prompt-11-` carries `P-011-OMNI-001`, a cross-device and multi-AI continuity contract with three pilots (`OMNI-PILOT-001` mobile capture to certified learning object, `OMNI-PILOT-002` cross-device code lab, `OMNI-PILOT-003` business experiment passport). Its continuation packets record physical iPhone, iPad and ASUS review as **incomplete**, and an `AccessibilityGate` that is conditional pending physical device review.
- `lippytm/Evolutionary-Evolutions-Creative-Creations-Studios-of-Intergalactic-Corporate-Services-LLC.` carries a cross-device Linux RPG control plane with iPhone and iPad as first-class control terminals.

## What this adds

An iPad session is a first-class work session, not a lesser one. That has three consequences for this Control Tower.

### 1. Session capture must be device-labelled

A task, workflow run or continuation packet should record the device it originated from (`iphone`, `ipad`, `asus_laptop`, `workstation`, `unknown`) alongside the platform and provider route. Handoff records already separate `device_or_platform`; this makes the device a first-class field rather than prose.

### 2. Resume, do not fork

iPad capture is often partial: a thought, a link, an approval, a correction. The continuity rule is that an iPad entry returns to the same task, correlation ID and evidence record it belongs to. A second device must never create a parallel canonical record for the same work, and a device-local draft must not silently overwrite a newer revision made elsewhere.

### 3. Approvals are device-neutral but review is not

Approval of a financial, publishing, credential, deletion or production-deployment action is valid from any device, because it is the owner acting. What is not device-neutral is visual and interaction review: layout, touch navigation, readability, keyboard and focus behaviour, and accessibility on iPad remain **pending physical review** until someone records findings from an actual iPad. Authoring page logic and HTML structure is not the same as a physical device pass, and this repository must not report a device pass it has not performed.

## Unverified boundaries

- No live synchronization among iPhone, iPad, ASUS laptop and this Control Tower exists in this repository.
- No iPad review findings have been recorded here.
- Cloud-backed shared state is specified for the Hostinger-facing platform, not implemented as a Jarvis Control Tower service.
- Device labelling is proposed here, not yet enforced by a schema or test.
- Recording a device name in a record is not evidence that the session occurred, nor proof of the account or identity used on that device.

## Next concrete steps

1. Add the optional `device` field to the task envelope and continuation-packet schema, defaulting to `unknown`.
2. Run one real cross-device resume test: start a task on iPad, resume it on the ASUS laptop, and record whether context, evidence labels and revision state survived.
3. Record actual iPad review findings for the composer, workbench, diary, RPG companion and research questbook pages, including defects, before claiming any accessibility or mobile pass.
4. Keep private session content out of the public repository; only sanitized, evidence-labelled device findings belong here.
