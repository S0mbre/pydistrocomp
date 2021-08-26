# -*- coding: utf-8 -*-

import requests, sys, os, json
import subprocess as sp
import concurrent.futures

NL = '\n'
WORKERS = 10
TIMEOUT = 4
TESTFILE = r'c:\_PROG_\WPy64-3950\p396.txt'
TESTJS = r'c:\_PROG_\WPy64-3950\p396.json'

class Pkgcomp:

    def __init__(self, pyexes=None, dbdir=None, use_procs=True, max_workers=WORKERS, 
                timeout=TIMEOUT, requests_args={}):
        self.pyexes = pyexes
        self.dbdir = dbdir or os.path.dirname(os.path.realpath(__file__))
        self.dbfile = os.path.join(self.dbdir, 'pypkg.json')
        self.max_workers = max_workers
        self.timeout = timeout
        self.requests_args = requests_args
        self.use_procs = use_procs
        self.load_db()

    def __del__(self):
        self.save_db()

    def load_db(self, filepath=None):
        if filepath:
            self.dbfile = os.path.abspath(filepath)
            self.dbdir = os.path.dirname(self.dbfile)
        self._pkdict = {}
        if os.path.isfile(self.dbfile):
            with open(self.dbfile, 'r', encoding='utf-8') as infile:
                self._pkdict = json.load(infile)

    def save_db(self, filepath=None):
        if filepath:
            self.dbfile = os.path.abspath(filepath)
            self.dbdir = os.path.dirname(self.dbfile)
        if self._pkdict:
            with open(self.dbfile, 'w', encoding='utf-8') as jsfile:
                json.dump(self._pkdict, jsfile, ensure_ascii=False, indent=2)

    def get_pkg_info(self, pkname):
        res = requests.get('https://pypi.org/pypi/{}/json'.format(pkname), 
                           headers={'Accept': 'application/json'}, timeout=self.timeout, **self.requests_args)
        if res.status_code != 200: 
            raise Exception(f'HTTP Error {res.status_code}!{NL}{res.text}')
        resjs = json.loads(res.content)
        return resjs['info']

    def get_pkg_info_multi(self, pknames, on_info=None, on_error=None):
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

    def update_db(self, pknames, **kwargs):
        def on_info(pkname, pkinf):
            self._pkdict.update({pkname: 
                                    {'name': pkinf.get('name', pkname),
                                    'author': pkinf.get('author', ''),
                                    'summary': pkinf.get('summary', ''),
                                    'latest': pkinf.get('version', ''),
                                    'homepage': pkinf.get('package_url', pkinf.get('project_url', pkinf.get('home_page', '')))
                                    }})
        get_pkg_info_multi(pknames, on_info=on_info, on_error=(lambda pkname, exc: print(f'{pkname}: {str(exc)}')), **kwargs)

    def get_pip_list(pyexe=None):
        pyexe = pyexe or sys.executable
        return [s.strip().split('==') for s in sp.check_output([pyexe, '-m', 'pip', 'freeze'], encoding='utf-8').split('\n') if s]

def main():
    """
    pknames = []
    versions = []
    with open(TESTFILE, 'r', encoding='utf-8') as txtfile:
        for ln in txtfile:
            s = ln.split('==')
            pknames.append(s[0].strip())
            versions.append(s[1].strip() if len(s) > 1 else '')  

    pkdict = collect_pkinfo(pknames)
    with open(TESTJS, 'w', encoding='utf-8') as jsfile:
        json.dump(pkdict, jsfile, ensure_ascii=False, indent=2)
    """
    lst = get_pip_list(r'c:\Progs\WPy64-3901\python-3.9.0rc1.amd64\python.exe')
    print(lst)

## ---------------------------------------------------------------------------------------------- ##
if __name__ == '__main__':
    main()                    