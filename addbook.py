__version__ = "0.1.0"

import argparse
import requests
import sys
import os
from dotenv import load_dotenv
from pyzotero import zotero

from obsidian_utils import create_markdown_file
from utils import parse_date, unique_list_of_dicts

load_dotenv()

ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID")
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_LIBRARY = os.getenv("ZOTERO_LIBRARY", "user")

VAULT_PATH = os.path.expanduser(os.getenv("OBSIDIAN_VAULT", "~/ObsidianVault"))
NOTES_DIR = os.path.join(VAULT_PATH, "03 resources", "bibliography")

if not ZOTERO_USER_ID or not ZOTERO_API_KEY:
    print("Missing Zotero credentials. Please set ZOTERO_USER_ID and ZOTERO_API_KEY in your .env file.")
    sys.exit(1)

def find_isbn(title, author=None, language="eng"):
    query = f"https://openlibrary.org/search.json?title={title}"
    if author:
        query += f"&author={author}"
    resp = requests.get(query)
    if resp.status_code != 200:
        return None
    data = resp.json()
    docs = data.get("docs", [])
    if not docs:
        return None

    # Filter docs by language
    filtered_docs = [d for d in docs if language in d.get("language", [])]
    if not filtered_docs:
        print("could not find any docs in language")
        return None

    # Pick the first doc
    doc = filtered_docs[0]

    # Get all editions for this work
    work_key = doc.get("key")  # e.g., '/works/OL2707183W'
    editions_url = f"https://openlibrary.org{work_key}/editions.json"
    editions_resp = requests.get(editions_url)
    if editions_resp.status_code != 200:
        return None
    editions = editions_resp.json().get("entries", [])
    
    # only allow physical books (however, physical_format is often missing)
    allowed_formats = ['paperback', 'hardback', 'hardcover', 'softback', 'perfect paperback', 'book', '']
    editions = [edition for edition in editions if edition.get("physical_format", "").lower() in allowed_formats]
    if not editions:
        return None
    
    # allow only specified language
    filtered_editions = []
    for edition in editions:
        langs = edition.get("languages", [])
        lang_keys = []
        for l in langs:
            if isinstance(l, dict) and "key" in l:
                lang_keys.append(l["key"].split("/")[-1])
        if language in lang_keys:
            filtered_editions.append(edition)
    
    # Order editions by allowed_formats and then by publish_date (ascending)
    format_priority = {fmt: i for i, fmt in enumerate(allowed_formats)}
    
    filtered_editions.sort(
        key=lambda edition: (
            format_priority.get(edition.get("physical_format", "").lower(), len(format_priority)),
            parse_date(edition.get("publish_date"))
        )
    )

    # Find the first edition with an ISBN
    for edition in filtered_editions:
        for key in ["isbn_13", "isbn_10"]:
            if key in edition and edition[key]:
                return edition[key][0]

    # Fallback: try top-level doc ISBNs
    for key in ["isbn", "isbn_10", "isbn_13"]:
        if key in doc and doc[key]:
            return doc[key][0]

    return None

def fetch_metadata(isbn):
    """Get book metadata from Open Library by ISBN"""
    url = f"https://openlibrary.org/isbn/{isbn}.json"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None
    return resp.json()

def get_author_names(authors):
    """Given a list of author dicts with 'key', return a list of names"""
    unique_authors = unique_list_of_dicts(authors)
    names = []
    for author in unique_authors:
        key = author.get("key")
        if not key:
            continue
        url = f"https://openlibrary.org{key}.json"
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            name = data.get("name")
            if name:
                names.append(name)
    return names

def build_creators(author_names):
    """
    Convert a list of full author names into Zotero creators list.
    Each creator is a dict with creatorType, firstName, lastName.
    """
    creators = []
    for name in author_names:
        name = name.strip()
        if "," in name:
            # Format "Last, First"
            last, first = name.split(",", 1)
            creators.append({
                "creatorType": "author",
                "firstName": first.strip(),
                "lastName": last.strip()
            })
        else:
            # Format "First Last" or single word
            parts = name.split()
            if len(parts) == 1:
                creators.append({
                    "creatorType": "author",
                    "firstName": parts[0],
                    "lastName": ""
                })
            else:
                creators.append({
                    "creatorType": "author",
                    "firstName": " ".join(parts[:-1]),
                    "lastName": parts[-1]
                })
    return creators

def define_item(metadata, language='eng'):
    author_names = get_author_names(metadata.get("authors"))
    creators = build_creators(author_names)
    
    title = metadata.get("title")
            
    item = {
        "itemType": "book",
        "title": metadata.get("title"),
        "creators": creators,
        "date": metadata.get("publish_date"),
        "publisher": metadata.get("publishers", [None])[0],
        "language": language,
        "ISBN": metadata.get("isbn_13", [None])[0] or metadata.get("isbn_10", [None])[0],
    }
    return item

def add_to_zotero(metadata, language='eng'):
    """Add book to Zotero with full metadata"""
    zot = zotero.Zotero(ZOTERO_USER_ID, ZOTERO_LIBRARY, ZOTERO_API_KEY)
    
    item = define_item(metadata, language)
    created_item = zot.create_items([item])
    
    if len(created_item['successful'])>0:
        print(f"Added '{metadata.get('title')}' to Zotero")
    else:
        print(f"Failed to add '{metadata.get('title')}' to Zotero")
    return created_item

def get_biblatex_entry(created_item):
    zot = zotero.Zotero(ZOTERO_USER_ID, ZOTERO_LIBRARY, ZOTERO_API_KEY)
    
    item_key = list(created_item['successful'].values())[0]['key']
    entry = zot.item(item_key, format='bibtex')
    entry = entry.entries[0]
    return entry
    

def main():
    parser = argparse.ArgumentParser(description="Add book to Zotero by title/author")
    parser.add_argument("title", help="Book title")
    parser.add_argument("author", nargs="?", help="Author name (optional)")
    parser.add_argument("--lang", default="eng", help="Language code (default: eng)")
    parser.add_argument("--obsidian", type=lambda x: x.lower() in ("true", "1", "yes"), default=True, help="Create Obsidian note (default: True)")
    parser.add_argument("--type", default="", help="Fiction or non-fiction (default: None)")
    parser.add_argument("--genre", default="", help="Book genre. Any string will do (default: None)")
    parser.add_argument("--notes", default="")
    
    args = parser.parse_args()

    isbn = find_isbn(args.title, args.author)
    if not isbn:
        print("Could not find ISBN")
        sys.exit(1)
        
    metadata = fetch_metadata(isbn)
    
    created_item = add_to_zotero(metadata)
    
    if args.obsidian:
        bib_entry = get_biblatex_entry(created_item)
        os.makedirs(NOTES_DIR, exist_ok=True)
        create_markdown_file(bib_entry, dst=NOTES_DIR, language=args.lang, type=args.type, genre=args.genre, notes=args.notes)

if __name__ == "__main__":
    main()
