# pydistrocomp
### Comparison of python distro packages

## What's this good for?
This small pure-python utility lets you **review and compare packages installed in your various python distros**. Let's say you have several 'real' distributions of Python (e.g. 3.5, 3.7 and 3.9) and a bunch of virtual environments. Now you'd like to know which packages are installed in each distro and compare their versions, also checking out the latest available version of each package and its description. 

With a few code lines `pydistrocomp` will help you generate a comparison table (pandas DataFrame) that you can export in a variety of formats. For example, you can get an HTML table that looks like this:

![](https://github.com/S0mbre/pydistrocomp/blob/main/screenshots/screen01.jpg)

Reviewing this table, you can easily see what packages are included in which distro (last two columns highlighted green), match against the newest version (column "latest") and check out the basic package info: name, authors, homepage and summary.

## Usage
See `pydistro.py` for examples in the `main()` function. 

You pass a list of python executables (for each distro you want to review / compare) to the `Pkgcomp` class constructor:
```python
envs = [None, # None = current environment (mine is 3.9.1)
        r'c:\WPy64-3950\python-3.9.5.amd64\python.exe' # other env (3.9.5)
        ]
```

Then create a `Pkgcomp` object passing this list:
```python
pk = Pkgcomp(envs, get_latest_vers=False, debug=True)
```
The `Pkgcomp` parameters are:
- `pyexes`: list of python executables or a dict in format `{'executable path': 'human label'}` (both path and label can be `None` or `0` to automatically guess the current environment and version number)
- `dbdir`: directory to store the package database (used for caching package info); default = project dir
- `use_procs`: whether to use multiple processes (default is `False`, meaning multiple threads)