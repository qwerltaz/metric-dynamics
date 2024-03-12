import os

import git
import pandas as pd
from pydriller import Repository, Commit

DATA_DIR = "data"


class MetricParse:
    """Parse metrics from a git repository."""

    def __init__(self, repo_url: str):
        """
        Initialize metric parser with repository url.

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
        ).traverse_commits()

        sloc = 0  # Source lines of code.
        all_lines = 0  # All additions and deletions combined.
        for i, commit in enumerate(traverser):
            sloc = sloc + commit.insertions - commit.deletions
            all_lines = all_lines + commit.lines

            print(
                'commit', i + 1, 'of', commit_count,
                '| author:', commit.author.name,
                '| date:', commit.committer_date,
                '| lines: ', f'{commit.lines} (+{commit.insertions} -{commit.deletions} )',
            )

            commit_metric_dict = {
                "hash": commit.hash,
                "author": commit.author.name,
                "date": commit.committer_date,
                "commit_message": commit.msg,
                "is_merge": commit.merge,
                "codebase_size": sloc,
                "lines": commit.lines,
                "all_lines": all_lines,
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
        metric_dict = dict()

        return metric_dict

    @property
    def main_branch(self):
        """Main or master branch."""

        candidates = ["main", "master", "origin/main", "origin/master"]
        refs = self.repo.references
        for candidate in candidates:
            if candidate in refs:
                return candidate

        raise Exception(f"Main branch not in {self.repo_url}.")


mp = MetricParse("https://github.com/areski/python-nvd3")
# mp = MetricParse("https://github.com/daimajia/bleed-baidu-white")
mp.save_metrics_for_each_commit()
