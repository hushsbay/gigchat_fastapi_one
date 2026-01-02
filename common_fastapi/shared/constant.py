from typing import Final

class Const:

    CODE_OK: Final[str] = '0'
    CODE_NOT_OK: Final[str] = '-1'
    CODE_NOT_FOUND: Final[str] = '-100'
    CODE_BLANK_DATA: Final[str] = '-101'
    CODE_ALREADY_EXIST: Final[str] = '-102'

    MSG_NOT_OK: Final[str] = '오류가 발생하였습니다. '
    MSG_NOT_FOUND: Final[str] = '데이터가 없습니다. '
    MSG_BLANK_DATA: Final[str] = '값이 없습니다. '
    MSG_ALREADY_EXIST: Final[str] = '이미 존재하는 데이터입니다. '
