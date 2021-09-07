

# pydistrocomp
### Comparison of python distro packages

## What's this good for?
This small pure-python utility lets you **review and compare packages installed in your various python distros**. Let's say you have several 'real' distributions of Python (e.g. 3.5, 3.7 and 3.9) and a bunch of virtual environments. Now you'd like to know which packages are installed in each distro and compare their versions, also checking out the latest available version of each package and its description. 

With a few code lines `pydistrocomp` will help you generate a comparison table (pandas DataFrame) that you can export in a variety of formats. For example, you can get an HTML table that looks like this:

![](https://github.com/S0mbre/pydistrocomp/blob/main/screenshots/screen01.jpg)

Reviewing this table, you can easily see what packages are included in which distro (last two columns highlighted green), match against the newest version (column "latest") and check out the basic package info: name, authors, homepage and summary.

An even better effect is achieved in an Excel report:

![](https://github.com/S0mbre/pydistrocomp/blob/main/screenshots/screen02.jpg)

## Usage
Clone the project and install the few required packages:
```bash
git clone https://github.com/S0mbre/pydistrocomp.git
cd pydistrocomp
python -m pip install -r requirements.txt
```

You can also run the code online (without downloading or installing anything) on Binder using this link: https://mybinder.org/v2/gh/S0mbre/pydistrocomp/main.
- Follow the URL to open Binder and wait for the server to start
- Open the `playground.ipynb` Jupyter notebook and run it

See `pdcomp.py` for examples. 

You pass a list of python executables (for each distro you want to review / compare) to the `Pkgcomp` class constructor:
```python
envs = [None, # None = current environment (mine is 3.9.1)
        r'c:\WPy64-3950\python-3.9.5.amd64\python.exe' # other env (3.9.5)
        ]
```

Then create a `Distros` object passing this list:
```python
pk = Distros(envs, force_update=False)
```

### `Distros` parameters
The `Distros` parameters are:
- `pyexes`: list of python executables or a dict in format `{'executable path': 'human label'}` (both path and label can be `None` or `0` to automatically guess the current environment and version number)
> The simplest case is just a list of python executables, e.g.:
> ```python
> envs = [r'c:\py37\python-3.7.5.amd64\python.exe', 
>         r'c:\py39\python-3.9.5.amd64\python.exe']
> ```
> As mentioned, the list can also include `None` or an empty string (or just any falsy object) to tell the app to take the current executable (from `sys.executable`). By default, the list is empty (meaning that only the current executable will be analyzed). So to get the packages in your current python you can do just this:
> ```python
> df = Distros().asdataframe()
> ```
> The other option is a dictionary with python executables as keys and labels as values, e.g.:
> ```python
> envs = {r'c:\py37\python-3.7.5.amd64\python.exe': 'py37',
>         r'c:\py39\python-3.9.5.amd64\python.exe': 'latest_python'}
> ```
> This option is available if you don't want to rely on automatic labeling. To analyze the current python distro, you can also pass a falsy object here, e.g. `[(None, 'my-python')]` (to use a custom label) or just `None` (to use automatic labeling).
- `dbdir`: directory to store the package database (used for caching package info); default = current project path
- `save_on_exit`: whether to save the database automatically when the app exits (in the class destructor); default = `True`
- `append_to_current`: custom postfix to mark the current python environment, if present (default = `'(CURRENT)'`
- `force_update`: whether to update package data from PyPI forcefully; default = `False`
> Setting this parameter to `True` will dramatically increase execution time. It is recommended to keep this set to `False` after the database is filled from the first launch.
- `vcomp_or_level`: integer or an instance of `VersionCompare` class used to compare package versions
> The `vcomp_or_level` parameter lets you decide on the criterion for comparing versions. The value of `2` (default) means that only the major and minor versions are considered (e.g. `0.1` from `0.1.5`).
> If you set this to `1`, only the first part of the version string (major version) will be considered. The value of `3` tells the app to consider the first 3 parts, and so on.
- `on_error`: custom exception handler (default = `print`)

### Indexing and iterating `Distros`
Once you've created a `Distros` object, you can access individual python distros (environments) in the usual pythonic way:
- get a distro by alias or executable path:
```python
d = distros['3.9.5']
# OR
d = distros[r'c:\WPy64-3950\python-3.9.5.amd64\python.exe']
# OR
d = distros[''] # << to get the current environment
```
- get a distro by index:
```python
d = distros[0]
```
- you can also use the `get()` method instead of the index operator:
```python
d1 = distros.get(0)
d2 = distros.get('3.9.5')
```
- iterate distros:
```python
for d in distros:
    print(d.pyexe, d.alias, len(d))
```
### Some global parameters in `pydistro.py`:
- `DEBUG`: whether to output debug messages to the console (`STDOUT`) to track the execution progress; default = `False`
- `WORKERS`: max number of threads to execute for concurrent operations (default = `10`)
- `TIMEOUT`: timeout in seconds for a single HTTP request to PyPI (during database updates); default = `5` seconds
- `REQUEST_ARGS`: dictionary containing additional parameters passed to `requests.get()` (such as HTTP proxy etc.); by default, this is an empty dict (no extra parameters)
- `VERS_LEVEL`: level of versions strings to compare (see above)
- `MULTI_EXECUTOR_CLASS`: concurrent executor class (not configurable)

## How To...
- export the comparison table to Excel:
```python
pk = Pkgcomp([None, r'c:\WPy64-3950\python-3.9.5.amd64\python.exe'])
pk.to_xl('pk.xlsx', version_compare_level=2)
```
> The inbuilt method `to_xl()` outputs the comparison table to a pretty Excel report, highlighting missing and latest packages in each environment.
> The `version_compare_level` parameter lets you decide on the criterion for highlighting later versions. The value of `2` (default) means that only the major and minor versions are considered (e.g. `0.1` from `0.1.5`).
> If you set this to `1`, only the first part of the version string (major version) will be considered. The value of `3` tells the app to consider the first 3 parts, and so on.

- export to various formats:
```python
pk = Pkgcomp([None, r'c:\WPy64-3950\python-3.9.5.amd64\python.exe'])
df = pk()

# >> CSV (comma-separated values):
pk.to_csv('pk.csv', df=df)
# >> JSON (with pretty printing):
pk.to_json('pk.json', df=df)
# >> HTML
pk.to_html('pk.html', df=df)
# >> pickle (python object)
pk.to_pickle('pk.gz', df=df)
```

- convert to string:
```python
pk = Pkgcomp([None, r'c:\WPy64-3950\python-3.9.5.amd64\python.exe'])
df = pk()

# simple string convertion (native Pandas):
print(pk.to_string(df=df))
# pretty string (with tabulate):
print(pk.to_stringx(df=df, tablefmt='fancy_grid', maxwidth=200, filepath='pk.txt')) # also saved string to a text file
```

## To-Do List
- generate `requirements.txt` or a similar list of packages required for installation based on a selected distro
- automatic installation of missing / required packages from one distro to another, e.g. 
`pk.install('3.7 > 3.9', latest=True)`
- view package dependency trees (via [`pipdeptree`](https://github.com/naiquevin/pipdeptree))
