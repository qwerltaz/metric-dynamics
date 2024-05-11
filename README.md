# metric-dynamics
Compute common software metrics for every commit in a list of repositories. 
Results are saved in `data/results`.


## Usage
To compute metrics for a list of repositories from the default list:
```bash
py schedule.py --urls-path=data/url/pypi_top_1000.csv
```
The `.csv` file should contain a column of GitHub repository URLs.
