# TasteMatch 2.0: Music Search That Checks Itself

## Base project

This project is built on my Module 3 project, the **Music Recommender Simulation** (TasteMatch 1.0). Original repo: https://github.com/AnishBashyal/ai110-module3show-musicrecommendersimulation-starter

The original was a small content based music recommender. It read 18 songs from a csv file and compared each one to a user profile (favorite genre, favorite mood, target energy, and if they like acoustic songs). Each song got points: genre match +2.0, mood match +1.0, energy closeness up to +1.0, and acousticness up to +0.5. It showed the top 5 songs and a reason for every point. It only worked if the user's genre and mood matched the csv words exactly.

## What this version does

Now you can just type what you want in normal words, like "mellow music for studying late at night", and the system gives you songs with a short explanation and a confidence score.

Two judges look at your request separately:

- **Judge A** is my original scorer. A keyword parser turns your words into a profile, then the old scoring rules rank the songs. No AI model is used here.
- **Judge B** uses Gemini embeddings. It compares the meaning of your request to a short description of each song. This is the retrieval part (RAG).

Then the system checks if they agree. If they agree, the confidence is high. If they only partly agree, or only one judge understood the request, it still answers but shows a warning. If nothing is trusted (like random letters), it refuses. Gemini then writes a short reason for each song using only the retrieved descriptions and notes, and the code checks that the reason really quotes that text.

## Why it matters

Most recommenders always give you something, even when your request makes no sense. I wanted one that can say "I'm not sure" or "I don't understand this", and shows why it picked each song.

## Architecture overview

<img src="assets/architecture.png" alt="System architecture diagram" width="650">

The diagram is written as text in [diagrams/architecture.mmd](diagrams/architecture.mmd) (Mermaid), and the picture above is made from it. Here is how a request moves through the system:

1. **Input validator** (`src/validator.py`). It cleans the text and rejects things that can't be a music request: empty, too long (over 200 characters), or just numbers and symbols.
2. **Judge A** (`src/judge_a.py`). A keyword parser (`src/text_parser.py`) finds genre, mood, energy and acoustic words, including simple "not sad" handling. Then my original scoring rules rank the songs. If it finds no genre and no mood, Judge A says "no opinion" instead of ranking.
3. **Judge B** (`src/judge_b.py`). It turns the request into an embedding with Gemini and compares it to the saved embeddings of the song descriptions (`data/embeddings_cache.json`). The closest songs win. It also gives a "strength" number, how far the best match is above the average song.
4. **Agreement check** (`src/agreement.py`). It compares the top 5 of both judges. 2 or more shared songs means recommend. 1 shared song means recommend with a warning. If only one judge has an opinion, it answers with a warning and a capped confidence. If nothing is trusted, it refuses.
5. **Explainer** (`src/explainer.py`). Gemini writes one short reason per song using only that song's description and the notes for its genre and mood (`data/notes.json`). It also has to quote its source.
6. **Grounding check.** The code checks that the quote is really in the retrieved text. If not, or if Gemini is down, that song shows its plain description instead.
7. **Run log** (`logs/runs.jsonl`). Every run adds one line, including rejected and refused ones.

Where checking happens:

- **Tests:** a pytest suite that runs offline with a fake Gemini, and an evaluation script (`eval/run_eval.py`) that runs fixed requests through the whole system.
- **Human:** the answer shows the confidence and any warning, and the run log can be read afterwards to see what each judge picked and why.
