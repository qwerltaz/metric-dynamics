# metric-dynamics
Compute common software metrics for every commit in a list of repositories. 
Results are saved in `data/results`.


## Usage
To compute metrics for a list of repositories from the default list:
```bash
py schedule.py --urls-path=data/url/pypi_top_1000.csv
```
The `.csv` file should contain a column of GitHub repository URLs.

## tl;dr
Size of Python repositories in lines of code (LOC) and its relation to common software metrics:
<img width="953" height="1365" alt="25-12-24_676_msedge" src="https://github.com/user-attachments/assets/1c466060-efd7-486e-9f08-314f3badf672" />
