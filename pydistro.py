# -*- coding: utf-8 -*-

import requests, sys, os, json
import subprocess as sp
import concurrent.futures
import pandas as pd
from openpyxl import load_workbook, worksheet, styles
import packaging.version as pkvers
from tabulate import tabulate

NL = '\n'
WORKERS = 10
TIMEOUT = 4

def is_iterable(obj):
    if isinstance(obj, str): return False
    try:
        _ = iter(obj)
        return True
    except:
        return False

def num2az(num):
    s = ''
    while num > 0:
        num, remainder = divmod(num - 1, 26)
        s = chr(65 + remainder) + s
    return s

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
        if not isinstance(pyexes, dict) and not is_iterable(pyexes):
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
            tab = worksheet.table.Table(displayName='Table1', ref=f'a1:{num2az(COLS)}{ROWS}')
            tab.tableStyleInfo = worksheet.table.TableStyleInfo(name='TableStyleMedium8', showFirstColumn=False, 
                                                                showLastColumn=False, showRowStripes=False, showColumnStripes=False)
            if 'Table1' in ws.tables:
                del ws.tables['Table1']
            ws.add_table(tab)

            # adjust col widths
            COLW = {'a': 27, 'b': 18, 'c': 35, 'd': 77, 'e': 44, 'f': 16}
            for i in range(7, COLS + 1):
                COLW[num2az(i)] = 16
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