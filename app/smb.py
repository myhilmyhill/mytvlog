from typing import Tuple
from pathlib import Path
from smbclient import register_session, copyfile, makedirs, removedirs, remove, utime, stat, walk, scandir
from smbprotocol.exceptions import SMBOSError, NoSuchFile
from smbprotocol.open import FileAttributes

class SMB:
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        register_session(server, username=username, password=password)

    def reinit(self):
        register_session(self.server, username=self.username, password=self.password)

    def move_files(self, src_file_or_pattern, dst_dir):
        self.reinit()
        if self._is_dir(src_file_or_pattern):
            raise IsADirectoryError(f"フォルダ: {src_file_or_pattern}")

        makedirs(dst_dir, exist_ok=True)
        src_path = Path(src_file_or_pattern)
        src_dir = str(src_path.parent)
        src_pattern = src_path.name

        for d in scandir(src_dir, src_pattern):
            if d.is_dir():
                self.move_folder(d.path, f"{dst_dir}/{d.name}")
            elif d.is_file():
                src = d.path
                dst = f"{dst_dir}/{d.name}"
                if self.exists(dst):
                    raise FileExistsError(f"移動先に既に存在しています: {dst}")

                copyfile(src, dst)
                st_src = stat(src)
                utime(dst, ns=(st_src.st_atime_ns, st_src.st_mtime_ns))
                st_dst = stat(dst)
                if st_dst.st_size != st_src.st_size or st_dst.st_mtime_ns != st_src.st_mtime_ns:
                    raise IOError(f"ファイルサイズと更新日時が一致していない: {dst}")

                remove(src)

    def move_folder(self, src_dir, dst_dir):
        self.reinit()
        if not self._is_dir(src_dir):
            raise NotADirectoryError(f"フォルダでない: {src_dir}")
        makedirs(dst_dir, exist_ok=True)

        for w in walk(src_dir):
            w_top_src, w_dirs, w_files = w
            w_top_dst = w_top_src.replace(src_dir, dst_dir)

            for dir in w_dirs:
                makedirs(f"{w_top_dst}/{dir}", exist_ok=True)

            for file in w_files:
                src = f"{w_top_src}/{file}"
                dst = f"{w_top_dst}/{file}"
                if self.exists(dst):
                    raise FileExistsError(f"移動先に既に存在しています: {dst}")

                copyfile(src, dst)
                st_src = stat(src)
                utime(dst, ns=(st_src.st_atime_ns, st_src.st_mtime_ns))
                st_dst = stat(dst)
                if st_dst.st_size != st_src.st_size or st_dst.st_mtime_ns != st_src.st_mtime_ns:
                    raise IOError(f"ファイルサイズと更新日時が一致していない: {dst}")

                remove(src)

        removedirs(src_dir)

    def move_files_by_root(self, src_file_or_pattern, dst_root) -> Tuple[str, str]:
        self.reinit()
        if self._is_dir(src_file_or_pattern):    # //server/src_root/to/dir
            self.move_folder_by_root(src_file_or_pattern, dst_root)

        src_dir = src_file_or_pattern # //server/src_root/to/pattern
        parts = src_dir.split("/")    # -> [, , server, src_root, to, pattern]
        parts[3] = dst_root           # -> [, , server, dst_root, to, pattern]
        pattern = parts.pop()         # -> [, , server, dst_root, to]
        dst_dir = "/".join(parts)

        self.move_files(src_file_or_pattern, dst_dir)
        return dst_dir, pattern

    def move_folder_by_root(self, src_dir, dst_root) -> str:
        self.reinit()
        if not self._is_dir(src_dir):
            parts_src = src_dir.split("/")
            parts_src.pop()
            src_dir = "/".join(parts_src)

        parts = src_dir.split("/")
        parts[3] = dst_root
        dst_dir = "/".join(parts)

        self.move_folder(src_dir, dst_dir)
        return dst_dir

    def delete_files(self, src_file_or_pattern) -> bool:
        self.reinit()
        if self._is_dir(src_file_or_pattern):
            raise IsADirectoryError(f"フォルダ: {src_file_or_pattern}")

        src_path = Path(src_file_or_pattern)
        src_dir = str(src_path.parent)
        src_pattern = src_path.name

        try:
            processed = False
            for d in scandir(src_dir, src_pattern):
                if d.is_dir():
                    pass
                elif d.is_file():
                    src = d.path
                    remove(src)
                    processed = True
            return processed
        except NoSuchFile:
            return False
        except SMBOSError as e:
            if "0xc0000034" in str(e):    # No such file or directory
                return False
            raise

    def get_file_size(self, path) -> int | None:
        self.reinit()
        try:
            st = stat(path)
            return st.st_size
        except FileNotFoundError:
            return None
        except SMBOSError as e:
            if "STATUS_OBJECT_NAME_NOT_FOUND" in str(e) or "c000003a" in str(e) or "0xc0000034" in str(e):
                return None
            raise

    def exists(self, path) -> bool:
        return self.get_file_size(path) is not None

    def _is_dir(self, path) -> bool:
        self.reinit()
        try:
            st = stat(path)
            return bool(st.st_file_attributes & FileAttributes.FILE_ATTRIBUTE_DIRECTORY)
        except FileNotFoundError:
            return False
        except SMBOSError as e:
            if "STATUS_OBJECT_NAME_NOT_FOUND" in str(e) or "c000003a" in str(e) or "0xc0000034" in str(e) or "0xc0000033" in str(e):
                return False
            raise
