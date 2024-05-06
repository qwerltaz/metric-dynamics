"""Data processing module."""

import argparse
import os
from typing import Literal

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from parse import DATA_DIR


def process_results(mode: Literal["merge"] = "merge"):
    """Merge all results into a separate table and save to the results directory."""
    merge_dir = os.path.join(DATA_DIR, "results")
    all_results = pd.DataFrame()

    # Get all dataframes from the directory.
    all_results_dataframes_list = get_results_df_list(merge_dir)

    if mode == "merge":
        all_results = pd.concat(all_results_dataframes_list, ignore_index=True)
        save_path = "_all_results.csv"
    else:
        raise ValueError("Invalid mode.")

    all_results = process_default(all_results)
    all_results.to_csv(os.path.join(DATA_DIR, "results", save_path), encoding="utf-8")


def get_results_df_list(path: str):
    """Get a list of dataframes from the directory."""
    df_list = []
    for file in os.listdir(path):
        if file.endswith(".csv"):
            results = pd.read_csv(os.path.join(path, file), encoding="utf-8")

            # Add repo name column to the results.
            repo_name = file.split(".")[0]
            results["repo_name"] = repo_name

            df_list.append(results)

    return df_list


def process_default(df: pd.DataFrame):
    """Default data processing."""
    df.drop(columns=["ID"], inplace=True)
    df.drop_duplicates(subset="hash", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.index.name = "ID"

    df["commit_message"] = df["commit_message"].str.replace("\r\n", " ")

    return df


def main():
    parser = argparse.ArgumentParser(description="Process data.")
    parser.add_argument("--mode", "-m", choices=["merge"], help="Mode of processing the data.",)
    args = parser.parse_args()

    if args.mode == "merge":
        process_results()
        print("Merged results.")


if __name__ == "__main__":
    main()
