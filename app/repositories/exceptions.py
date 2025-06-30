class RepositoryError(Exception):
    """すべてのリポジトリエラーの基底クラス"""
    def __init__(self, detail: str | None = None):
        self.detail = detail
        super().__init__(detail)

class NotFoundError(RepositoryError):
    """リソースが見つからなかったとき"""

class AlreadyExistsError(RepositoryError):
    """一意制約などで既に存在するとき"""

class InvalidDataError(RepositoryError):
    """不正なデータを受け取ったとき (HTTP 400)"""

class UnexpectedError(RepositoryError):
    """予期せぬその他エラー (HTTP 500)"""
