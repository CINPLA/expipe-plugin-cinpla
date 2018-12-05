
# Getting started

- make a github user [github](https://github.com/)
- download and install [Anaconda](https://www.anaconda.com/download/) version 3.7, command line version
- download and install [github desktop](https://desktop.github.com/)
- (optional) download and install [atom](https://atom.io/)

## Installation

Set up access to Norstore first:

- [Setup Norstore](https://github.com/CINPLA/expipe/wiki/Setup-Norstore)

Then follow the installation instructions for your operating system:

- [Installation on Linux](https://github.com/CINPLA/expipe/wiki/Installation-on-Linux)
- [Installation on Windows](https://github.com/CINPLA/expipe/wiki/Installation-on-Windows)

## Documentation

(old)
See the [wiki](https://github.com/CINPLA/expipe-plugin-cinpla/wiki/) or the [documentation](http://expipe-plugin-cinpla.readthedocs.io/en/latest/) 
for more information on how to use expipe.

(new)
### Clone cinpla-base

First we need to clone the cinpla-base repository.
Open Github Desktop, hit Clone Repository --> URL --> paste `https://github.com/CINPLA/cinpla-base` and choose the folder in which you want to save this repository (you will need it later).
It is reccommended to create a new folder called `apps` in your local disk (not kant!).

### Get Anaconda ready

Open the Anaconda prompt and navigate to the cinpla-base folder (`cd path-to-cinpla-base` - e.g. `cd C:\\apps\cinpla-base`)

Now we need to create a new anaconda environment:

``` 
conda create -n expipe python=3.5
source activate expipe
```

If you plan to use electrophysiology and spike sorting also run this:

```
conda install pyqt=4
```

Then we can get all the python packages needed by:

```
pip install -r requirements.txt
```

Now run expipe:
```
expipe
```

(in Windows, if it fails, run:
```
pip uninstall numpy
pip install numpy
```
and try again!)

### Clone the templates

Templates are used to create modules in expipe actions. Use github desktop to clone https://github.com/CINPLA/expipe-templates-cinpla.git.
This is a collection of templates used by the group that can be loaded into each project's templates folder.

### Create a project

The project will contain the data and relative information. You can make a folder called `data` or `projects`, for example, and create you projects there.

First change directory to your projects directory
```
cd path-to-data (or path-to-projects)
```

Then create a new project:
```
expipe create project_name
```

Now we can interact with the project by running:
```
jupyter notebook
```

This will open a browser window (e.g. in Chrome). To create a new notebook (used to write and run code) press `New`-->`Python 3`. This will create an ipython notebook file (`.ipynb`).

In the first cell type and import the expipe packages:
```
from expipe_plugin_cinpla.widgets import browser
import expipe
```

In the second cell type:
```
browser.display('project_name')
```

This will display an interactive widget to register actions (such as surgery, adjustment, perfusion, recordings, analysis), entities (such as animals) and process them, and saving them in `exdir` format.


