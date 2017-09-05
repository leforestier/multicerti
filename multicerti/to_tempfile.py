import os
from tempfile import mkstemp

def to_tempfile(strg, prefix = None):
    handle, temp_path = mkstemp(prefix = prefix)
    os.write(handle, strg.encode('utf-8'))
    os.close(handle)
    return temp_path 
