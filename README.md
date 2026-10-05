# Crop Health AI — Website deployment

FastAPI backend and administrator website for the offline-first crop disease research project.

This repository contains the website deployment package. The full Flutter application, ML experiments and datasets remain in the separate local project at D:\Crop disease detection.

- index.py: Vercel FastAPI entry point
- backend/app: authentication, optional sync and administration
- backend/alembic: schema migrations
- admin: website source
- requirements.txt: pinned dependencies

Required private environment variables: DATABASE_URL, JWT_SECRET (at least 32 characters).
Apply Alembic migrations once and seed the research catalog before using authenticated workflows. The backend does not run crop inference. No trained model, dataset, local credentials or offline phone images are included.

Current status: deployment setup is in progress; successful builds alone do not establish working database access or farmer-ready model accuracy.

Connected to Gnanambhika's Vercel project. Hosted schema initialization and public runtime verification are pending.
