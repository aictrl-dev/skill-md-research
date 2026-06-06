Use your code-review skill to review the following source file(s) for real defects.

Follow the explore-context protocol: before recording any finding, verify it with `query_context` (start with `callers` on the suspect function and `impact` on the file) so you keep only defects that actually matter. HARD LIMIT: at most 8 `query_context` calls total for this review — once you hit 8, stop querying and output what you have.

Output findings as a JSON array.
