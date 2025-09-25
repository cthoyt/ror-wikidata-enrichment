# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "click",
#     "pandas",
#     "pyobo",
#     "tqdm",
#     "wikidata-client",
# ]
# ///

"""This script identifies triples in Wikidata that can be incorporated into ROR.

This script is licensed under the MIT license. ROR and Wikidata are both licensed
under CC0. The data output from this script and stored in this repository
is also licensed under CC0
"""

from typing import Literal

import pandas as pd
import pyobo
import wikidata_client
from pathlib import Path
import click
from textwrap import dedent
from tqdm import tqdm

HERE = Path(__file__).parent.resolve()
DATA = HERE.joinpath("data")

PREDICATES_COUNT_SPARQL = """\
SELECT DISTINCT ?predicate (COUNT(?predicate) as ?count)
WHERE {
  ?subjectROR ^wdt:P6782 ?subject .
  ?subject ?predicate ?object .
  ?object wdt:P6782 ?objectROR .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en". }
}
GROUP BY ?predicate
ORDER BY DESC(?count)
"""


def _values(df: pd.DataFrame, namespace: Literal["wd", "wdt"]) -> str:
    return " ".join(df["predicate"].map(f"{namespace}:{{}}".format))


def _get_ror_name(ror_id: str) -> str | None:
    return pyobo.get_name("ror", ror_id)


def _df_ror_label(df):
    df["subjectLabel"] = df["subjectROR"].map(_get_ror_name)
    df["objectLabel"] = df["objectROR"].map(_get_ror_name)


def _df_predicate_label(df: pd.DataFrame, labels: dict[str, str]) -> None:
    df["predicateLabel"] = df["predicate"].map(labels)


def _tr(df: pd.DataFrame) -> set[tuple[str, ...]]:
    return {tuple(row) for row in df[subcolumns].values}


curie_to_label = {
    ("bfo", "0000062"): ("preceded by", None),
    ("bfo", "0000050"): ("part of", "P361"),
    ("bfo", "0000051"): ("has part", "P527"),
    ("bfo", "0000063"): ("precedes", None),
    # this could be mapped, but not important
    ("rdfs", "seeAlso"): ("see also", None),
}
#: The following Wikidata properties can be suggested back
#: to ROR
properties_that_can_be_suggested: set[str] = {
    wikidata_id
    for _, wikidata_id in curie_to_label.values()
    if wikidata_id
}

columns = [
    "subjectROR",
    "subjectLabel",
    "predicate",
    "predicateLabel",
    "objectROR",
    "objectLabel",
]
subcolumns = ["subjectROR", "predicate", "objectROR"]


@click.command()
def main() -> None:
    path_1 = DATA.joinpath("1-counts.tsv")
    path_2 = DATA.joinpath("2-counts.tsv")
    path_3 = DATA.joinpath("3-wikidata-ror-relations.tsv")
    path_4 = DATA.joinpath("4-ror-relations.tsv")
    path_5 = DATA.joinpath("5-diff-all.tsv")
    path_6 = DATA.joinpath("5-diff-suggestions.tsv")

    if path_3.is_file():
        wd_relations_df = pd.read_csv(path_3, sep="\t")

        # sneaky reload
        predicates_df = pd.read_csv(path_2, sep="\t")
        labels = dict(predicates_df[["predicate", "predicateLabel"]].values)
    else:
        if path_2.is_file():
            predicates_df = pd.read_csv(path_2, sep="\t")
        else:
            if path_1.is_file():
                click.echo(f"reading cache from {path_1}")
                predicates_df = pd.read_csv(path_1, sep="\t")
            else:
                predicates_df = pd.DataFrame(
                    wikidata_client.query(PREDICATES_COUNT_SPARQL)
                )
                predicates_df.to_csv(path_1, sep="\t", index=False)

            # since these are appearing in the predicate part of the query,
            # they have the wikidata direct (wdt) namespace that needs to get
            # stripped
            predicates_df["predicate"] = (
                predicates_df["predicate"]
                .str.removeprefix("http://www.wikidata.org/prop/direct/")
                .astype(str)
            )
            values_wd = _values(predicates_df, "wd")

            predicateL_label_sparql = dedent(f"""\
                SELECT ?predicate ?predicateLabel
                WHERE {{
                  VALUES ?predicate {{ {values_wd} }}
                  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en". }}
                }}
            """)
            labels = {
                r["predicate"]: r["predicateLabel"]
                for r in wikidata_client.query(predicateL_label_sparql)
            }

            _df_predicate_label(predicates_df, labels)
            predicates_df.to_csv(path_2, sep="\t", index=False)

        # apply some filters
        dfs = []

        for predicate in tqdm(predicates_df[predicates_df["count"] >= 50]["predicate"]):
            # this query looks for s-p-o where the predicate is given
            # and both the S and P are linked to ROR IDs
            ror_interaction_sparql = dedent(f"""\
                SELECT ?subjectROR ?objectROR
                WHERE {{ ?subjectROR ^wdt:P6782/wdt:{predicate}/wdt:P6782 ?objectROR . }}
                ORDER BY ?subjectROR ?objectROR
            """)
            tqdm.write(f"running sparql:\n{ror_interaction_sparql}")
            ror_interaction_df = pd.DataFrame(wikidata_client.query(ror_interaction_sparql))
            ror_interaction_df["predicate"] = predicate
            dfs.append(ror_interaction_df)

        wd_relations_df = pd.concat(dfs).sort_values(subcolumns)
        _df_ror_label(wd_relations_df)
        labels = dict(predicates_df[["predicate", "predicateLabel"]].values)
        _df_predicate_label(wd_relations_df, labels)

        # example row:
        # 03nmefy27	Google (Ireland)	P749	parent organization	00njsd438	Google (United States)
        wd_relations_df = wd_relations_df[columns]
        wd_relations_df.to_csv(path_3, sep="\t", index=False)

    if path_4.is_file():
        ror_relations_df = pd.read_csv(path_4, sep='\t')
    else:

        # next step, compare against ROR internal definitions, then make suggestions of relations
        # to add to ROR
        ror_relations_df = pyobo.get_relations_df("ror")
        ror_relations_df = ror_relations_df[ror_relations_df["target_ns"] == "ror"]

        ror_relations_df["predicate"] = [
            curie_to_label[tuple(reference_tuple)][1]
            for reference_tuple in ror_relations_df[["relation_ns", "relation_id"]].values
        ]
        ror_relations_df["predicateLabel"] = ror_relations_df["predicate"].map(labels)
        # filter out all relations we don't want to compare to wikidata
        ror_relations_df = ror_relations_df[ror_relations_df["predicate"].notna()]
        ror_relations_df = ror_relations_df.rename(
            columns={"ror_id": "subjectROR", "target_id": "objectROR"}
        )
        _df_ror_label(ror_relations_df)
        ror_relations_df = ror_relations_df[columns].sort_values(subcolumns)
        ror_relations_df.to_csv(path_4, sep="\t", index=False)

    diff_df = pd.DataFrame(
        _tr(wd_relations_df) - _tr(ror_relations_df), columns=subcolumns
    )
    _df_ror_label(diff_df)
    _df_predicate_label(diff_df, labels)
    diff_df = diff_df[columns]
    diff_df.to_csv(path_5, sep="\t", index=False)

    suggestion_df = diff_df[diff_df['predicate'].isin(properties_that_can_be_suggested)]
    suggestion_df.to_csv(path_6, sep='\t', index=False)

    click.echo(suggestion_df[suggestion_df['subjectLabel'].notna() & suggestion_df['objectLabel'].notna()]
               .head().to_markdown(tablefmt="github", index=False))


if __name__ == "__main__":
    main()
