
# Getitng started

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
