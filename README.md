
# Expipe plugin CINPLA

Expipe plugin for the CINPLA laboratory.


## Installation

`expipe-plugin-cinpla` can be installed by running

        $ pip install expipe-plugin-cinpla

It requires Python 3.10+ to run.

If you want the latest features and can't wait for the next release, install from GitHub:

        $ pip install git+https://github.com/CINPLA/expipe-plugin-cinpla.git


## Usage

The starting point is a valid `expipe` project. Refer to the [expipe docs](https://expipe.readthedocs.io/en/latest/) to read more on how to create one.

The recommended usage is via Jupyter Notebook / Lab, using the interactive widgets to Register, Process,
Curate, and View your actions.

To launch the interactive browser, you can run:

```python
from expipe_plugin_cinpla import display_browser

project_path = "path-to-my-project"

display_browser(project_path)
```

![alt text](docs/images/browser.png)


## Updating old projects

The current version uses Neurodata Without Borders as backend instead of Exdir. If you have an existing
project created with the old version, you can convert it to a new project as follows:

```python
from expipe_plugin_cinpla import convert_old_project

old_project_path = "path-to-old-project"
new_project_path = "path-to-new-project"

probe_path = "path-to-probe-path.json" # see probes/ folder

convert_old_project(old_project_path, new_project_path, probe_path)
```

To check out other options, use `convert_old_project?`


## How to contribute

### Set up development environment

First, we recommend to create a virtual environment and install `pip`;

* Using [venv](https://packaging.python.org/en/latest/key_projects/#venv):

        $ python3.11 -m venv <env_name>
        $ source <env_name>/bin/activate
        $ python3 -m pip install --upgrade pip

* Using [conda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html):

        $ conda create -n <env_name> python=3.11 pip
        $ conda activate <env_name>

Then install `expipe-plugin-cinpla` in editable mode from source:

        $ git clone https://github.com/CINPLA/expipe-plugin-cinpla.git
        $ cd expipe_plugin_cinpla
        $ python3 -m pip install -e ".[full]"


### pre-commit
We use [pre-commit](https://pre-commit.com/) to run Git hooks on every commit to identify simple issues such as trailing whitespace or not complying with the required formatting. Our pre-commit configuration is specified in the `.pre-commit-config.yml` file.

To set up the Git hook scripts specified in `.pre-commit-config.yml`, run

    $ pre-commit install

> **NOTE:**  If `pre-commit` identifies formatting issues in the commited code, the pre-commit Git hooks will reformat the code. If code is reformatted, it will show up in your unstaged changes. Stage them and recommit to successfully commit your changes.

It is also possible to run the pre-commit hooks without attempting a commit:

    $ pre-commit run --all-files
