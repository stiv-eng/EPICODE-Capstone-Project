"""Verification-only guard proving analysis never imports or accesses models."""
import importlib.abc
import os
import sys

FORBIDDEN_ROOTS = {'keras', 'torch', 'sklearn', 'joblib', 'motorsport_prediction'}


def model_path(value):
    if not isinstance(value, (str, bytes, os.PathLike)):
        return False
    value = '/'+os.fsdecode(value).replace('\\', '/').lower().lstrip('/')
    name = value.rsplit('/', 1)[-1]
    return (name.endswith(('.joblib', '.keras', '.pt')) or name == '.local-signing-key' or
            '/artifacts/models' in value or ('/artifacts/barcelona_v' in value and '/models' in value))


def install():
    class BlockPrediction(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in FORBIDDEN_ROOTS or fullname == 'motorsport.ml' or fullname.startswith('motorsport.ml.'):
                raise AssertionError('Analysis attempted a retired import: '+fullname)
    sys.meta_path.insert(0, BlockPrediction())

    def audit(event, args):
        if event in ('open', 'os.listdir', 'os.scandir') and args and model_path(args[0]):
            raise AssertionError('Analysis attempted to access a model artifact')
    sys.addaudithook(audit)
    original_stat = os.stat

    def stat(path, *args, **kwargs):
        if model_path(path):
            raise AssertionError('Analysis attempted to inspect model artifacts')
        return original_stat(path, *args, **kwargs)
    os.stat = stat
