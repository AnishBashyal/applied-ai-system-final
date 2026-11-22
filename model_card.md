# Model Card: TasteMatch 2.0

**What it is:** a music search where you type what you want in plain words. Two judges rank songs from a catalog of 36 songs (one with my original scoring rules, one with Gemini embeddings), the system checks if they agree, and Gemini writes a short explanation for each song that has to quote the song's description. It extends my Module 3 project, TasteMatch 1.0.

**Intended use:** a prototype that extends a content-based recommender with retrieval, multi-judge agreement, calibrated refusal and grounded explanations, so natural-language requests get answers that say how much to trust them.

**Not intended for:** real music apps, or deciding what real artists get heard. The songs and artists are synthetic and the catalog is small (36 songs), so results show how the system behaves, not real listening taste.

## Limitations and biases

- **Genre is weighted heavily in Judge A.** This is the bias from my original project, and it is still there. In the evaluation, "sad piano for a rainy night" put Glass Hearts (a sad pop song) first, and "happy summer pop" brings in sad pop songs.
- **The keyword parser only knows the words in my lexicon.** Words like "cozy" or "rainy" are not recognised, so Judge A says "no opinion". Negation only works in simple cases like "not sad".
- **Judge B is only as good as my song descriptions.** I wrote all 36 descriptions myself, so my wording and taste shape what gets retrieved. The embedding model was trained on general text, and Cultural and language bias are not covered by my tests, and all requests were in English.
- **Small synthetic catalog.** 19 genres, most with 1 or 2 songs, so the lists have limited variety.
- **The confidence floor rests on 21 requests.** Real requests had a strength of at least 0.076 and nonsense at most 0.070, which is a small gap. It should be checked again if the catalog or the kinds of requests change.
- **The grounding check only proves the quote is real.** It does not check every word of the explanation. One explanation said "deep concentration" when the description said "deep relaxation".
- **It depends on Gemini.** During evaluation Gemini returned 503 and 429 errors. Retries and fallbacks handled them, but with no key, requests with no keywords get refused.
- **Evaluation coverage.** 22 checks: 13 on requests mostly also used for calibration, 6 held-out requests, and 3 consistency runs. They verify the designed behavior and are not a statistical accuracy measure.

## Misuse and how I would prevent it

- **Prompt injection.** The request text goes into the explainer's prompt, so someone could try to slip in instructions. What helps: the request is limited to 200 characters, control characters are removed, Gemini's reply must be valid JSON with a quote, and the quote must be found in the retrieved text. Not yet covered: adversarial injection tests, and the explanation text itself is only partly checked (the quote is verified, not every claim).
- **Cost abuse.** If this were put online, someone could send many requests and use up the API key. It is only a command line tool now, and the key is in `.env`, which is ignored by git. A real service would need rate limits.
- **Over-trusting the answer.** A confident-looking recommendation could be wrong. The system shows a confidence score and a warning when only one judge understood the request, and it refuses instead of guessing.
- **Privacy.** `logs/runs.jsonl` stores every request. It is ignored by git, but a real service would need a clear policy for it.
- **Amplifying popular songs.** With a real catalog, a system like this could keep pushing the same artists. That is why I note it should not decide what real artists get heard.

## Testing results

- **Unit tests:** 102 pass. They run offline with a fake Gemini.
- **Evaluation script** (`python -m eval.run_eval`): 22 of 22 checks passed. That is 13 requests (most also used to set the confidence floor), 6 unseen requests, and 3 requests run twice that gave the same picks both times. Average confidence on answered requests was 0.51. Full output: `logs/evidence/eval_results.txt`.
- **Unseen requests:** 4 real ones were answered with songs in sensible genres and 2 off-topic ones were refused. The weakest was "sad piano for a rainy night" (confidence 0.2), because Judge A put a sad pop song first.
- **Guardrails in the runs:** Gemini returned 503 and 429 errors, and the retries and fallbacks handled them. The grounding check rejected 6 explanations in one run and those songs showed their plain description.

## What surprised me while testing reliability

**Nonsense scored almost as high as real requests.** I expected a gibberish request like "asdf qwerty" to get a clearly low similarity score, so a simple cutoff would catch it. It got 0.61. Real requests ranged from 0.62 to 0.86, so the top similarity alone could not tell them apart. What worked was a different number: how far the best match is above the average song. Real requests had at least 0.076 and nonsense at most 0.070. That is why the floor is based on "strength" and not on raw similarity.

## How I worked with AI

I used Claude Code across the whole lifecycle: design, implementation, testing, debugging and documentation. I kept ownership of the design decisions and the acceptance criteria.

- **Design.** I scoped the extension against my Module 3 recommender: add one concrete, buildable AI feature (retrieval) plus a reliability layer, and keep my original scorer intact as the baseline. I pressed on what the RAG part concretely was (which data, what retrieves it, how the output depends on it) until it was specified: song descriptions plus genre and mood notes, embedding retrieval, and explanations written from the retrieved text. I also found a coupling flaw. If Gemini parsed the request before Judge A ran, both judges would share one failure mode, and their agreement would prove nothing. So I specified two independent pipelines, a keyword parser for A and embeddings for B, that only meet at the agreement check.
- **Prompting.** I ran the build as a staged process: design first, then one module at a time, each with its own tests and its own commit (about 50 commits). I gave explicit constraints (keep it simple, core behavior first, no speculative edge-case work, plain-language docs) and asked for the trade-offs before approving a design. I also used the AI to test its own work. I asked it to trace one request end to end, which showed that Judge A returned a confident-looking ranking when it understood nothing.
- **Debugging.** I validated against the real Gemini API, not only mocked tests, which found what mocks could not: the embedding model merges a list of texts into one vector (every song would have shared one embedding), the first model I tried returned sustained "high demand" errors, and timeouts bypassed the retry logic. A smoke test caught a negation bug in the parser ("not sad" parsed as sad), and a failing test turned out to be a bad test input. Each problem was reproduced, fixed and committed on its own.
- **Verifying the AI's work.** I treated the AI's output as unverified until measured. The confidence floor comes from a calibration run on 21 requests. Raw similarity could not separate real from nonsense requests, so we switched to a strength measure. I then wrote expected outcomes for new requests before running them, so the evaluation covers unseen input. I tested how the system behaves when Gemini or the key is missing, and I re-checked the docs against the code and fixed errors such as a wrong check count in the README.

**One suggestion I accepted:** after I traced "cozy rainy afternoon", we saw that my original scorer, when it understood nothing, still ranked songs by energy alone and gave them a top score of 1.00. The AI suggested that Judge A should abstain when it finds no genre and no mood, and that Judge A should stay keyword-only so it does not depend on Gemini. I accepted both. Now Judge A says "no opinion", and Judge B can answer alone with a warning.

**One suggestion I did not accept as written:** the AI proposed three judges (my rules, embeddings, and Gemini reading the songs and rating them). I said the embedding judge and the Gemini judge sounded the same, since both go by meaning. The AI agreed, and we cut it to two judges. Gemini is used for the explanations instead.

**One suggestion I changed:** the plan was to use a second Gemini call to check that each explanation was grounded. I scoped the work to the core behavior, not small edge cases. We changed it to one call where Gemini must quote its source, and a plain-code check that the quote is really in the retrieved text. It is simpler, free, and cannot be fooled the same way. Trade-off: it checks the quote and not every word.

## What I would improve next

- Test the Gemini rewrite step on a bigger catalog, and run the confidence floor on more requests.
- Log the rejected quotes to confirm why the grounding check rejects them (likely Gemini paraphrases instead of copying).
- Test against prompt injection attempts.
- Use a real music catalog and descriptions written by more than one person.
