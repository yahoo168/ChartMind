class UserBaseException(Exception):
    """用戶相關異常的基類"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class UserAlreadyExistsError(UserBaseException):
    """當嘗試創建已存在的用戶時拋出"""
    pass

class UserNotFoundError(UserBaseException):
    """當查找的用戶不存在時拋出"""
    pass

class InvalidCredentialsError(UserBaseException):
    """當用戶登錄憑證（用戶名/密碼）無效時拋出"""
    pass

class UserCreationError(UserBaseException):
    """當創建用戶過程中發生技術錯誤時拋出"""
    pass

class InvalidUserDataError(UserBaseException):
    """當用戶數據格式或內容無效時拋出"""
    pass

class ExternalAuthError(UserBaseException):
    """當外部認證（如 Line、Google）失敗時拋出"""
    pass