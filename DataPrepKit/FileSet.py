import pathlib
import os

# Classes for working with files.

image_file_suffix_set = {
    'png', 'jpg', 'jpeg', 'bmp', 'webp', 'pbm',
    'ppm', 'pgm', 'pxm', 'pnm', 'tif', 'tiff',
    'sr', 'ras', 'exr', 'hdr', 'pic',
  }

def filter_image_files_by_ext(filepath):
    """This function expects a value of type Path() or PurePath.

    The list of image file extensions used here can be found in the OpenCV v3.4 documentation:
    https://docs.opencv.org/3.4/d4/da8/group__imgcodecs.html#ga288b8b3da0892bd651fce07b3bbd3a56
    """
    ext = filepath.suffix.lower()
    if ext[0] == '.':
        ext = ext[1:]
    else:
        pass
    return (ext in image_file_suffix_set)

class FileSet():
    """A FileSet is a class of mutable objects responsible for keeping
    track of a subset of the files on the local filesystem. A FileSet
    can be constructed with a filtering predicate that silently
    rejects files which are not accepted by the predicate. Internall a
    mutable set() object is used. This class overrides iter() so a for
    loop can iterate over the elements of the FileSet.
    """

    def __init__(self, initset=None, filter=None):
        self.fileset = set()
        if filter is None:
            self.filter = None
        elif callable(filter):
            self.filter = filter
        else:
            t = type(filter)
            raise ValueError(
                f'FileSet(filter=...) filter must be callable, is {t}',
                t,
              )
        self.merge(initset)

    def __iter__(self):
        return iter(self.fileset)

    @classmethod
    def check_item_type(_cls, index, thing):
        if thing is None:
            return None
        elif isinstance(thing, pathlib.PurePath) or \
             isinstance(thing, pathlib.Path):
            return thing
        elif isinstance(thing, str):
            return pathlib.PurePath(thing)
        else:
            t = type(thing)
            if index is None:
                msg = f'value of type {t} cannot be included in FileSet(),'
            else:
                msg = f'element {index} of sequence cannot be included in FileSet(),'
            msg = f'{msg} expecting a value that can be used to construct a PurePath()'
            raise ValueError(msg, t, index)

    def merge(self, otherset):
        if otherset is None:
            pass
        elif isinstance(list, otherset) or \
             isinstance(set, otherset) or \
             isinstance(frozenset, otherset):
            for i, item in zip(range(len(otherset)), otherset):
                self.__add(item, index=i)
        elif isinstance(FileSet, otherset):
            # If the otherset is a FileSet, we can skip the
            # check_item_type(), and do some other simple
            # optimizations, like skipping the filter if the filter is
            # the same.
            if otherset is self:
                pass
            elif otherset.filter is self.filter:
                self.fileset = self.fileset.union(otherset.fileset)
            else:
                for item in otherset.fileset:
                    self.__add(item)
        else:
            t = type(otherset)
            raise ValueError(
                f'FileSet() constructor takes list, set, frozenset, or FileSet. Instead got {t}',
                t,
              )

    def freeze(self):
        return frozenset(self.fileset)

    def copy(self):
        return FileSet(initset=self.fileset, filter=self.filter)

    def new_filter(self, filter):
        """Change the current filter for this FileSet,
        remove elements not matching the new filter."""
        if filter is self.filter:
            pass
        else:
            self.filter = filter
            oldset = self.fileset
            self.fileset = set()
            self.merge(oldset)

    def __add(self, filepath, index=None):
        if (self.filter is None) or self.filter(filepath):
            self.fileset.add(filepath)
        else:
            pass

    def add(self, filepath):
        """Add a filepath to this FileSet."""
        filepath = FileSet.check_item_type(index, filepath)
            # ^ raises error if item is not an acceptable type
        self.__add(filepath, None)

    def delete(self, filepath):
        self.fileset.discard(filepath)

    def merge_recursive(self, filepath_args):
        """Scan through a directory for files matching the FileSet
        predicate. The argument to this method must be a Path or
        PurePath."""
        if isinstance(filepath_args, str) or \
           isinstance(filepath_args, pathlib.PurePath):
            self.__merge_recursive(pathlib.Path(filepath_args))
        elif isinstance(filepath_args, pathlib.Path):
           self.__merge_recursive(filepath_args)
        else:
            for filepath in filepath_args:
                #print(f'FileSet.merge_recursive("{filepath}")')
                if not filepath:
                    pass
                elif isinstance(filepath, str):
                    self.__merge_recursive(pathlib.PurePath(filepath))
                elif isinstance(filepath, pathlib.PurePath) or \
                     isinstance(filepath, pathlib.Path):
                    self.__merge_recursive(filepath)
                else:
                    raise ValueError(
                        f'FileSet.merge_recursive() given argument of type {type(filepath)}, '
                        f'expecting Path, PurePath, or string',
                      )

    def __merge_recursive(self, filepath):
        if pathlib.Path(filepath).is_dir():
            for root, _dirs, files in os.walk(str(filepath)):
                root = pathlib.PurePath(root)
                for filename in files:
                    filepath = pathlib.PurePath(filename)
                    self.__add(root / filepath)
        else:
            self.__add(filepath)
