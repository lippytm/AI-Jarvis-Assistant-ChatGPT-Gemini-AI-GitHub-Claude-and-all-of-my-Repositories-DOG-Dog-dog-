# Proposed cross-device continuity addition

Owner works from iPhone, iPad and an ASUS laptop. A session can start on one device and resume on another.

## Proposed fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `device` | string, enum `iphone`/`ipad`/`asus_laptop`/`workstation`/`unknown` | optional, default `unknown` | Device that originated the task or entry |
| `device_session_ref` | string | optional | Opaque local reference that lets a later device resume the same session without creating a parallel record |
| `resumed_from_device` | string, same enum | optional | Device that previously held the session, when this is a resume |

## Rules

1. A missing `device` is not an error; it is `unknown` and must not be inferred from user agent, region or timestamp.
2. A resume must keep the existing `task_id` and `correlation_id`. A new ID means a new task, not a resumed one.
3. Device-local drafts must not overwrite a newer revision already recorded elsewhere; the conflict stays visible.
4. The device field records where work happened, not who authorized it. Approval identity is separate and unaffected.
5. A recorded device value is not evidence that a physical device pass, accessibility review or live synchronization occurred.

## Status

Proposed. Not yet enforced by schema, validator or test in this repository.
