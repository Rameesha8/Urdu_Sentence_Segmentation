# Urdu Sentence Segmentation on Twitter Data

## Project Overview
This project focuses on applying multiple sentence segmentation algorithms to **Urdu tweets** and analyzing their performance and limitations. The goal is to evaluate how different methods handle noisy social media text and suggest improvements for better segmentation.

---

## Dataset
- **Source:** Large-scale Urdu Tweet Dataset (Batra et al., 2021)  
- **Format:** Excel file (`urdu_tweets.xlsx`)  
- **Columns used:** `Text`  
- **Preprocessing:**  
  - Removed URLs, mentions, hashtags, retweets (`RT`)  
  - Removed punctuation and extra spaces  
  - Saved cleaned tweets to `data/processed/urdu_tweets_cleaned.csv`

---

## Sentence Segmentation Algorithms
1. **Rule-Based** – Splits sentences using Urdu punctuation (`۔`, `?`, `!`).  
2. **UrduHack** – Urdu NLP toolkit sentence tokenizer.  
3. **Stanza** – ML-based tokenization with Urdu model (fastest with small datasets).  
4. **Regex-Based** – Advanced splitting with patterns for multiple punctuation marks.  
5. **Hybrid** – Combines Rule-Based and UrduHack for improved accuracy.

---

## Features
- Applies **all five algorithms** on the dataset.  
- Randomly samples **50 tweets** for comparison.  
- Generates **average sentence count plots** and saves them to `results/`.  
- Produces **limitations and improvements report** per algorithm and saves it as CSV.  
- Displays **side-by-side colored example splits** for selected tweets.

---

## Folder Structure

Urdu_Sentence_Segmentation/
├── data/
│ ├── raw/urdu_tweets.xlsx
│ └── processed/urdu_tweets_cleaned.csv
├── results/
│ ├── segmentation_comparison_plot.png
│ └── segmentation_limitations_report.csv
├── notebooks/
│ └── Urdu_Sentence_Segmentation.ipynb
├── .gitignore
├── requirements.txt
└── README.md


---

## How to Run
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

2. **Run notebook:**
   Open notebooks/Urdu_Sentence_Segmentation.ipynb in Jupyter Notebook or VSCode.
**Outputs:**
   Cleaned dataset → data/processed/urdu_tweets_cleaned.csv
   Comparison plots → results/segmentation_comparison_plot.png


## Requirements
1. Python 3.9+
2. pandas, numpy, re, string
3. urduhack
4. stanza
5. matplotlib, seaborn

**Install all packages using:**

pip install -r requirements.txt
## Notes
1. Stanza-based segmentation may be slow on large datasets; sampling is recommended.
2. Limitations and improvements are documented in the CSV report for easy reference.