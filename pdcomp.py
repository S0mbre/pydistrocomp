# -*- coding: utf-8 -*-
from pydistro import Distros
from utils import Utils

## ---------------------------------------------------------------------------------------------- ##

def main():   
    # environments to compare (None = current)
    envs = [None, r'c:\_PROG_\WPy64-3910\python-3.9.1.amd64\python.exe', None, '']
    distros = Distros(envs, force_update=False)

    print(distros['3.9.1']['dask'].requires(distros['3.9.1'].pyexe))

    # df = distros.asdataframe()
    # distros.to_stringx(df=df, filepath='pk.txt')
    # distros.to_csv(df=df)
    # distros.to_html(df=df)
    # distros.to_json(df=df)
    # distros.to_pickle(df=df)
    # distros.to_xl(df=df)

    # diff_pk = distros['3.9.1'] - distros['']
    # print(f'Differing packages = {len(diff_pk)}')
    # diff_pk.to_xl('diff.xlsx')
    
## ---------------------------------------------------------------------------------------------- ##
if __name__ == '__main__':
    main()