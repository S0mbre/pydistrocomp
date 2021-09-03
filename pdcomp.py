# -*- coding: utf-8 -*-
from pydistro import Pkgcomp

## ---------------------------------------------------------------------------------------------- ##

def main():   
    # environments to compare (None = current)
    envs = [None, r'c:\_PROG_\WPy64-3910\python-3.9.1.amd64\python.exe']
    # create class instance (don't update existing DB with latest versions, switch on debugging messages)
    pk = Pkgcomp(envs, get_latest_vers=False, debug=True)
    df = pk()
    # output to various formats:
    pk.to_xl('pk.xlsx', df=df)
    # pk.to_csv(df=df)
    # pk.to_html(df=df)
    # pk.to_json(df=df)
    # pk.to_pickle(df=df)
    # pk.to_stringx(df=df, filepath='pk.txt')
    
## ---------------------------------------------------------------------------------------------- ##
if __name__ == '__main__':
    main()