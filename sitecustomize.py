# Python 3.13 compatibility for packages still importing imghdr (e.g. Streamlit)

import sys
import types

imghdr = types.ModuleType("imghdr")

def what(file, h=None):
    return None

imghdr.what = what
sys.modules["imghdr"] = imghdr
