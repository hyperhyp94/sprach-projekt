#!/usr/bin/env python3
"""Erstellt Anki .apkg-Dateien aus vocab_de.json"""
import json
import genanki
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUT_DIR = os.path.join(os.path.dirname(__file__), "static")

os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "vocab_de.json"), encoding="utf-8") as f:
    vocab = json.load(f)

# Anki Model: Vorderseite (Fremdsprache) -> Rückseite (Deutsch) + Kategorie-Tag
model = genanki.Model(
    1607392319,
    'A1 Vokabel Modell',
    fields=[
        {'name': 'Vorderseite'},
        {'name': 'Rückseite'},
        {'name': 'Kategorie'},
    ],
    templates=[{
        'name': 'Karte 1',
        'qfmt': '<div style="font-size: 2em; text-align: center; padding: 40px;">{{Vorderseite}}</div>',
        'afmt': '<div style="text-align: center; padding: 20px;">'
                '<div style="font-size: 1.2em; color: #666; margin-bottom: 10px;">{{Vorderseite}}</div>'
                '<div style="font-size: 2em; color: #2563eb; font-weight: bold;">{{Rückseite}}</div>'
                '<div style="margin-top: 20px; color: #999;">🏷️ {{Kategorie}}</div>'
                '</div>',
    }],
)

for lang_code, lang_name in [("es", "Spanisch"), ("tr", "Türkisch")]:
    lang_data = vocab.get(lang_code, {})
    deck = genanki.Deck(
        {
            "es": 2059400110,
            "tr": 2059400111,
        }[lang_code],
        f'A1 {lang_name} Vokabeln',
    )

    for category, words in lang_data.items():
        for w in words:
            note = genanki.Note(
                model=model,
                fields=[w["word"], w["translation"], category],
                tags=[category.replace(" ", "_")],
            )
            deck.add_note(note)

    filename = f'a1-{lang_code}.apkg'
    filepath = os.path.join(OUT_DIR, filename)
    genanki.Package(deck).write_to_file(filepath)
    print(f"✅ {filepath} ({len(lang_data)} Kategorien)")

print("\nFertig! Dateien liegen in static/")
