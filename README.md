# Urdu Sentence Segmentation Lab

A Streamlit dashboard for training and comparing sentence-segmentation baselines on Urdu tweets, then testing them on uploaded `.txt` files.

## What it does

- Trains a dataset-based Punkt model on cleaned Urdu tweets.
- Accepts a `.txt` file or pasted text for testing.
- Runs these algorithms on the uploaded test text:
  - Rule-Based
  - Regex
  - UrduHack
  - Stanza
  - Dataset-Trained Punkt
  - Groq LLM
  - Hybrid
- Shows a comparison table with the result, verdict, and reason for each algorithm.

## Run the app

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Environment

Create a `.env` file in the project root so you do not have to type the key every time:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

## Notes

- The `Dataset-Trained Punkt` model is trained from 50 cleaned Urdu tweets at startup.
- The dashboard uses punctuation-based reference splitting to judge whether each algorithm worked well on the uploaded test text.
- If `Stanza` or `UrduHack` is not available in your local environment, the app will still load and mark that algorithm as unavailable.
- `UrduHack` depends on `TensorFlow`, so the initial install can take a little longer than the UI-only packages.
- The first time `Stanza` runs, it downloads the Urdu tokenizer model automatically.
