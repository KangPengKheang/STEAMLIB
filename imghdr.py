# Compatibility shim for Python 3.13
# Streamlit still imports imghdr (removed from stdlib)

def what(file, h=None):
    return None
