# -*- coding: utf-8 -*-
import requests, sys, os, json
import subprocess as sp
import concurrent.futures
import pandas as pd
from openpyxl import load_workbook, worksheet, styles
import packaging.version as pkvers
from tabulate import tabulate
from utils import Utils

## ---------------------------------------------------------------------------------------------- ##

DEBUG = False

NL = '\n'
WORKERS = 10
TIMEOUT = 4
REQUEST_ARGS = {}
VERS_LEVEL = 2
PACKAGES = {}
MULTI_USE_PROCS = False
MULTI_EXECUTOR_CLASS = concurrent.futures.ProcessPoolExecutor if MULTI_USE_PROCS else concurrent.futures.ThreadPoolExecutor

## ---------------------------------------------------------------------------------------------- ##

class VersionCompare:

    def __init__(self, level=VERS_LEVEL):
        self.level = level

    def get_version(self, version_str):
        version_str = version_str.strip() if version_str else ''
        if not version_str: return pkvers.Version('0')
        parts = version_str.split('.')
        if len(parts) > self.level:
            return pkvers.Version('.'.join(parts[:self.level])) 
        return pkvers.Version(version_str)

    def compare_binary(self, pk1, pk2, comp='<'):
        v_1 = self.get_version(pk1)
        v_2 = self.get_version(pk2)
        if comp=='<':
            return v_1 < v_2
        if comp=='>':
            return v_1 > v_2
        if comp=='==':
            return v_1 == v_2
        if comp=='<=':
            return v_1 <= v_2
        if comp=='>=':
            return v_1 >= v_2
        raise Exception(f'Wrong operator: {comp}')

    def is_equal(self, pk1, pk2):
        return self.compare_binary(pk1, pk2, '==')

    def sort_versions(self, versions):
        vv = list(enumerate([self.get_version(v) for v in versions]))
        values = set(map(lambda x: x[1], vv))
        newlist = sorted([[y for y in vv if y[1]==x] for x in values], key=lambda e: e[0][1])
        return [tuple(x[0] for x in e) if len(e) > 1 else e[0][0] for e in newlist]

## ---------------------------------------------------------------------------------------------- ##
class Package:

    prop_names = ['name', 'author', 'summary', 'homepage', 'latest']

    def __init__(self, pk, version=None, force_update=False, vcomp_or_level=VERS_LEVEL, on_error=None, no_update_global=False):
        self.vcomp = vcomp_or_level if isinstance(vcomp_or_level, VersionCompare) else VersionCompare(vcomp_or_level)
        self._version = ''
        self.normalized_version = ''
        if not isinstance(pk, Package):
            self._pkname = pk.lower()
            self.version = version
        else:
            self._pkname = pk.name
            self.version = pk.version
        self.on_error = on_error
        self.force_update = force_update
        self.no_update_global = no_update_global        
        self.update_properties(pk.asdict(False) if isinstance(pk, Package) else None)

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        self._version = value
        self.normalized_version = str(self.vcomp.get_version(value))

    def _properties_set(self):
        return all(p in self.__dict__ for p in Package.prop_names)

    def _get_pkg_info(self):
        try:
            res = requests.get('https://pypi.org/pypi/{}/json'.format(self._pkname), 
                            headers={'Accept': 'application/json'}, timeout=TIMEOUT, **REQUEST_ARGS)
            if res.status_code != 200: 
                raise Exception(f'HTTP Error {res.status_code}!{NL}{res.text}')
            resjs = json.loads(res.content)
            return resjs['info']

        except Exception as err:
            if self.on_error: 
                self.on_error(err)
            else:
                raise

        return dict()

    def update_properties(self, pkinf=None):
        global PACKAGES
        if DEBUG: print(f'UPDATING DATA FOR PACKAGE "{self._pkname}" ...')
        pkinf = pkinf or PACKAGES.get(self._pkname, None)
        if self.force_update or pkinf is None:
            if DEBUG: print(f'  GETTING DATA FROM PYPI FOR PACKAGE "{self._pkname}" ...')
            pkinf = self._get_pkg_info()
            if DEBUG: print(f'  PYPI DATA FETCHED')
        if not pkinf:
            if self.on_error: 
                self.on_error(f'Package {self._pkname} not found on PyPI!')
            else:
                raise Exception(f'Package {self._pkname} not found on PyPI!')

        inf = {'name': pkinf.get('name', self._pkname), 'author': pkinf.get('author', ''),
               'summary': pkinf.get('summary', ''), 'latest': pkinf.get('version', ''),
               'homepage': pkinf.get('home_page', pkinf.get('project_url', pkinf.get('package_url', '')))}
        self.__dict__.update(inf)
        if not self.no_update_global:
            PACKAGES.update({self._pkname: inf})
        if DEBUG: print(f'DATA UPDATED')

    def asdict(self, name_as_key=True):
        if not self._properties_set():
            self.update_properties()
        inf = {k: v for k, v in self.__dict__.items() if k=='version' or k in Package.prop_names}
        return {self._pkname: inf} if name_as_key else inf

    def is_outdated(self):
        return self.vcomp.compare_binary(self._version, getattr(self, 'latest', ''))

    def install(self, pyexe=None, upgrade=True, force_version=None):
        args = ['install']
        if upgrade:
            args.append('--upgrade')
        if force_version:
            args.append('--force-reinstall')
            args.append(f'{self._pkname}=={force_version}')
        else:
            args.append(self._pkname)
        return Utils.pip(args, None, pyexe, self.on_error)

    def uninstall(self, pyexe=None):
        return Utils.pip(['uninstall', '--yes'], self._pkname, pyexe, self.on_error)

    def __str__(self):
        return f'Package {self._pkname}{" [" + self.version + "]" if self.version else ""}'

    def __repr__(self):
        return str(self.asdict())

    def __hash__(self):
        return hash((self._pkname, self.normalized_version or ''))

## ---------------------------------------------------------------------------------------------- ##

class Packages:

    def __init__(self, packages=None, force_update=False, vcomp_or_level=VERS_LEVEL, on_error=None):
        full_packages = packages and isinstance(packages[0], Package)
        if full_packages:
            self._pknames = [pk.name for pk in packages]
            self.packages = packages.copy()
        else:
            self._pknames = packages or list(PACKAGES.keys())
            self.packages = []
        self.on_error = on_error
        self.force_update = force_update
        self.vcomp = vcomp_or_level if isinstance(vcomp_or_level, VersionCompare) else VersionCompare(vcomp_or_level)
        self._it = None
        if not full_packages:
            self._collect_packages()

    def _collect_packages(self):
        if not self._pknames:
            return 
        self.packages.clear()
        has_versions = Utils.is_iterable(self._pknames[0])

        def worker(pkname, version):
            pk = Package(pkname, version, force_update=self.force_update, vcomp_or_level=self.vcomp, on_error=self.on_error)
            self.packages.append(pk)
        
        with MULTI_EXECUTOR_CLASS(max_workers=WORKERS) as executor:
            futures = {executor.submit(worker, pkname, version): pkname for pkname, version in self._pknames} if has_versions else \
                      {executor.submit(worker, pkname, None): pkname for pkname in self._pknames} 
            for future in concurrent.futures.as_completed(futures):
                pkname = futures[future]
                try:
                    future.result()
                except Exception as err:
                    if self.on_error: 
                        self.on_error(f'{pkname}: {str(err)}')

    def get(self, pkname):
        for pk in self.packages:
            if pk.name == pkname:
                return pk
        return None

    def asdict(self):
        return {pk.asdict() for pk in self.packages}

    def asdataframe(self):
        pkdict = self.asdict()
        if pkdict:
            df = pd.DataFrame.from_dict(pkdict, orient='index')
            return df.reindex(sorted(df.index, key=lambda x: x.lower()))
        return None

    def _get_merged(self, other, op='+'):
        if op=='+':            
            ps = []
            for pk1 in self.packages:
                for pk2 in other.packages:
                    if pk2.name == pk1.name and pk2.version == pk1.version:
                        break
                else:
                    ps.append(pk1)
            return ps

        elif op=='-':
            return list(set(self.packages) - set(other.packages))

        elif op=='&':
            return list(set(self.packages) & set(other.packages))

        elif op=='|':
            return list(set(self.packages) | set(other.packages))

        elif op=='^':
            return list(set(self.packages) ^ set(other.packages))

        else:
            raise Exception(f'Wrong operator: {op}')


    def _concat_from(self, other, op='+'):
        return Packages(self._get_merged(other, op), self.force_update, self.vcomp, self.on_error)

    def get_fullunion(self, other):
        return self._concat_from(other, '+')
      
    def update_fullunion(self, other):
        self.packages = self.get_fullunion(other)
        self._pknames = [pk.name for pk in self.packages]
        return self

    def get_union(self, other):
        return self._concat_from(other, '|')
      
    def update_union(self, other):
        self.packages = self.get_union(other)
        self._pknames = [pk.name for pk in self.packages]
        return self

    def get_intersection(self, other):
        return self._concat_from(other, '&')

    def update_intersection(self, other):
        self.packages = self.get_intersection(other)
        self._pknames = [pk.name for pk in self.packages]
        return self

    def get_difference(self, other):
        return self._concat_from(other, '-')

    def update_difference(self, other):
        self.packages = self.get_difference(other)
        self._pknames = [pk.name for pk in self.packages]
        return self

    def get_symmetric_difference(self, other):
        return self._concat_from(other, '^')

    def update_symmetric_difference(self, other):
        self.packages = self.get_symmetric_difference(other)
        self._pknames = [pk.name for pk in self.packages]
        return self

    def list_outdated(self):
        return (pk for pk in self.packages if pk.is_outdated(self.vcomp))

    def list_uptodate(self):
        return (pk for pk in self.packages if not pk.is_outdated(self.vcomp))

    def install(self, packages=None, pyexe=None, upgrade=True, force_version=False, on_install=None):
        packages = packages or self.packages
        if not packages: return
        for pk in packages:
            res = pk.install(pyexe, upgrade, pk.version if force_version and pk.version else None)
            if not res.returncode and on_install:
                on_install(pk, res.stdout)

    def __repr__(self):
        return str(self.asdict())

    def __str__(self):
        return '\n'.join(str(pk) for pk in self.packages) if self.packages else 'No packages'

    def __getitem__(self, key):
        pk = self.get(key)
        if pk is None:
            raise IndexError
        return pk

    def __len__(self):
        return len(self.packages)

    def __iter__(self):
        self._it = iter(self.packages)
        return self._it

    def __next__(self):
        return next(self._it)

    def __or__(self, other):
        return self.get_union(other)

    def __ior__(self, other):
        return self.update_union(other)

    def __add__(self, other):
        return self.get_fullunion(other)

    def __iadd__(self, other):
        return self.update_fullunion(other)

    def __sub__(self, other):
        return self.get_difference(other)

    def __isub__(self, other):
        return self.update_difference(other)

    def __and__(self, other):
        return self.get_intersection(other)

    def __iand__(self, other):
        return self.update_intersection(other)

    def __xor__(self, other):
        return self.get_symmetric_difference(other)

    def __ixor__(self, other):
        return self.update_symmetric_difference(other)
        
## ---------------------------------------------------------------------------------------------- ##

class Distro(Packages):

    def __init__(self, pyexe=None, alias=None, force_update=False, vcomp_or_level=VERS_LEVEL, on_error=None):
        self.pyexe = os.path.abspath(pyexe) or sys.executable
        self.alias = alias or f'{self._get_env_version()} (CURRENT)'
        self.on_error = on_error
        super().__init__(self._list_env_packages(), force_update, vcomp_or_level, on_error)
        if not getattr(self, 'packages', None):
            raise Exception(f'Unable to get packages from environment "{self.pyexe}"!')

    def install(self, on_install=None):
        if not getattr(self, 'packages', None): return
        super().install(pyexe=self.pyexe, upgrade=True, on_install=on_install)

    def asdataframe(self):
        return super().asdataframe().rename(columns={'version': self.alias})

    def _list_env_packages(self):
        return [tuple(s.strip().split('==')) for s in Utils.execute([self.pyexe, '-m', 'pip', 'list', '--format', 'freeze']).split('\n') if s]

    def _get_env_version(self):
        try:
            return Utils.execute([self.pyexe, '-V']).split(' ')[-1].strip()
        except:
            return None

    def __hash__(self):
        return hash((self.pyexe, self.alias))

    def __str__(self):
        return f'{self.alias} ("{self.pyexe}""):{NL}{super().__str__()}'

## ---------------------------------------------------------------------------------------------- ##

class Distros:

    def __init__(self, pyexes=None, dbdir=None, save_on_exit=True, force_update=False, vcomp_or_level=VERS_LEVEL, on_error=None):
        self.force_update = force_update
        self.vcomp = vcomp_or_level if isinstance(vcomp_or_level, VersionCompare) else VersionCompare(vcomp_or_level)
        self.on_error = on_error
        self.distros = []
        self._has_updated = False
        self.save_on_exit = save_on_exit
        self.dbdir = dbdir or os.path.dirname(os.path.realpath(__file__))
        self.dbfile = os.path.join(self.dbdir, 'pypkg.json')
        self.load_db()
        if pyexes:
            if Utils.is_iterable(pyexes):
                if isinstance(pyexes, dict):
                    pyexes = pyexes.copy()
                else:
                    pyexes = {p[0]: p[1] for p in pyexes} if Utils.is_iterable(pyexes[0]) else {p: None for p in pyexes}
            else:
                pyexes = {pyexes: None}
            self._list_envs(pyexes)
        else:
            self.distros = [Distro(force_update=self.force_update, vcomp_or_level=self.vcomp, on_error=self.on_error)]

    def __del__(self):
        if not MULTI_USE_PROCS and self._has_updated and self.save_on_exit:
            self.save_db()

    def list_distros(self, asdict=True):
        if not self.distros: return None
        return {d.pyexe: d.alias for d in self.distros} if asdict else [(d.pyexe, d.alias) for d in self.distros]

    def get(self, pyexe):
        for d in self.distros:
            if d.pyexe.lower() == pyexe or d.alias == pyexe:
                return d
        return None

    def load_db(self, filepath=None):
        global PACKAGES     
        if filepath:
            self.dbfile = os.path.abspath(filepath)
            self.dbdir = os.path.dirname(self.dbfile)
        if DEBUG: print(f'LOADING DB FROM "{self.dbfile}" ...')
        PACKAGES = {}
        self._has_updated = False
        if os.path.isfile(self.dbfile):
            PACKAGES = json.load(open(self.dbfile, 'r', encoding='utf-8'))
            if DEBUG: print(f'LOADED {len(PACKAGES)} PACKAGE DEFS')
        elif DEBUG: 
            print('NO DB FILE FOUND! (WILL CREATE NEW ON EXIT)')

    def save_db(self, filepath=None):
        if filepath:
            if self.dbfile != filepath:
                self._has_updated = True
            self.dbfile = os.path.abspath(filepath)
            self.dbdir = os.path.dirname(self.dbfile)
        if not self._has_updated: return
        if DEBUG: print(f'SAVING DB TO "{self.dbfile}" ...')
        if PACKAGES:
            with open(self.dbfile, 'w', encoding='utf-8') as jsfile:
                json.dump(PACKAGES, jsfile, ensure_ascii=False, indent=2)
            if DEBUG: print(f'SAVED {len(PACKAGES)} PACKAGE DEFS')
        elif DEBUG: 
            print('NO PACKAGE DEFS, NO DB CREATED!')

    def asdataframe(self):
        pass

    def _list_envs(self, pyexes, on_distro=None):
        def worker(pyexe):
            if isinstance(pyexe, tuple):
                distro = Distro(pyexe[0], pyexe[1], self.force_update, self.vcomp, self.on_error)
            else:
                distro = Distro(pyexe, None, self.force_update, self.vcomp, self.on_error)
            self.distros.append(distro)
            return distro
        
        with MULTI_EXECUTOR_CLASS(max_workers=WORKERS) as executor:
            futures = {executor.submit(worker, *pyexe): pyexe for pyexe in pyexes}
            for future in concurrent.futures.as_completed(futures):
                pyexe, alias = futures[future]
                try:
                    distro = future.result()
                    if on_distro:
                        on_distro(self, distro)

                except Exception as err:
                    if self.on_error: 
                        self.on_error(f'Error retrieving env "{alias}"" ("{pyexe}""): {str(err)}')

    def __getitem__(self, key):
        d = self.get(key)
        if d is None:
            raise IndexError
        return d

    def __str__(self):
        return '\n\n'.join(str(d) for d in self.distros)

## ---------------------------------------------------------------------------------------------- ##
class Pkgcomp:

    def __init__(self, pyexes=None, dbdir=None, use_procs=False, max_workers=WORKERS, 
                 get_latest_vers=True, timeout=TIMEOUT, save_on_exist=True, version_labels=True,
                 debug=False, request_args={}):
        self.pyexes = pyexes or [sys.executable]
        self.dbdir = dbdir or os.path.dirname(os.path.realpath(__file__))
        self.dbfile = os.path.join(self.dbdir, 'pypkg.json')
        self.max_workers = max_workers
        self.get_latest_vers = get_latest_vers
        self.timeout = timeout
        self.request_args = request_args
        self.use_procs = use_procs
        self.save_on_exist = save_on_exist
        self.version_labels = version_labels
        self.debug = debug
        self._has_updated = False
        self.load_db()

    def __del__(self):
        if self._has_updated and self.save_on_exist and not self.use_procs:
            self.save_db()

    def load_db(self, filepath=None):        
        if filepath:
            self.dbfile = os.path.abspath(filepath)
            self.dbdir = os.path.dirname(self.dbfile)
        if self.debug: print(f'LOADING DB FROM "{self.dbfile}" ...')
        self._pkdict = {}
        self._has_updated = False
        if os.path.isfile(self.dbfile):
            self._pkdict = json.load(open(self.dbfile, 'r', encoding='utf-8'))
            if self.debug: print(f'LOADED {len(self._pkdict)} PACKAGE DEFS')
        elif self.debug: 
            print('NO DB FILE FOUND! (WILL CREATE NEW ON EXIT)')

    def save_db(self, filepath=None):
        if filepath:
            if self.dbfile != filepath:
                self._has_updated = True
            self.dbfile = os.path.abspath(filepath)
            self.dbdir = os.path.dirname(self.dbfile)
        if not self._has_updated: return
        if self.debug: print(f'SAVING DB TO "{self.dbfile}" ...')
        if self._pkdict:
            with open(self.dbfile, 'w', encoding='utf-8') as jsfile:
                json.dump(self._pkdict, jsfile, ensure_ascii=False, indent=2)
            if self.debug: print(f'SAVED {len(self._pkdict)} PACKAGE DEFS')
        elif self.debug: 
            print('NO PACKAGE DEFS, NO DB CREATED!')

    def get_pkg_info(self, pkname, on_error=None):
        try:
            res = requests.get('https://pypi.org/pypi/{}/json'.format(pkname), 
                            headers={'Accept': 'application/json'}, timeout=self.timeout, **self.request_args)
            if res.status_code != 200: 
                raise Exception(f'HTTP Error {res.status_code}!{NL}{res.text}')
            resjs = json.loads(res.content)
            return resjs['info']

        except Exception as err:
            if on_error: 
                on_error(err)
            else:
                raise

        return dict()

    def list_packages_env(self, pyexe=None):
        pyexe = pyexe or sys.executable
        return [tuple(s.strip().split('==')) for s in sp.check_output([pyexe, '-m', 'pip', 'list', '--format', 'freeze'], encoding='utf-8').split('\n') if s]

    def update_db(self, pknames=None, update_existing=True, savedb=True):
        def on_info(pkname, pkinf):
            inf = {'name': pkinf.get('name', pkname), 'author': pkinf.get('author', ''),
                   'summary': pkinf.get('summary', ''), 'latest': pkinf.get('version', ''),
                   'homepage': pkinf.get('home_page', pkinf.get('project_url', pkinf.get('package_url', '')))}
            self._pkdict.update({pkname: inf})
            if self.debug: print(f'>>> UPDATED PK: {pkname}')  

        if self._pkdict:
            if update_existing:
                # if update_existing, update existing package info
                if not pknames: pknames = list(self._pkdict.keys())
            elif pknames:
                # otherwise, exclude existing packages
                pknames = list(set(pknames) - set(list(self._pkdict.keys())))
        if pknames:
            if self.debug: print(f'{NL}UPDATING DB WITH {len(pknames)} PACKAGES ...')
            self._get_pkg_info_multi(pknames, on_info=on_info, on_error=(lambda pkname, exc: print(f'~~~ ERROR UPDATING "{pkname}": {str(exc)}')))
            self._has_updated = True
            if self.debug: print('DB UPDATED')
            if savedb: self.save_db()

    def compare_env(self, pyexes=None):
        pyexes = pyexes or self.pyexes
        if not pyexes:
            if self.debug: print('~~~ NO ENVS TO ANALYZE!')
            return None
        if not isinstance(pyexes, dict) and not Utils.is_iterable(pyexes):
            pyexes = [pyexes]
        packages, pknames = self._collect_env_packages(pyexes)
        if not pknames:
            if self.debug: print('~~~ NO PACKAGES RETRIEVED!')
            return None
        self.update_db(pknames, self.get_latest_vers)
        df = self._db2pd()
        for env, data in packages.items():
            df[env] = pd.Series(data, index=df.index)
        df.dropna(how='all', subset=list(packages.keys()), inplace=True)
        df.fillna('', inplace=True)
        return df

    def to_xl(self, filepath='pk.xlsx', pyexes=None, df=None, version_compare_level=2):
        df = df if not df is None else self.compare_env(pyexes)
        ROWS = len(df) + 1
        COLS = len(df.columns) + 1
        try:
            if self.debug: print(f'OUTPUTTING TO EXCEL ("{filepath}") ...')
            df.to_excel(filepath, index_label='packages')
            wb = load_workbook(filename=filepath)
            ws = wb.active

            # align first column left
            for col in ws.iter_cols(max_col=1, min_row=2, max_row=ROWS):
                for cell in col:
                    cell.alignment = styles.Alignment(horizontal='left')

            # format as table
            tab = worksheet.table.Table(displayName='Table1', ref=f'a1:{Utils.num2az(COLS)}{ROWS}')
            tab.tableStyleInfo = worksheet.table.TableStyleInfo(name='TableStyleMedium8', showFirstColumn=False, 
                                                                showLastColumn=False, showRowStripes=False, showColumnStripes=False)
            if 'Table1' in ws.tables:
                del ws.tables['Table1']
            ws.add_table(tab)

            # adjust col widths
            COLW = {'a': 27, 'b': 18, 'c': 35, 'd': 77, 'e': 44, 'f': 16}
            for i in range(7, COLS + 1):
                COLW[Utils.num2az(i)] = 16
            for c in COLW:
                ws.column_dimensions[c].width = COLW[c]

            # highlight missing and latest versions
            for row in ws.iter_rows(min_row=2, max_row=ROWS, min_col=7, max_col=COLS):
                for cell in row:
                    if not cell.value:
                        cell.style = 'Accent2'
                cells = list(row)
                lv = self._get_latest_vers([c.value or '' for c in cells], version_compare_level)
                if not lv is None:
                    cells[lv].style = 'Accent1'
            
            # save workbook
            wb.save(filename=filepath)
            if self.debug: print(f'SAVED TO EXCEL ("{filepath}")')

        except Exception as err:
            print(err)

    def to_csv(self, filepath='pk.csv', pyexes=None, df=None, sep=';'):
        df = df if not df is None else self.compare_env(pyexes)
        if self.debug: print(f'OUTPUTTING TO CSV ("{filepath}") ...')
        df.to_csv(filepath, sep=sep, index=False)
        if self.debug: print(f'SAVED TO CSV ("{filepath}")')

    def to_html(self, filepath='pk.html', pyexes=None, df=None):
        df = df if not df is None else self.compare_env(pyexes)
        if self.debug: print(f'OUTPUTTING TO HTML ("{filepath}") ...')
        with open(filepath, 'w', encoding='utf-8') as file_:
            file_.write(df.to_html(na_rep='', index=False, render_links=True))
        if self.debug: print(f'SAVED TO HTML ("{filepath}")')

    def to_json(self, filepath='pk.json', pyexes=None, df=None):
        df = df if not df is None else self.compare_env(pyexes)
        if self.debug: print(f'OUTPUTTING TO JSON ("{filepath}") ...')
        with open(filepath, 'w', encoding='utf-8') as file_:
            file_.write(df.to_json(orient='index', indent=2))
        if self.debug: print(f'SAVED TO JSON ("{filepath}")')

    def to_pickle(self, filepath='pk.gz', pyexes=None, df=None, compression='infer'):
        df = df if not df is None else self.compare_env(pyexes)
        if self.debug: print(f'OUTPUTTING TO PICKLE ("{filepath}") ...')
        df.to_pickle(filepath, compression=compression)
        if self.debug: print(f'SAVED TO PICKLE ("{filepath}")')

    def to_clipboard(self, pyexes=None, df=None, excel=True, sep=None):
        df = df if not df is None else self.compare_env(pyexes)
        df.to_clipboard(excel, sep, index=False, na_rep='')
        if self.debug: print('SAVED TO CLIPBOARD')

    def to_string(self, pyexes=None, df=None):
        df = df if not df is None else self.compare_env(pyexes)
        return df.to_string(index=False, na_rep='')

    def to_stringx(self, pyexes=None, df=None, tablefmt='fancy_grid', maxwidth=200, filepath=None, **kwargs):
        df = df if not df is None else self.compare_env(pyexes)
        if maxwidth:
            maxcolw = maxwidth // len(df.columns)
            df = df.transform(lambda x: x.str.wrap(maxcolw))
        kwargs = kwargs or {}
        if tablefmt:
            kwargs['tablefmt'] = tablefmt 
        kwargs['headers'] = 'keys'
        kwargs['showindex'] = False
        if not 'stralign' in kwargs:
            kwargs['stralign'] = 'left'
        s = tabulate(df, **kwargs)
        if filepath:
            if self.debug: print(f'OUTPUTTING TO TEXT FILE ("{filepath}") ...')
            with open(filepath, 'w', encoding='utf-8') as file_:
                file_.write(s)
            if self.debug: print(f'SAVED TO TEXT FILE ("{filepath}")')
        return s

    def _comp_versions(self, versions, level=2):
        getvers = lambda s: pkvers.Version('.'.join(s.strip().split('.')[:level]) if s.strip() else '0')
        vv = list(enumerate([getvers(v) for v in versions]))
        values = set(map(lambda x: x[1], vv))
        newlist = sorted([[y for y in vv if y[1]==x] for x in values], key=lambda e: e[0][1])
        return [tuple(x[0] for x in e) if len(e) > 1 else e[0][0] for e in newlist]

    def _get_latest_vers(self, versions, level=2):
        latest = self._comp_versions(versions, level)[-1]
        return latest if not isinstance(latest, tuple) else None

    def _collect_env_packages(self, pyexes):
        if not pyexes: return None
        isdict = isinstance(pyexes, dict)
        packages = {}
        def on_envpklist(pyexe, envpklist):
            k = pyexes[pyexe] if isdict else pyexe
            if not k:
                k = self._get_env_version(pyexe) if pyexe else f'{sys.version.split()[0]} (CURRENT)'
            elif self.version_labels and not isdict:
                k = self._get_env_version(pyexe)
            if k:
                packages[k] = dict(envpklist)
                if self.debug: print(f'>>> RETRIEVED PKS FOR ENV: {k}')
            elif self.debug: 
                print(f'~~~ CANNOT PARSE ENV "{pyexe}"!')
        if self.debug: print(f'{NL}COLLECTING PACKAGE LISTS FROM {len(pyexes)} ENVS ...')
        self._list_packages_env_multi(pyexes, on_envpklist=on_envpklist, on_error=(lambda pyexe, exc: print(f'~~~ ERROR LISTING PKS FOR ENV "{pyexe}": {str(exc)}')))
        if not packages: return None

        pknames = set()
        for v in packages.values():
            for kk in v:
                pknames.add(kk)
        pknames = list(pknames)
        if self.debug: print(f'COLLECTED {len(pknames)} PACKAGES FROM {len(pyexes)} ENVS')

        return (packages, pknames)

    def _db2pd(self):
        if self._pkdict:
            df = pd.DataFrame.from_dict(self._pkdict, orient='index')
            return df.reindex(sorted(df.index, key=lambda x: x.lower())) #df.sort_index()
        return None

    def _get_env_version(self, env):
        env = env or sys.executable
        try:
            return sp.check_output([env, '-V'], encoding='utf-8').split(' ')[-1].strip()
        except:
            return None

    def _get_pkg_info_multi(self, pknames, on_info=None, on_error=None):
        ex_class = concurrent.futures.ProcessPoolExecutor if self.use_procs else concurrent.futures.ThreadPoolExecutor
        with ex_class(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.get_pkg_info, pkname): pkname for pkname in pknames}
            for future in concurrent.futures.as_completed(futures):
                pkname = futures[future]
                try:
                    pkinf = future.result()
                    if on_info: on_info(pkname, pkinf)
                except Exception as err:
                    if on_error: on_error(pkname, err)

    def _list_packages_env_multi(self, pyexes, on_envpklist=None, on_error=None):
        ex_class = concurrent.futures.ProcessPoolExecutor if self.use_procs else concurrent.futures.ThreadPoolExecutor
        with ex_class(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.list_packages_env, pyexe): pyexe for pyexe in pyexes}
            for future in concurrent.futures.as_completed(futures):
                pyexe = futures[future]
                try:
                    envpklist = future.result()
                    if on_envpklist: on_envpklist(pyexe, envpklist)
                except Exception as err:
                    if on_error: on_error(pyexe, err)

    def __call__(self, key=None):
        return self.compare_env(key)