---
name: telephony-zadarma
description: Spanish (+34) and EU phone capabilities for Hermes via Zadarma. Place outbound bridged calls, send SMS, check balance, list owned numbers, and pull call detail records (CDR). Complements the core `telephony` skill (Twilio/Bland.ai/Vapi) when Spanish or low-cost EU numbers are required.
version: 0.1.0
author: liberathio (Thio)
license: MIT
metadata:
  hermes:
    tags: [telephony, phone, sms, voice, zadarma, spain, eu, calling, callback]
    related_skills: [telephony]
    category: productivity
---

# Telephony — Zadarma (Spain / EU)

This optional skill gives Hermes phone capabilities through **Zadarma**, a SIP/VoIP
provider with native Spanish (+34) numbers and competitive EU rates. It complements
the core `telephony` skill: use `telephony` (Twilio/Bland.ai/Vapi) when you need a
US number or AI-driven calls, and use **this skill** when you need:

- a real Spanish (+34) phone number
- low-cost outbound calls within Spain / EU
- a callback-bridged call (Zadarma calls you, then the destination, then bridges)
- SIP trunk routing for an existing PBX (e.g. FreeSWITCH/Asterisk integration)

It ships `scripts/zadarma.py`, a small CLI + Python module that wraps the
Zadarma REST API with HMAC-SHA1 signing.

## What this solves (Level 1 — bridged callback)

This v0.1 covers the practical case: **place an outbound call without an Android
companion app**. The Zadarma callback API rings your verified number first, and
once you pick up, rings the destination and bridges both legs. There is **no AI
agent on the call** — it is human-to-human, just initiated by Hermes.

A future v0.2 may add Level 2 (AI on the call) by combining Zadarma SIP + a
streaming TTS/STT pipeline. Out of scope for this skeleton.

## Capabilities

- save provider credentials into `~/.hermes/.env`
- check account balance and currency
- list numbers owned in Zadarma
- place a bridged callback call (`from` → `to`) and return the `call_id`
- query call detail records (CDR) for a date range
- send SMS from an owned number (where supported by destination country)

## Safety rules — mandatory

1. **Always confirm** before placing a call or sending an SMS. Use Hermes'
   approval flow (`tools/approval.py`).
2. **Never dial emergency numbers** (112, 091, 061, 080, etc.).
3. **No spam, harassment, impersonation, or robocalls.** Spanish and EU law
   (LSSI, RGPD, ePrivacy) is strict — comply.
4. Treat third-party phone numbers as sensitive; do not persist them to Hermes
   memory unless the user explicitly asks.
5. The user's own Zadarma number IS configuration and may be persisted.
6. Respect Spanish "Lista Robinson" if you ever expand to outbound campaigns.

## Decision tree — when to use this skill vs core `telephony`

```
Need a Spanish (+34) or low-cost EU number?
├── YES → use this skill (Zadarma)
└── NO  → use core `telephony` skill (Twilio)

Need AI to talk on the call (Bland.ai / Vapi)?
├── YES → use core `telephony` skill (Twilio + Bland/Vapi)
└── NO  → use this skill (Zadarma callback bridge)
```

## Setup

Credentials live in 1Password. The expected env vars:

| Variable | Purpose | 1Password reference (example) |
|---|---|---|
| `ZADARMA_KEY` | API user key | `op://Personal/Zadarma/key` |
| `ZADARMA_SECRET` | API secret | `op://Personal/Zadarma/secret` |
| `ZADARMA_FROM` | Default caller number (E.164, e.g. +34911234567) | `op://Personal/Zadarma/phone` |

Resolve at runtime with: `op inject -i .env.tpl -o ~/.hermes/.env`

Or persist directly: `python scripts/zadarma.py save-creds --key ... --secret ... --from +34...`

## Examples

```bash
# Sanity check
python scripts/zadarma.py balance
# → {"status":"success","balance":"12.34","currency":"EUR"}

# List your owned numbers
python scripts/zadarma.py numbers

# Place a bridged callback (Zadarma rings $ZADARMA_FROM first, then +34666777888, then bridges)
python scripts/zadarma.py callback --to +34666777888
# → {"status":"success","call_id":"abc-123"}

# Today's call records
python scripts/zadarma.py cdr --start 2026-04-16 --end 2026-04-16
```

## When invoked by Hermes

Trigger on user intents like:
- "llama a +34..."
- "llámame y conecta con ..."
- "envía un SMS al ..."
- "cuánto saldo me queda en Zadarma"

Always:
1. Confirm the destination number with the user (read it back).
2. Request approval via `tools/approval.py`.
3. Execute and return `call_id` to the user for tracking.
4. Log the action (do NOT log the destination number unless the user asks).

## Roadmap

- [ ] v0.1 — bridged callback + balance + numbers + CDR (this skeleton)
- [ ] v0.2 — SMS send + inbound SMS polling
- [ ] v0.3 — Zadarma SIP trunk registration helper
- [ ] v1.0 — AI on the call (Level 2): SIP softphone + streaming pipeline

## References

- Zadarma API docs: https://zadarma.com/en/support/api/
- Hermes core `telephony` skill: `optional-skills/productivity/telephony/`
- Hermes approval flow: `tools/approval.py`
