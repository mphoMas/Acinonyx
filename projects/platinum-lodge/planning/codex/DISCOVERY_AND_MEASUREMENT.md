# Launch intake and workflow measurement

## Confirmed and unresolved

Confirmed by owner on 9 October 2026: Mozambique launch, existing Excel workflows, no established daily flow measurement. Release one supports multiple properties, reservations/check-in, billing/payments and housekeeping. Production backend is required; this preview is not the release.

Still needed: second real property and property list; room inventory; legal entity per property; tax/fiscal invoice requirements verified locally; MZN handling/rounding; business-day cutover; payment providers and merchant ownership; connectivity/device profile; Excel files and authoritative fields; migration cutover/rollback; shared guest privacy policy; role memberships; support hours and operational sign-off. Do not request customer Excel sheets in public Git or commit personal data. Use redacted column samples for mapping, and controlled storage for migration inputs.

D1 acceptance needs owner-approved launch boundaries. A country decision alone does not close D1. Mozambique legal/payment requirements require qualified local verification, not assumptions from the prototype.

## Baseline from Excel (D2)

Select one reception, finance and housekeeping representative plus an operations supervisor. Observe routine and exception tasks over five representative operating days, including a busy arrival/departure period. Start with a paper or spreadsheet log: this does not require an existing analytics system. Obtain staff consent and collect process facts, not performance rankings.

Measure reservation creation/modification; arrival verification and room allocation; check-in; checkout/bill correction; payment matching; housekeeping assignment/status/inspection; manager exception triage. Record start/end, interruptions, handoffs, corrections and whether successfully completed. Use anonymous staff codes and synthetic guest references. Never record card details, guest names, IDs or payment credentials. Separate elapsed time from active task time. Mark incomplete observations and reasons; exclude neither difficult tasks nor exceptions silently.

The adjacent observations.csv is intentionally empty. The observer writes one row per measured attempt. End-to-end timers start at the task trigger and end at confirmed completion; record interruptions separately. Times use explicit offset +02:00. Compare the same task class, complexity and property across Excel and the integrated candidate, with staff familiarization first. Capture at least 20 matched routine attempts per primary workflow before interpreting medians; report sample size, failures and distribution, and treat small samples as exploratory. Repeat under realistic connectivity and shift handovers.

## Productivity evaluation (M3)

Report median and p90 active/elapsed times, successful completion rate, correction rate and handoff count by task/property. Interview staff about uncertainty and cognitive load. Targets from the project plan (30% median improvement, 95% task success, SUS 80) are proposals, not measured results. Do not use a faster result that increases financial errors, access leakage or double bookings. Investigate outliers and bottlenecks, refine the UI, and repeat the matched tasks. Keep baseline/raw measurements access-controlled; publish only anonymous aggregates with methodology. Owner/operations sign-off is needed before treating the measurement as acceptance evidence.
