import argparse
import json
import os

import git
import pandas as pd
from pydriller import Repository, Commit
import radon
from radon.cli import Config
from radon.cli.harvest import CCHarvester, RawHarvester, HCHarvester, MIHarvester

DATA_DIR = "data"


class MetricParse:
    """Parse metrics from a git repository."""

    def __init__(self, repo_url: str):
        """
        Initialize metric parser from repository url.

        :param repo_url: repository url
        """
        self.repo_url = repo_url

        self.repo_name = self.repo_url.split("/")[-1]
        self.repo_dir = os.path.join(DATA_DIR, "repos", self.repo_name)

        self.repo: git.Repo
        if os.path.isdir(self.repo_dir) and os.listdir(self.repo_dir):
            self.repo = git.Repo(self.repo_dir)
        else:
            self.repo = git.Repo.clone_from(self.repo_url, self.repo_dir)

        self.repo.git.checkout(self.main_branch)

    def save_metrics_for_each_commit(self) -> None:
        """Save info and metrics for each commit in main branch in a csv file."""
        branch = self.main_branch

        # TODO: count commits only in main branch
        commit_count = self.repo.git.rev_list('--count', 'HEAD')
        commit_metrics_list = []
        traverser = Repository(
            self.repo_dir,
            only_in_branch=branch,
            only_modifications_with_file_types=[".py"],
            num_workers=4,
        ).traverse_commits()

        sloc = 0  # Source lines of code.
        all_lines = 0  # All additions and deletions combined.
        for i, commit in enumerate(traverser):
            sloc = sloc + commit.insertions - commit.deletions
            all_lines = all_lines + commit.lines

            if __name__ == "__main__":
                print(
                    'commit', i + 1, 'of', commit_count,
                    '| author:', commit.author.name,
                    '| date:', commit.committer_date,
                    '| lines_changed: ', f'{commit.lines} (+{commit.insertions} -{commit.deletions})',
                )

            commit_metric_dict = {
                "hash": commit.hash,
                "author": commit.author.name,
                "date": commit.committer_date,
                "commit_message": commit.msg,
                "is_merge": commit.merge,
                "codebase_size": sloc,
                "lines_changed": commit.lines,
                "total_lines_changed": all_lines,
                "insertions": commit.insertions,
                "deletions": commit.deletions,
                "dmm_unit_size": commit.dmm_unit_size,
                "dmm_unit_complexity": commit.dmm_unit_complexity,
                "dmm_unit_interfacing": commit.dmm_unit_interfacing,
            }

            commit_metric_dict |= self.get_metrics(commit)
            commit_metrics_list.append(commit_metric_dict)

        commit_metrics_df = pd.DataFrame(commit_metrics_list)
        commit_metrics_df["date"] = pd.to_datetime(commit_metrics_df["date"], utc=True)

        commit_metrics_df.to_csv(os.path.join(DATA_DIR, "commit_metrics_" + self.repo_name + ".csv"))

    def get_metrics(self, commit: Commit) -> dict[str, float]:
        """
        Checkout parser's repo at given commit and compute software metrics for that commit.
        Computes total raw metrics (LOC, LLOC, SLOC, comments), and average of other metrics.
        """
        metric_dict = dict()

        self.repo.git.checkout(commit.hash)

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

        # Raw metrics. Summed across the commit.
        raw_harvester = RawHarvester([self.repo_dir], config)
        raw_results = json.loads(raw_harvester.as_json())
        keys = ["LOC",  # Lines of code (total).
                "LLOC",  # Logical lines of code (containing exactly one statement).
                "SLOC",  # Source lines of code.
                "comments",  # Comment lines.
                ]
        for key in keys:
            metric_dict["radon_" + key] = 0
        for file in raw_results.values():
            for key in keys:
                metric_dict["radon_" + key] += file[key.lower()]

        # Cyclomatic complexity. Per function.
        cc_harvester = CCHarvester([self.repo_dir], config)
        cc_results = json.loads(cc_harvester.as_json())
        unit_complexity_lists["cc"] = []  # Cyclomatic complexity.
        for file in cc_results.values():
            for unit in file:
                unit_complexity_lists["cc"].append(unit["complexity"])

        # Maintainability index. Per file.
        mi_harvester = MIHarvester([self.repo_dir], config)
        mi_results = json.loads(mi_harvester.as_json())
        unit_complexity_lists["MI"] = []
        for file in mi_results.values():
            unit_complexity_lists["MI"].append(file["mi"])

        # Halstead complexity. Per file.
        config.by_function = False
        hc_harvester = HCHarvester([self.repo_dir], config)
        hc_results = json.loads(hc_harvester.as_json())
        keys = ["vocabulary", "length", "volume", "difficulty", "effort", "time", "bugs"]
        for key in keys:
            unit_complexity_lists[key] = []
        for file in hc_results.values():
            for key in keys:
                unit_complexity_lists[key].append(file["total"][key])

        # Compute average of each metric, across the commit.
        for metric in unit_complexity_lists:
            metric_dict["radon_avg_" + metric] = self.metric_avg(unit_complexity_lists[metric])

        return metric_dict

    @staticmethod
    def metric_avg(metrics: list) -> float:
        """Compute average of metrics."""
        return sum(metrics) / len(metrics)

    @property
    def main_branch(self) -> str:
        """Main or master branch of the parser's repository."""

        candidates = ["main", "master", "origin/main", "origin/master"]
        refs = self.repo.references
        for candidate in candidates:
            if candidate in refs:
                return candidate
        raise Exception(f"Main branch not in {self.repo_url}.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--size", dest="size", choices=['s', 'm', 'b'], default='s', help="Repo size.")
    args = parser.parse_args()

    if args.size == "s":
        mp = MetricParse("https://github.com/qwerltaz/ml_proj2022")
    elif args.size == "m":
        mp = MetricParse("https://github.com/areski/python-nvd3")

    mp.save_metrics_for_each_commit()


if __name__ == "__main__":
    main()
