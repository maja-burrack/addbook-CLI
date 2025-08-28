
import os
from datetime import datetime, date
from dotenv import load_dotenv
from utils import parse_date

load_dotenv()

vault_path = os.path.expanduser(os.getenv("OBSIDIAN_VAULT", "~/ObsidianVault"))
notes_dir = os.path.join(vault_path, "03 resources", "bibliography")
os.makedirs(notes_dir, exist_ok=True)

def _clean_string(s, replace=['{', '}']):
    return s.replace("{", "").replace("}", "")

def full_length_language(language):
    LANG_DICT = {
        'english': ['eng', 'en'],
        'danish': ['dan', 'da']
    }
    
    for k, v in LANG_DICT.items():
        if language in v:
            return k
        else:
            continue
    
    # Fallback
    return language

def make_bibtex_key(biblatex_entry: dict):
    authors = biblatex_entry.get("author", "")
    title = biblatex_entry.get("title", "")
    year = biblatex_entry.get("year")
    try:
        publication_date = biblatex_entry['date']
    except:
        try:
            publication_date = biblatex_entry.get("publish_date", "")
            if not year:
                year = parse_date(publication_date).year
        except ValueError:
            year = ""
    
    authors = _clean_string(authors)
    title = _clean_string(title)
    
    # Take last name of first author, lowercase
    last_name = authors.split(" and ")[0].split(",")[0].lower()
    
    # Take first three words of title, capitalize first letter of each, remove spaces
    title_words = title.split()[:3]
    short_title = "".join(word.capitalize() for word in title_words)
    
    key = f"{last_name}{short_title}{year}"
    return key

def create_markdown_file(biblatex_entry, dst, language=None, type="", genre="", notes=""):

    citekey = make_bibtex_key(biblatex_entry)
    authors = biblatex_entry.get("author", "")
    title = biblatex_entry.get("title", "")
    year = biblatex_entry.get("year")
    try:
        publication_date = biblatex_entry['date']
    except:
        try:
            publication_date = biblatex_entry.get("publish_date", "")
            if not year:
                year = parse_date(publication_date).year
        except ValueError:
            year = ""
            
    if not language:
        language = biblatex_entry.get("language", "english")
    language = full_length_language(language).lower()
        
    today = date.today().isoformat()
    
    authors = _clean_string(authors)
    title = _clean_string(title)
        
    content = f"""---
title: {title}
author: {authors}
year: {year}
type: {type}
genre: {genre}
language: {language}
completion_date: {today}
date: {today}
completed: True
tags: source/book
---
# {title}
*by {authors}*

## My Notes
{notes}

"""
    filename = os.path.join(dst, f"@{citekey}.md")
    if os.path.exists(filename):
        print(f"Obsidian note NOT created, because note already exists: {filename}")
        return None
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Created Obsidian literature note: {filename}")
