from smbclient import register_session, copyfile, makedirs, removedirs, remove, utime, stat, walk
from smbprotocol.exceptions import SMBOSError, SMBException
from smbprotocol.open import FileAttributes

class SMB:
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        register_session(server, username=username, password=password)

    def reinit(self):
        register_session(self.server, username=self.username, password=self.password)

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
                if self._exists(dst):
                    raise FileExistsError(f"移動先に既に存在しています: {dst}")

                copyfile(src, dst)
                st_src = stat(src)
                utime(dst, ns=(st_src.st_atime_ns, st_src.st_mtime_ns))
                st_dst = stat(dst)
                if st_dst.st_size != st_src.st_size or st_dst.st_mtime_ns != st_src.st_mtime_ns:
                    raise IOError(f"ファイルサイズと更新日時が一致していない: {dst}")

                remove(src)

        removedirs(src_dir)

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

    def _exists(self, path):
        self.reinit()
        try:
            stat(path)
            return True
        except FileNotFoundError:
            return False
        except SMBOSError as e:
            if "STATUS_OBJECT_NAME_NOT_FOUND" in str(e) or "c000003a" in str(e) or "0xc0000034" in str(e):
                return False
            raise

    def _is_dir(self, path):
        self.reinit()
        try:
            st = stat(path)
            return bool(st.st_file_attributes & FileAttributes.FILE_ATTRIBUTE_DIRECTORY)
        except FileNotFoundError:
            return False
        except SMBOSError as e:
            if "STATUS_OBJECT_NAME_NOT_FOUND" in str(e) or "c000003a" in str(e) or "0xc0000034" in str(e):
                return False
            raise
