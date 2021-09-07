# -*- coding: utf-8 -*-
import subprocess as sp
import sys
class Utils:

    @staticmethod
    def is_iterable(obj):
        if isinstance(obj, str): return False
        try:
            _ = iter(obj)
            return True
        except:
            return False

    @staticmethod
    def num2az(num):
        s = ''
        while num > 0:
            num, remainder = divmod(num - 1, 26)
            s = chr(65 + remainder) + s
        return s

    @staticmethod
    def execute(args, encoding='utf-8', capture_stderr=True, on_error=None):
        try:
            return sp.check_output(args, stderr=sp.STDOUT if capture_stderr else None, encoding=encoding)

        except sp.CalledProcessError as err:
            if on_error:
                on_error(err.cmd, err.returncode, err.stdout, err.stderr)
            else:
                raise

    @staticmethod
    def pip(args, pkname=None, pyexe=None, on_error=None):
        if not args:
            raise Exception('No arguments given to pip!')

        pyexe = pyexe or sys.executable
        args_ = [pyexe, '-m', 'pip'] + [cmd for cmd in args]
        if pkname: args_.append(pkname)
        
        def on_error_(cmd, returncode, stdout, stderr):
            on_error({'cmd': cmd, 'returncode': returncode, 'stdout': stdout, 'stderr': stderr})

        return Utils.execute(args_, on_error=on_error_ if on_error else None)
