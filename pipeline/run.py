"""Rebuild everything: python -m pipeline.run [years...]

1. fetch any missing seasons from Baseball Savant
2. physics features for every pitch
3. Stuff+ model (leave-one-season-out) + SHAP
4. compact tables for the app
"""
import sys

from pipeline import aggregate, features, fetch, model

if __name__ == "__main__":
    years = [int(y) for y in sys.argv[1:]] or [2024, 2025, 2026]
    fetch.main(years)
    features.main()
    model.main()
    aggregate.main()
