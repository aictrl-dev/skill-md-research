# First-batch browser review — 21 October 2026

Local built website served at `http://127.0.0.5:3005` through a task-owned preview server. Other services on `127.0.0.1:3005` and `127.0.0.3:3005` were left running. Preview-only CSP sets `connect-src 'none'; script-src 'self' 'unsafe-inline'`, blocking PostHog ingestion and its remote SDK. No product account, form submission, grant, repository connection or task execution was created.

Chrome Work profile, using the CUA integration:

- Opened `/blog/swe-evo-analysis`; the rendered title, author/date, H1 and content match the refreshed source. Desktop screenshot shows legible hero/body and no overlap with navigation.
- Scrolled through the published-results area and evaluation section; the selected data table, versioned source links and explicit limits render.
- Applied the browser viewport capability at 390 × 844 for responsive review. Rendered DOM reported a 375 px content viewport and a 375 px document width: no horizontal page overflow. The results region fits within 311 px. Header and model identifier wrap inside the table; all result columns remain visible.
- Captured mobile hero and results screenshots through CUA. Navigation collapses to its existing mobile toggle; title and body wrap within the page. The existing cookie notice overlays the bottom viewport until acknowledged; it is not treated as analytics consent or changed by this batch.
- Restored the normal viewport, then opened `/signup`. The email action is an accessible link labelled “Continue with email in aictrl,” targeting `https://app.aictrl.dev/`, followed by “Enter your email on the next screen to request a magic link.” No email input or POST form remains on the static signup page.

Screenshots were inspected in the tool output; no standalone screenshot artifact is claimed. This is local rendered verification, not proof of production headers, actual email delivery, successful signup, approved analytics capture or executor lifecycle. The existing source-confirmed app email flow is covered in the QA report. Google report navigation remains intermittent even though local preview navigation is responsive; its pending account checks remain open.
