.PHONY: setup run pipeline test cache
setup:
	python -m pip install -r requirements-dev.txt
run:
	python -m streamlit run app/streamlit_app.py
pipeline:
	python scripts/run_pipeline.py
test:
	python -m pytest
cache:
	python scripts/build_llm_cache.py
