import os
import platform
import ivy_to_cpp

def main():
    if platform.system() == 'Darwin':
        path = ':'.join(os.path.join(x,'lib') for x in ivy_to_cpp.get_lib_dirs())
        pvar = 'DYLD_LIBRARY_PATH'
        if os.environ.get(pvar):
            path += ':' + os.environ[pvar]
        cmd = 'export {}={}'.format(pvar,path)
        print(cmd)
