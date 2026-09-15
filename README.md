# Invoice Intelligence — Paperclip + GitHub Models

Multi-document invoice/packing-list extraction MVP.

- Upload multiple PDF/JPG/PNG files.
- User describes the required fields in natural language.
- AI extracts requested data and can take net weight from packing lists.
- Cross-document reconciliation.
- JSON export.
- Docker + Render deployment files.
- Paperclip agent roles/workflow included.

Run locally:
`pip install -r requirements.txt`
`uvicorn app.main:app --reload`

Set `GITHUB_TOKEN` in `.env`.
