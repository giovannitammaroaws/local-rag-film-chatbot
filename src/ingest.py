import ast
from pathlib import Path

import pandas as pd
import chromadb
import ollama
from tqdm import tqdm

from src.config import CHROMA_PATH, CHROMA_COLLECTION, EMBED_MODEL

_DATA = Path(__file__).parent.parent / "data"
MOVIES_CSV  = str(_DATA / "tmdb_5000_movies.csv")
CREDITS_CSV = str(_DATA / "tmdb_5000_credits.csv")

BATCH_SIZE = 50


# Parses a JSON-encoded column (genres, keywords, cast, crew) and returns
# a comma-separated string of 'name' values, limited to max_items.
def parse_names(json_str: str, max_items: int = 5) -> str:
    try:
        items = ast.literal_eval(json_str)
        return ", ".join(i["name"] for i in items[:max_items])
    except Exception:
        return ""


# Extracts the director name from the crew JSON column.
def extract_director(crew_json: str) -> str:
    try:
        for member in ast.literal_eval(crew_json):
            if member.get("job") == "Director":
                return member["name"]
    except Exception:
        pass
    return "Unknown"


# Loads and merges the two CSVs, extracts relevant fields,
# and returns a clean DataFrame ready for embedding.
def load_dataset() -> pd.DataFrame:
    movies  = pd.read_csv(MOVIES_CSV)
    credits = pd.read_csv(CREDITS_CSV)

    credits = credits.rename(columns={"movie_id": "id"})
    credits = credits.drop(columns=["title"])
    df = movies.merge(credits, on="id")

    df["genres"]   = df["genres"].apply(parse_names)
    df["cast"]     = df["cast"].apply(lambda x: parse_names(x, max_items=3))
    df["director"] = df["crew"].apply(extract_director)
    df["keywords"] = df["keywords"].apply(parse_names)
    df["year"]     = pd.to_datetime(df["release_date"], errors="coerce").dt.year.fillna(0).astype(int)

    df = df.dropna(subset=["overview"])
    df = df[df["overview"].str.strip() != ""]

    return df[["id", "title", "overview", "genres", "cast", "director", "keywords", "year", "vote_average"]]


# Builds the text that will be embedded for each film.
# Combines title, genres, director, cast, keywords and overview.
def build_document(row) -> str:
    return (
        f"Title: {row['title']} ({row['year']})\n"
        f"Director: {row['director']}\n"
        f"Cast: {row['cast']}\n"
        f"Genres: {row['genres']}\n"
        f"Keywords: {row['keywords']}\n"
        f"Overview: {row['overview']}"
    )


# Calls Ollama to generate an embedding vector for a single text.
def embed(text: str) -> list[float]:
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


# Indexes all films into ChromaDB in batches.
# Skips films that are already present (upsert by string id).
def index_films(df: pd.DataFrame):
    client     = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=CHROMA_COLLECTION)

    total   = len(df)
    indexed = 0

    progress = tqdm(total=total, desc="Indexing films", unit="film", ncols=80)

    for start in range(0, total, BATCH_SIZE):
        batch = df.iloc[start : start + BATCH_SIZE]

        ids        = []
        documents  = []
        embeddings = []
        metadatas  = []

        for _, row in batch.iterrows():
            doc = build_document(row)
            ids.append(str(row["id"]))
            documents.append(doc)
            embeddings.append(embed(doc))
            metadatas.append({
                "title":    row["title"],
                "year":     int(row["year"]),
                "director": row["director"],
                "genres":   row["genres"],
                "rating":   float(row["vote_average"]),
            })

        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        indexed += len(batch)
        progress.update(len(batch))

    progress.close()

    print(f"\nDone. {indexed} films stored in ChromaDB at '{CHROMA_PATH}'.")


def main():
    print("Loading dataset...")
    df = load_dataset()
    print(f"  {len(df)} films loaded.\n")

    print(f"Indexing into ChromaDB (model: {EMBED_MODEL})...")
    print("  This will take ~10-15 minutes on first run.\n")
    index_films(df)


if __name__ == "__main__":
    main()
