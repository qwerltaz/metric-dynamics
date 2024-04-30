"""Data processing module."""

import argparse
import os

import pandas as pd

from parse import DATA_DIR


def merge_results():
    """Merge all results into a separate table and save to the results directory."""
    merge_dir = os.path.join(DATA_DIR, "results")

    all_results_dataframes_list = []
    all_results = pd.DataFrame()

    for file in os.listdir(merge_dir):
        if file.endswith(".csv"):
            results = pd.read_csv(os.path.join(merge_dir, file), encoding="utf-8")

            # Add repo name column to the results.
            repo_name = file.split(".")[0]
            results["repo_name"] = repo_name

            all_results_dataframes_list.append(results)




    # Concatenate, reset index, drop duplicates.
    all_results = pd.concat(all_results_dataframes_list, ignore_index=True)
    all_results.drop(columns=["ID"], inplace=True)
    all_results.drop_duplicates(subset="hash", inplace=True)
    all_results.reset_index(drop=True, inplace=True)
    all_results.index.name = "ID"
    all_results.to_csv(os.path.join(DATA_DIR, "results", "_all_results.csv"), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Process data.")
    parser.add_argument("--merge-results", action="store_true", help="Merge all results into a separate table.")
    args = parser.parse_args()

    if args.merge_results:
        merge_results()
        print("Merged results.")


if __name__ == "__main__":
    main()