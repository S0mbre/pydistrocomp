# -*- coding: utf-8 -*-

import requests, sys, os, json
import subprocess as sp
import concurrent.futures

NL = '\n'
WORKERS = 10
TIMEOUT = 4
TESTFILE = r'c:\_PROG_\WPy64-3950\p396.txt'
TESTJS = r'c:\_PROG_\WPy64-3950\p396.json'

def get_pkg_info(pkname, timeout=TIMEOUT):
    res = requests.get('https://pypi.org/pypi/{}/json'.format(pkname), headers={'Accept': 'application/json'}, timeout=timeout)
    if res.status_code != 200: 
        raise Exception(f'HTTP Error {res.status_code}!{NL}{res.text}')
    resjs = json.loads(res.content)
    if not 'info' in resjs: 
        raise Exception(f'No "info" section in returned pkg info!{NL}{res.text}')        
    return resjs['info']

def get_pkg_info_multi(pknames, on_info=None, on_error=None, use_procs=True, max_workers=WORKERS, timeout=TIMEOUT):
    ex_class = concurrent.futures.ProcessPoolExecutor if use_procs else concurrent.futures.ThreadPoolExecutor
    with ex_class(max_workers=max_workers) as executor:
        futures = {executor.submit(get_pkg_info, pkname, timeout): pkname for pkname in pknames}
        for future in concurrent.futures.as_completed(futures):
            pkname = futures[future]
            try:
                pkinf = future.result()
                if on_info: on_info(pkname, pkinf)
            except Exception as err:
                if on_error: on_error(pkname, err)

def collect_pkinfo(pknames, pkdict=None, **kwargs):
    pkdict = pkdict or {}
    def on_info(pkname, pkinf):
        pkdict.update({pkname: {'name': pkinf.get('name', pkname),
                                'author': pkinf.get('author', ''),
                                'summary': pkinf.get('summary', ''),
                                'latest': pkinf.get('version', ''),
                                'homepage': pkinf.get('package_url', pkinf.get('project_url', pkinf.get('home_page', '')))
                                }})
    get_pkg_info_multi(pknames, on_info=on_info, on_error=(lambda pkname, exc: print(f'{pkname}: {str(exc)}')), **kwargs)
    return pkdict

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
    lst = get_pip_list()
    print(lst)

## ---------------------------------------------------------------------------------------------- ##
if __name__ == '__main__':
    main()                    