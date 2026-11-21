"""
Keyword lexicon for Judge A's rule-based query parser.

No LLM is involved here. Each table maps words a person might type to the
labels that already exist in data/songs.csv, so the original scorer can use them.
"""

# words that point straight at a genre in the catalog
GENRE_WORDS = {
    "pop": "pop",
    "lofi": "lofi",
    "lo-fi": "lofi",
    "lo fi": "lofi",
    "rock": "rock",
    "ambient": "ambient",
    "jazz": "jazz",
    "synthwave": "synthwave",
    "retrowave": "synthwave",
    "indie": "indie pop",
    "indie pop": "indie pop",
    "hip hop": "hip hop",
    "hip-hop": "hip hop",
    "rap": "hip hop",
    "classical": "classical",
    "orchestra": "classical",
    "country": "country",
    "edm": "edm",
    "electronic": "edm",
    "techno": "edm",
    "r&b": "r&b",
    "rnb": "r&b",
    "metal": "metal",
    "folk": "folk",
    "reggae": "reggae",
    "blues": "blues",
    "punk": "punk",
    "latin": "latin",
    "salsa": "latin",
    "soul": "soul",
}

# words that suggest a mood (the mood must exist in the catalog)
MOOD_WORDS = {
    "happy": "happy", "cheerful": "happy", "sunny": "happy", "upbeat": "happy", "morning": "happy",
    "chill": "chill", "mellow": "chill", "lazy": "chill", "laid back": "chill",
    "intense": "intense", "workout": "intense", "gym": "intense", "running": "intense",
    "training": "intense", "lifting": "intense",
    "relax": "relaxed", "relaxed": "relaxed", "relaxing": "relaxed", "unwind": "relaxed",
    "moody": "moody", "dark": "moody", "midnight": "moody", "late night": "moody", "brooding": "moody",
    "focus": "focused", "focused": "focused", "study": "focused", "studying": "focused",
    "concentrate": "focused", "coding": "focused", "work": "focused", "reading": "focused",
    "confident": "confident", "swagger": "confident", "bold": "confident",
    "peaceful": "peaceful", "calm": "peaceful", "quiet": "peaceful", "sleep": "peaceful",
    "serene": "peaceful",
    "nostalgic": "nostalgic", "nostalgia": "nostalgic", "memories": "nostalgic", "throwback": "nostalgic",
    "euphoric": "euphoric", "ecstatic": "euphoric",
    "romantic": "romantic", "romance": "romantic", "date": "romantic", "dinner": "romantic",
    "candlelit": "romantic", "love": "romantic",
    "aggressive": "aggressive", "angry": "aggressive", "rage": "aggressive",
    "melancholy": "melancholy", "wistful": "melancholy", "lonely": "melancholy",
    "uplifting": "uplifting", "hopeful": "uplifting", "road trip": "uplifting",
    "sad": "sad", "heartbreak": "sad", "crying": "sad", "tears": "sad", "breakup": "sad",
    "rebellious": "rebellious", "rebel": "rebellious", "defiant": "rebellious",
    "joyful": "joyful", "celebrate": "joyful", "dance": "joyful", "dancing": "joyful",
    "dreamy": "dreamy", "floating": "dreamy", "hazy": "dreamy",
}

# energy cues: each hit pulls the target energy toward its value (0 to 1)
ENERGY_WORDS = {
    # low
    "mellow": 0.3, "calm": 0.25, "quiet": 0.25, "sleep": 0.2, "relax": 0.3, "relaxing": 0.3,
    "chill": 0.35, "study": 0.35, "studying": 0.35, "soft": 0.3, "slow": 0.3, "gentle": 0.3,
    "peaceful": 0.25, "lazy": 0.3,
    # medium
    "upbeat": 0.7, "road trip": 0.7, "driving": 0.7,
    # high
    "workout": 0.92, "gym": 0.92, "running": 0.9, "party": 0.88, "intense": 0.92, "loud": 0.92,
    "fast": 0.9, "hype": 0.9, "energetic": 0.9, "pump": 0.92, "festival": 0.92, "dance": 0.85,
}

# acousticness cues
ACOUSTIC_WORDS = {"acoustic": True, "unplugged": True, "piano": True, "guitar": True,
                  "electronic": False, "synth": False, "edm": False}
