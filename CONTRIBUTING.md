# Contributing

Use Python 3.13 and install `requirements-dev.txt`. Run `python -m pytest -q` before submitting changes. The automated tests run without credentials or live Gemini requests.

Keep computation separate from display formatting. Do not edit result tables to make a chart look better. New evaluation policies should write separate outputs and document their selection rule and limitations. Preserve the original result and Story/Limitations hashes unless a reviewed scientific change explicitly requires updating them.

Never commit `.env`, `.streamlit/secrets.toml`, raw exports under `data/`, or API keys. Use synthetic summaries in tests, and mock provider requests. Label a fixed-policy fallback clearly; never call it a model response. Retention proposals must pass independent validation and must never change real collection.

For a bug report, include the page, steps, expected result, and sanitized error category. Remove keys and personal data from screenshots and logs.
