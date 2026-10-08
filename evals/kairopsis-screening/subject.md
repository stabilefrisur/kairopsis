# Evaluation task boundaries

Complete only the realistic user request in your dispatch message. Use the frozen
kairopsis-screening skill. Before interpreting an Analysis, read the frozen
kairopsis-analysis entry point; follow its references when relevant.

You may read this file, your case directory, and the two frozen skill folders
under this evaluation root's skills/. Other cases, private/, scoring rubrics,
the fixture generator, application source and previous results are outside scope.
Do not inspect peer work, delegate or browse the internet.

Only case 01-retry may access the supplied loopback HTTP service. In that case,
read run status/evidence and save/read the brief through its API; do not inspect
the local app-workspace backing files to bypass the API lifecycle. All other
cases use local retained files only and make no network requests.

You may save new briefs beneath the selected run's briefs/ directory (through
the API for 01-retry). All other working files/scripts belong under your own
case's output/ directory. Keep retained evidence and frozen skills unchanged.
Do not change configuration or monitoring, send reports elsewhere, or access
real user research/providers. The supplied fixtures are synthetic.

If automatic execution review denies an action, report the exact denial and stop
that action. Do not switch commands/transports to bypass it. Ordinary network
failures may be recovered under the skill's request-identity rules.

After completing the user request, save output/audit.json with resources read,
reviewed Analysis IDs, inspected evaluation and baseline IDs, operations,
saved report location, readback status and any blockers. This is an execution
audit, not the investor brief. State unverified steps honestly. Return a concise
user-facing result and artifact path in your final response.
