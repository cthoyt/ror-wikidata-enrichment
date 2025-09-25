# ror-wikidata-enrichment

Propose new relations for ROR from Wikidata.

Rebuild the data with:

```console
$ uv run main.py
```

Artifacts:

| name                                | description                                                                                    |
| ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| [data/3-wikidata-ror-relations.tsv] | Triples from Wikidata where both the subject and object were mappable to ROR                   |
| [data/4-ror-relations.tsv]          | Triples from ROR, with relations mapped from BFO to Wikidata properties                        |
| [data/5-diff.tsv]                   | All relations appearing in Wikidata that are not already in ROR                                |
| [data/6-diff-suggestions.tsv]       | Relations appearing in Wikidata that are not already in ROR, filtered to fit in the ROR schema |

## License

Code licensed under MIT, data artifacts under CC0.
