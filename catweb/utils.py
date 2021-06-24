import pathlib


def mkdir_exist_ok(path):
    """
    make a dir and don't fail if it exists

    takes string paths or pathlib posixpaths
    """
    if type(path) != pathlib.PosixPath:
        path = pathlib.Path(path)
    try:
        path.mkdir(parents=True)
    except FileExistsError:
        pass
