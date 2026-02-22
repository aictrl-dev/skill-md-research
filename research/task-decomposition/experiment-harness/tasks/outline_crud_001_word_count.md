# Task Spec: Add word_count to Documents

## Description

Add a `word_count` field to the Document model that:
1. Is automatically calculated when document content changes
2. Is stored in the database for querying/sorting
3. Is returned in the Document API response
4. Can be used for filtering documents by length

## Files to Modify

- `server/models/Document.ts` - Add word_count column
- `server/presenters/document.ts` - Include word_count in response
- `server/routes/api/documents/documents.ts` - API handlers
- `server/migrations/` - Database migration
