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
