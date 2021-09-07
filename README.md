

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
distros = Distros(envs, force_update=False)
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
`Distros` is a wrapper around a collection of python distributions, each represented by a `Distro` object. Once you've created a `Distros` object, you can access individual python distros (environments) in the usual pythonic way:
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

### `Distro` class: a single python distro
A `Distro` object, in its turn, is a collection of python packages 'on steroids'. It is derived from the `Packages` class that lets you access individual packages, reviews their data, iterate over them, and so on. Every `Distro` object has two main properties (strings): 
- `pyexe` -- full path to the `python` executable in a given distro
- `alias` -- alias (short name) for the distro, e.g. `3.9.5`

As mentioned, these two properties are given to the constructor as parameters, and either or both can be `None`: if `pyexe` is `None`, the current executable will be used; and if `alias` is `None` (or an empty string), the executable's version will be used as an auto label for the distro. 

When created, a `Distro` object will retrieve all the packages installed with that distro and store them in its `packages` collection. As it is, a `Distro` (or its parent class `Packages`) is itself a collection, and can be iterated and indexed to access individual packages:
```python
distros = Distros()

# get number of installed packages
print(f'Number of packages: {len(distros)}')

# iteration
for package in distros:
    print(package.name, package.version)
    
# indexing by package name
numpy_ = distros['numpy']

# indexing by index
pk = distros[-1]
```

### `Package`: an individual python package
Each package in a `Distro` or `Packages` object is an instance of `Package` containing the important package data:
- `name`
- `author`
- `summary`
- `homepage`
- `latest` version
- current `version`

This package information is retrieved from the package cache -- the `pypkg.json` file found in the project root. If this cache is missing, or it lacks data for that specific package, or if `force_update` is passed to the `Package` constructor, then information is fetched from the [PyPI index](https://pypi.org/). To speed up things, package objects are spawned by `Packages` with multithreading. 

A `Package` object also lets you perform the basic [pip operations](https://pip.pypa.io/en/stable/cli/):
- `install()`: install the package
- `uninstall()`: uninstall the package
- `check()`: check package integrity
- `show()`: return package information as text
- `required_by()`: list packages that depend on this package
- `requires()`: list packages that this package depends on

All these methods require passing the python executable path; if not passed (left `None`), the current executable is used.

A string representation of a `Package` gives its name and version, e.g. *"Babel [2.9.0]"*.

### Comparing packages in distros
One cool feature is set-like operations when comparing two or more distros:
```python
distros = Distros([None, r'c:\WPy64-3910\python-3.9.1.amd64\python.exe'])

# get unique and newer packages in current distro
unique_newer = distros[''] - distros['3.9.1']
print(str(unique_newer))

# get common packages between the two distros
common_packages = distros[''] & distros['3.9.1']

# get all packages in both distros (omitting duplicates)
all_packages = distros[''] | distros['3.9.1']

# get all packages in both distros (with duplicates -- different versions)
all_packages = distros[''] + distros['3.9.1']

# get symmetric difference (only unique packages from both distros)
unique_pks = distros[''] ^ distros['3.9.1']
```
All these operations return an instance of `Packages`. This means that you can chain set-like operations as you want and work with the resulting packages, e.g.:
```python
# make custom slice
pks = (distros[''] & distros['3.9.1']) - distros['3.5.1']
# see what's inside
print(pks)
# collect the versions of each package
versions = [pk.version for pk in pks]
```

### Installing and uninstalling
You can install or uninstall a collection of packages from a `Distro` or `Packages` object easily. Note, however, that to do so on a `Packages` object, you need to pass the python executable path, since `Packages` is unaware and independent of python distributions. 
```python
distros = Distros([None, r'c:\WPy64-3910\python-3.9.1.amd64\python.exe'])

# installing on a Distro object will upgrade all packages
on_install = lambda pk, stdout: print(f'{pk.name}: {stdout}')
distros[''].install(on_install=on_install)

# installing on a Packages object gives more flexibility
#   1. Install unique/newer packages from 3.9.1 into current distro
pks = distros['3.9.1'] - distros['']
pks.install(pyexe=distros[''].pyexe, upgrade=True, force_version=False, on_install=on_install)
#   2. Upgrade common packages
(distros['3.9.1'] & distros['']).install(pyexe=distros['3.9.1'].pyexe)
#   3. Force reinstall specific versions
pks = Packages([('pillow', '8.0.1'), ('pyyaml', '5.3.1')], 
               distros.package_cache, distros.force_update, distros.vcomp, distros.on_error)
pks.install(pyexe=distros['3.9.1'].pyexe, force_version=True, on_install=on_install)

# uninstalling from Distro
distros[''].uninstall(packages=['pypdf2', 'openpyxl', 'tabulate'], on_uninstall=on_install)
# uninstalling from Packages
(distros[''] - distros['3.9.1']).uninstall(pyexe=distros[''].pyexe, on_uninstall=on_install)
```

### Export functionality
You can easily export a `Distro` or `Packages` object into a variety of formats including the system clipboard.
```python
distros = Distros()
distro = distros[0] # current python distro

# >> Pandas dataframe
df = distro.asdataframe()
# >> Excel workbook
distro.to_xl('pk.xlsx', df=df)
# >> CSV (comma-separated values)
distro.to_csv('pk.csv', df=df)
# >> JSON (with pretty printing)
distro.to_json('pk.json', df=df)
# >> HTML
distro.to_html('pk.html', df=df)
# >> pickle (python object)
distro.to_pickle('pk.gz', df=df)

# simple string convertion (native Pandas)
print(distro.to_string(df=df))
# pretty string (with tabulate)
print(distro.to_stringx(df=df, tablefmt='fancy_grid', 
                        maxwidth=200, filepath='pk.txt')) # also saved text file

# copy to clipboard (in Excel-supported format)
distro.to_clipboard('pk.gz', df=df, excel=True)
```
Export also works from a `Distros` object, in which case the resulting table contains the package versions for all the distros. 
> The `to_xl()` method on `Distros` outputs the comparison table also highlighting the missing and latest packages in each environment.

## Global parameters in `pydistro.py`:
You can change some globals in `pydistro.py` to tweak the program behavior:
- `DEBUG`: whether to output debug messages to the console (`STDOUT`) to track the execution progress; default = `False`
- `WORKERS`: max number of threads to execute for concurrent operations (default = `10`)
- `TIMEOUT`: timeout in seconds for a single HTTP request to PyPI (during database updates); default = `5` seconds
- `REQUEST_ARGS`: dictionary containing additional parameters passed to `requests.get()` (such as HTTP proxy etc.); by default, this is an empty dict (no extra parameters)
- `VERS_LEVEL`: level of versions strings to compare (see `vcomp_or_level` parameter description in `Distros`)
- `MULTI_EXECUTOR_CLASS`: concurrent executor class (not configurable)

## To-Do List
- view package dependency trees (via [`pipdeptree`](https://github.com/naiquevin/pipdeptree))
