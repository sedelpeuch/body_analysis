# python_body-analysis

Script for body measurement analysis and following

Additional line of information text about what the project does.

## Prerequisites

Before you begin, ensure you have met the following requirements:

## Installing python_body-analysis

To install python_body-analysis, follow these steps:

```bash
poetry install
```

## Using python_body-analysis

To use python_body-analysis, follow these steps:

```bash
# CLI demo
poetry run body_analysis

# Streamlit application
poetry run streamlit run body_analysis/dashboard.py
```

### Pages
- Main dashboard: charts of weight/composition and daily calories with phase markers
- Phases: select a phase to view a detailed timeline and KPIs
- Photos: compare monthly photos with optional blur mode

### Data layout
- `data/com.samsung.health.weight*.csv` — Samsung Health export for body composition
- `data/com.samsung.health.food_intake*.csv` — Samsung Health export for food intake
- `data/phases.json` — Phase configuration, example provided
- `data/photos/YYYY-MM/*.jpg|png` — Monthly photo sets

## License

This project is licensed under Apache 2.0, a permissive open source license that
allows you to freely use, modify, distribute, and sell your own
products that include this software. The full text of the license can be
obtained from the [Apache website](https://www.apache.org/licenses/LICENSE-2.0).
