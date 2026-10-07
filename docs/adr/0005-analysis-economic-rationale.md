# Preserve economic rationale with Analysis definitions

Implemented 7 October 2026.

An Analysis carries optional Economic Rationale alongside its calculation and
settings. Capturing it in the resolved definition lets evaluations and Snapshots
retain the reasoning applicable at that time; keeping it only in agent conversation
or Idea notes would separate the research question from independently screened
Analyses. This extends the evidence-preservation decision in
[ADR 0004](0004-portable-idea-evidence.md).

Use one human-readable field initially: the investment question, reasoning and
qualifications belong together. Revised rationale follows existing definition
revision rules. Earlier evidence, including Latest calculations using a captured
definition, keeps its earlier rationale. Missing historical rationale remains
missing; it is never reconstructed from today's Library entry.

Rationale supplies context for interpretation. Calculations, monitoring rules and
freshness eligibility retain their existing meanings. Agents assess the hypothesis
against supporting and challenging evidence; the text is research content, not
instructions controlling agent behaviour.
