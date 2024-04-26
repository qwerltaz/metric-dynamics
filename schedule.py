"""Schedule metrics collection for a number of repositories."""

import argparse

import pandas as pd

from parse import MetricParse


def schedule_repositories(repo_urls_csv_path: str) -> None:
    """
    Schedule metrics collection for a number of repositories, from a csv file with repository names and urls.

    :param repo_urls_csv_path: path to csv file with columns `name` and `repo_url`
    """
    repo_urls = pd.read_csv(repo_urls_csv_path, encoding="utf-8")

    # Column to track which repositories have been computed.
    if "computed" not in repo_urls.columns:
        repo_urls["computed"] = False

    for i, row in repo_urls.iterrows():
        if row["computed"]:
            continue

        repo_url = row["repo_url"]
        if repo_url and isinstance(repo_url, str):
            metric_parse = MetricParse(repo_url)
            metric_parse.save_metrics_for_each_commit()

        repo_urls.loc[i, "computed"] = True
        repo_urls.to_csv(repo_urls_csv_path, index=False, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Schedule metrics collection for a number of repositories.")
    parser.add_argument("--mode", "-m", choices=["tiny", "full"], help="Mode to run the script in.",
                        default="tiny", required=False)
    args = parser.parse_args()

    if args.mode == "tiny":
        schedule_repositories("data/url/urls_tiny.csv")
    elif args.mode == "full":
        schedule_repositories("data/url/pypi_top_1000.csv")


if __name__ == "__main__":
    main()
