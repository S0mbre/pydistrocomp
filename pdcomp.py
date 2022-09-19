# -*- coding: utf-8 -*-
from pydistro import Distros
import sys

## ---------------------------------------------------------------------------------------------- ##

def main():
    # environments to compare (None = current)
    envs = [None]
    distros = Distros(envs, force_update=False)
    df = distros.asdataframe()
    distros.to_xl('pk.xlsx' if len(sys.argv) < 2 else sys.argv[1], df=df)

## ---------------------------------------------------------------------------------------------- ##
if __name__ == '__main__':
    main()