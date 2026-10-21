# Deployment

**Live app:** https://cyberflight-mvp1.streamlit.app/

Deployed from `main` with Python 3.13. All six pages rendered in hosted browser checks, demo-mode unsupported Q&A was refused, and a live Gemini triage request succeeded. The owner-approved key and model are held in encrypted hosting secrets; no key is committed. See `VALIDATION.json` for remaining untested items.

## Streamlit Community Cloud

After this project is pushed to GitHub, sign in at https://share.streamlit.io/ and create an app with these settings:

| Setting | Value |
|---|---|
| Repository | `Shivani-exe/cyberflight-mvp1` |
| Branch | `main` |
| Entrypoint | `app/streamlit_app.py` |
| Python | `3.13` |

The repository includes `app_data/` and `results/`; the hosted app does not need `data/` or a pipeline run. Runtime packages are pinned in `requirements.txt`. Python is selected in Advanced settings, not inferred from the Dockerfile.

For a public demonstration, launch with no secrets: cached/fixed mode works without a provider key. For live Gemini, the account owner can set `GEMINI_API_KEY` and optionally `GEMINI_MODEL` in the host's secrets settings using `.streamlit/secrets.toml.example` as the format. Do not paste `.env` directly into TOML settings. Turn off Demo mode to make a live request. A host-side key can incur provider usage from app visitors; keep it out of Git and choose access and quota settings appropriate for your audience.

Deployment is complete only after the hosted URL loads all six pages and a no-key fallback works. A local test pass does not confirm hosting success. Live planner generation was verified locally and on the hosted app; full batch LLM evaluation and live grounded Q&A remain untested.

Official guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Docker

```sh
docker build -t cyberflight .
docker run --rm -p 8501:8501 cyberflight
```

The image runs as an unprivileged user and excludes local secrets and raw exports. To use live Gemini with a private local container, pass an environment file at runtime:

```sh
docker run --rm -p 8501:8501 --env-file .env cyberflight
```

The Dockerfile is provided as a deployment option; a Docker image build has not been tested in the delivery environment.
