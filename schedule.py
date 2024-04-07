"""Schedule metrics collection for a number repositories."""

import os

import pandas as pd

from parse import MetricParse


def schedule_repositories(repo_urls_csv_path: str) -> None:
    """
    Schedule metrics collection for a number repositories, from a csv file with repository names and urls.

    :param repo_urls_csv_path: path to csv file with columns `name` and `repo_url`
    """
    repo_urls = pd.read_csv(repo_urls_csv_path)

    # TODO: try saving progress in a file, to continue from where it stopped

    for i, row in repo_urls.iterrows():
        repo_name = row["name"]
        repo_url = row["repo_url"]
        metric_parse = MetricParse(repo_url)
        metric_parse.save_metrics_for_each_commit()  # TODO manually set results path

os.path.join("data", "results", "tiny")