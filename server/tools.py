def get_uid():
    """Generate an incrementing UID for each plugin."""
    #Written by Max Ertl (https://github.com/Sirs0ri)
    global UID
    uid = "d_{0:04d}".format(UID)
    UID += 1
    return uid