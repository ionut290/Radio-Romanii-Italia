# Redazione Geopolitica RDI — modalità ChatGPT (senza API)

- `scripts/update_geopolitica.py` aggiorna i titoli da RSS ogni 15 minuti.
- Il passaggio di generazione OpenAI a pagamento non viene eseguito dal workflow.
- Gli approfondimenti preparati in ChatGPT si pubblicano aggiungendo una voce a `data/geopolitica-articles.json`.
- Le immagini create in ChatGPT vanno caricate nel repository in `data/geopolitica-images/<id>.png` prima di riferirle nel JSON. Non sono fotografie degli eventi: indicarle come illustrazioni IA.
- Per ogni contenuto: verificare più fonti quando possibile, distinguere notizie e analisi, mantenere le citazioni a fonti esterne, indicare lo stato di revisione. Senza verifica editoriale usare `ai_assisted_unreviewed`, non `editorially_reviewed`.
- Prima della pubblicazione eseguire `python scripts/validate_geopolitica_articles.py`. Il validatore controlla schema e lunghezza, non la veridicità dei fatti.
- Ogni articolo deve esistere sia in italiano (`it`) sia in rumeno (`ro`), con massimo 4000 parole per lingua.
- La pagina `geopolitica.html` carica il file JSON aggiornato e gli articoli restano disponibili anche dopo che una notizia esce dal feed giornaliero.

## Esempio di struttura (non pubblicare questo esempio come notizia)

```json
{
  "schema_version": 1,
  "items": {
    "geo-example1234": {
      "id": "geo-example1234",
      "category": "diplomatie",
      "region": "europa",
      "source_url": "https://example.org/source",
      "source_name": "Nome della testata",
      "source_published": "2026-10-28T10:00:00Z",
      "editorial_status": "ai_assisted_unreviewed",
      "it": {
        "title": "Titolo italiano",
        "lead": "Introduzione verificabile e contestualizzata.",
        "sections": [{"heading": "Contesto", "paragraphs": ["Paragrafo approfondito."]}],
        "conclusion": "Conclusione"
      },
      "ro": {
        "title": "Titlu în română",
        "lead": "Introducere",
        "sections": [{"heading": "Context", "paragraphs": ["Paragraf explicativ."]}],
        "conclusion": "Concluzie"
      }
    }
  }
}
```

L'esempio è solo descrittivo e non supera la validazione: i contenuti pubblicabili devono essere molto più approfonditi e comprendere almeno due sezioni per lingua.
