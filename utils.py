# -*- coding: utf-8 -*-
import subprocess as sp

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