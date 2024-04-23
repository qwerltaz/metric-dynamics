"""Contains a class to parse metrics for each commit in a git repository."""

from datetime import datetime
from enum import Enum
import json
import os
from time import perf_counter
from typing import Literal

import git
import pandas as pd
from pydriller import Repository, Commit
import radon
import radon.complexity
from radon.cli import Config
from radon.cli.harvest import CCHarvester, RawHarvester, HCHarvester, MIHarvester

from logger import get_logger

DATA_DIR = "data"

logger = get_logger()


class HarvesterOutcome(Enum):
    """Errors that can occur during metrics harvesting."""
    SUCCESS = 0
    PYTHON_VERSION_2 = 1
    INVALID_CODE = 2


class MetricParse:
    """Parse metrics from a git repository."""

    def __init__(self, repo_url: str):
        """
        Initialize metric parser from repository url.

        :param repo_url: repository url
        """
        if not isinstance(repo_url, str) or not repo_url:
            raise ValueError("Received repository URL was empty or None.")

        self.repo_url = repo_url
        self.repo_name = self.repo_url.split("/")[-1]
        self.repo_dir = os.path.join(DATA_DIR, "repos", self.repo_name)

        self.repo: git.Repo
        if os.path.isdir(self.repo_dir) and os.listdir(self.repo_dir):
            self.repo = git.Repo(self.repo_dir)
        else:
            self.repo = git.Repo.clone_from(self.repo_url, self.repo_dir)

        self.repo.git.checkout(self.main_branch)

    @staticmethod
    def shorten_commit_message(commit_message: str, max_len: int = 100) -> str:
        """Shorten commit message for logging."""
        msg = commit_message.replace("\n", " ")
        if len(msg) > max_len:
            msg = msg[:max_len]
            msg += "..."
        return msg

    def _get_unprocessed_commit_hash_range(self) -> tuple[str | None, str | None]:
        """Get start and end commit hashes not included in the repository's results table."""
        if not os.path.exists(self._default_save_path):
            return None, None

        results_df = pd.read_csv(self._default_save_path)
        if results_df.empty:
            return None, None

        # Reverse order: from the very first commit to the first in the results table.
        first_hash = None
        last_hash = results_df["hash"].iloc[0]

        return first_hash, last_hash

    def save_metrics_for_each_commit(self, save_path: str = None) -> None:
        """Save info and metrics for each commit in main branch in a csv file."""
        branch_main = self.main_branch

        commit_count = self.repo.git.rev_list('--count', 'HEAD')
        commit_metrics_list = []

        start_hash, end_hash = self._get_unprocessed_commit_hash_range()
        traverser = Repository(
            self.repo_dir,
            only_in_branch=branch_main,
            only_modifications_with_file_types=[".py"],
            num_workers=4,
            order="reverse",
            # to=datetime.fromisoformat("2016-11-17"),
            from_commit=start_hash,
            to_commit=end_hash,
        ).traverse_commits()

        save_frequency = 100
        commit_start_time = perf_counter()
        for i, commit in enumerate(traverser):
            time_taken = perf_counter() - commit_start_time
            commit_start_time = perf_counter()
            print(
                'repo', self.repo_name,
                '| commit', i + 1, 'of', commit_count,
                '| author:', commit.author.name,
                '| date:', commit.committer_date,
                '| lines_changed: ', f'{commit.lines} (+{commit.insertions} -{commit.deletions})',
                '| time taken:', f'{time_taken:.2f}s',
                '\n\tcommit message:', self.shorten_commit_message(commit.msg)
            )

            commit_metric_dict = {
                "hash": commit.hash,
                "author": commit.author.name,
                "date": commit.committer_date,
                "commit_message": commit.msg,
                "is_merge": commit.merge,
                "lines_changed": commit.lines,
                "insertions": commit.insertions,
                "deletions": commit.deletions,
                "dmm_unit_size": commit.dmm_unit_size,
                "dmm_unit_complexity": commit.dmm_unit_complexity,
                "dmm_unit_interfacing": commit.dmm_unit_interfacing,
            }

            sw_metrics, outcome = self._get_metrics(commit)
            if sw_metrics is None:
                # Shortened message for logging.
                commit_msg_short = self.shorten_commit_message(commit.msg)

                if outcome == HarvesterOutcome.PYTHON_VERSION_2:
                    logger.info(
                        f"Error computing metrics for {self.repo_name}. "
                        + f"Invalid python version, stopped for repository at: \"{commit_msg_short}\" ({commit.hash}).")
                    break
                elif outcome == HarvesterOutcome.INVALID_CODE:
                    logger.info(
                        f"Error computing metrics for {self.repo_name}. "
                        + f"Skipped commit \"{commit_msg_short}\" ({commit.hash}).")
                    continue

            # Add software metrics to commit metrics.
            commit_metric_dict |= sw_metrics
            commit_metrics_list.append(commit_metric_dict)

            if (i + 1) % save_frequency == 0:
                self._save_to_csv(commit_metrics_list, save_path)

        if not commit_metrics_list:
            logger.warning(f"Found zero computable commits for {self.repo_name}.")
            return

        self._save_to_csv(commit_metrics_list, save_path)

    def _save_to_csv(self, metrics_list: list, save_path: str) -> None:
        """Save DataFrame of metrics to a csv file."""
        if not metrics_list:
            return

        metrics_df = pd.DataFrame(metrics_list)

        if save_path:
            result_path = save_path
        else:
            result_path = self._default_save_path

        if os.path.exists(result_path):
            old_df = pd.read_csv(result_path, index_col="ID", encoding="utf-8")
            metrics_df = pd.concat([old_df, metrics_df], ignore_index=True)

        metrics_df["date"] = pd.to_datetime(metrics_df["date"], utc=True)
        metrics_df.sort_values("date", inplace=True)
        metrics_df.reset_index(drop=True, inplace=True)
        metrics_df.index.name = "ID"

        metrics_df.to_csv(result_path, encoding="utf-8", mode="w")

    def _get_metrics(self, commit: Commit) -> tuple[dict[str, float] | None, HarvesterOutcome]:
        """
        Checkout parser's repo at given commit and compute software metrics for that commit.
        Computes total raw metrics (LOC, LLOC, SLOC, comments), and average of other metrics.
        """
        metric_dict = dict()

        self.repo.git.checkout(commit.hash, force=True)

        config = Config(
            exclude=[],
            ignore=[],
            no_assert=True,
            show_closures=False,
            order=radon.complexity.SCORE,
            show_complexity=True,
            min='A',
            max='F',
            total_average=True,
            include_ipynb=False,
            multi=True,  # Count multiline strings as comment lines as well.
            by_function=False,
        )

        # Dict to store lists of unit complexity metrics.
        unit_complexity_lists = dict()

        # List to store errors from harvester. Contains lists of [str, dict].
        harvester_errors: list[list] = []

        # Raw metrics. Summed across the commit.
        raw_harvester = RawHarvester([self.repo_dir], config)
        raw_results = json.loads(raw_harvester.as_json())
        keys = ["LOC",  # Lines of code (total).
                "LLOC",  # Logical lines of code (containing exactly one statement).
                "SLOC",  # Source lines of code.
                "comments"]  # Comment lines.
        for key in keys:
            metric_dict["radon_" + key] = 0
        for file_path, file in raw_results.items():
            if "error" in file:
                harvester_errors.append([file_path, file])
                break
            for key in keys:
                metric_dict["radon_" + key] += file[key.lower()]

        # Cyclomatic complexity. Per function.
        cc_harvester = CCHarvester([self.repo_dir], config)
        cc_results = json.loads(cc_harvester.as_json())
        unit_complexity_lists["cc"] = []  # Cyclomatic complexity.
        for file_path, file in cc_results.items():
            if "error" in file:
                harvester_errors.append([file_path, file])
                break
            for unit in file:
                unit_complexity_lists["cc"].append(unit["complexity"])

        # Maintainability index. Per file.
        mi_harvester = MIHarvester([self.repo_dir], config)
        mi_results = json.loads(mi_harvester.as_json())
        unit_complexity_lists["MI"] = []
        for file_path, file in mi_results.items():
            if "error" in file:
                harvester_errors.append([file_path, file])
                break
            unit_complexity_lists["MI"].append(file["mi"])

        # Halstead's complexity. Per file.
        config.by_function = False
        hc_harvester = HCHarvester([self.repo_dir], config)
        hc_results = json.loads(hc_harvester.as_json())
        keys = ["vocabulary", "length", "volume", "difficulty", "effort", "time", "bugs"]
        for key in keys:
            unit_complexity_lists[key] = []
        for file_path, file in hc_results.items():
            if "error" in file:
                harvester_errors.append([file_path, file])
                break
            for key in keys:
                unit_complexity_lists[key].append(file["total"][key])

        if harvester_errors:
            for file_path, file in harvester_errors:
                if file["error"].startswith("Missing parentheses in call to 'print'. Did you mean print(...)?"):
                    return None, HarvesterOutcome.PYTHON_VERSION_2

                logger.info(f"Error in harvester at {file_path}: {file['error']}")
                return None, HarvesterOutcome.INVALID_CODE

        # Compute average of each metric, across the commit.
        for metric in unit_complexity_lists:
            metric_dict["radon_avg_" + metric] = self._metric_avg(unit_complexity_lists[metric])

        return metric_dict, HarvesterOutcome.SUCCESS

    @staticmethod
    def _metric_avg(metrics: list) -> float | None:
        """Compute average of metrics."""
        if not metrics:
            return None
        return sum(metrics) / len(metrics)

    @property
    def _default_save_path(self) -> str:
        """Default save path for results."""
        return os.path.join(DATA_DIR, "results", self.repo_name + ".csv")

    @property
    def main_branch(self) -> str:
        """Main or master branch of the parser's repository."""

        candidates = ["main", "master", "origin/main", "origin/master"]
        refs = self.repo.references
        for candidate in candidates:
            if candidate in refs:
                return candidate
        raise Exception(f"Main branch not in {self.repo_url}.")


def trial():
    metric_parse = MetricParse("https://github.com/coreyleveen/irc_bot")
    metric_parse.save_metrics_for_each_commit()


if __name__ == "__main__":
    trial()
