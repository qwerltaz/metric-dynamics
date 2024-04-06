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

    def get_metrics(self, commit: Commit) -> dict:
        """Checkout commit and compute software metrics."""
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
            include_ipynb=False
        )

        cc_harvester = CCHarvester([self.repo_dir], config)
        cc_results = cc_harvester.as_json()
        # with open("data/results/tiny/test-radon-results-cc.json", 'w', encoding='utf-8') as f:
        #     f.write(cc_results)
        # TODO: add method to compute avg, put metrics in metric_dict for each harvester.

        raw_harvester = RawHarvester([self.repo_dir], config)
        raw_results = raw_harvester.as_json()
        with open("data/results/tiny/test-radon-results-raw-metrics.json", 'w', encoding='utf-8') as f:
            f.write(raw_results)

        config.multi = True  # Count multiline strings as comment lines as well.
        mi_harvester = MIHarvester([self.repo_dir], config)
        mi_results = mi_harvester.as_json()
        with open("data/results/tiny/test-radon-results-mi.json", 'w', encoding='utf-8') as f:
            f.write(mi_results)

        config.by_function = False
        hc_harvester = HCHarvester([self.repo_dir], config)
        hc_results = hc_harvester.as_json()
        with open("data/results/tiny/test-radon-results-hc.json", 'w', encoding='utf-8') as f:
            f.write(hc_results)

        # TODO add metrics to metric_dict
        raise NotImplementedError

        return metric_dict

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
