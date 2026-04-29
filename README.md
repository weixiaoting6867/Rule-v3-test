# Relation Extraction Sample from READMEs

This repository provides a relation extraction sample based on README files from open-source GitHub repositories. Five representative READMEs are included as worked examples; the same extraction pipeline is designed to scale to 500 or more READMEs.

## Overview

Relation extraction is the NLP task of identifying semantic relationships between entities in text. This project applies rule-based and pattern-based extraction to README files, identifying relations such as:

- **depends_on** – software dependency relationships (e.g., "Library A requires Package B")
- **supports** – compatibility statements (e.g., "Tool A supports Python 3.8+")
- **built_with** – technology stack declarations (e.g., "Project X is built with Framework Y")
- **provides** – feature descriptions (e.g., "Service A provides REST API B")
- **integrates_with** – integration relationships (e.g., "Plugin A integrates with Platform B")

## Repository Structure

```
.
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── src/
│   └── extract_relations.py    # Relation extraction script
└── data/
    ├── sample_readmes/          # Sample input README files (5 examples)
    │   ├── readme_001.md
    │   ├── readme_002.md
    │   ├── readme_003.md
    │   ├── readme_004.md
    │   └── readme_005.md
    └── sample_relations.json   # Extracted relations (5 samples demonstrating dataset format)
```

## Dataset

`data/sample_relations.json` contains extracted relations from 5 representative README files, demonstrating the format used when processing the full 500-README dataset. Each record includes:

| Field | Description |
|---|---|
| `readme_id` | Unique identifier for the README (1–5 in this sample) |
| `repo` | Source GitHub repository (`owner/repo`) |
| `relations` | List of extracted subject–predicate–object triples |

Each relation triple contains:
- `subject` – the source entity
- `predicate` – the relation type
- `object` – the target entity
- `sentence` – the source sentence from the README
- `confidence` – extraction confidence score (0.0–1.0)

## Usage

### Requirements

```bash
pip install -r requirements.txt
```

### Extract relations from a README file

```bash
python src/extract_relations.py --input path/to/README.md
```

### Extract relations from a directory of READMEs

```bash
python src/extract_relations.py --input-dir data/sample_readmes/ --output data/my_relations.json
```

## Example

Input (excerpt from `data/sample_readmes/readme_001.md`):

```markdown
## Flask

Flask is a lightweight WSGI web application framework. It depends on Werkzeug
and Jinja2. Flask supports Python 3.8 and newer.
```

Output:

```json
{
  "readme_id": 1,
  "repo": "pallets/flask",
  "relations": [
    {
      "subject": "Flask",
      "predicate": "depends_on",
      "object": "Werkzeug",
      "sentence": "It depends on Werkzeug and Jinja2.",
      "confidence": 0.80
    },
    {
      "subject": "Flask",
      "predicate": "depends_on",
      "object": "Jinja2",
      "sentence": "It depends on Werkzeug and Jinja2.",
      "confidence": 0.80
    },
    {
      "subject": "Flask",
      "predicate": "supports",
      "object": "Python 3.8",
      "sentence": "Flask supports Python 3.8 and newer.",
      "confidence": 0.95
    }
  ]
}
```

## License

This dataset and code are released for research and educational purposes.
