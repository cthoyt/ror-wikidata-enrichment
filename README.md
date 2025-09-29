# ror-wikidata-enrichment

Code for proposing new relations to ROR from Wikidata, accompanying the blog post
at [https://cthoyt.com/2025/09/25/enriching-ror-with-wikidata.html](https://cthoyt.com/2025/09/25/enriching-ror-with-wikidata.html).

Rebuild the data with:

```console
$ uv run main.py
```

Artifacts:

| name                                | description                                                                                    |
| ----------------------------------- | ---------------------------------------------------------------------------------------------- |
| [data/3-wikidata-ror-relations.tsv](data/3-wikidata-ror-relations.tsv) | Triples from Wikidata where both the subject and object were mappable to ROR                   |
| [data/4-ror-relations.tsv](data/4-ror-relations.tsv)          | Triples from ROR, with relations mapped from BFO to Wikidata properties                        |
| [data/5-diff.tsv](data/5-diff.tsv)                   | All relations appearing in Wikidata that are not already in ROR                                |
| [data/6-diff-suggestions.tsv](data/6-diff-suggestions.tsv)       | Relations appearing in Wikidata that are not already in ROR, filtered to fit in the ROR schema |

## License

ROR and Wikidata are both licensed under CC0.

Original code licensed under MIT, original data artifacts under CC0.
