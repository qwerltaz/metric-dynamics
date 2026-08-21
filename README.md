# metric-dynamics
Compute common software metrics for every commit in a list of repositories. 
Results are saved in `data/results`.


## Usage
To compute metrics for a list of repositories from the default list:
```bash
py schedule.py --urls-path=data/url/pypi_top_1000.csv
```
The `.csv` file should contain a column of GitHub repository URLs.

## Results
The figure below shows the size of Python repositories in lines of code (LOC) and its relation to common software metrics. Almost all growing projects either put emphasis on maintenance and decrease the software metrics, or have project complexity grow extremely fast until the project becomes
unmaintainable and is abandoned. This results in the corner of the graphs where both the metric and LOC are high being empty, signifying that there are no projects that grow big while managing to not care about code maintainability.
<img width="953" height="1365" alt="25-12-24_676_msedge" src="https://github.com/user-attachments/assets/1c466060-efd7-486e-9f08-314f3badf672" />
