from fastapi import status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Any, Optional, Dict, List
from common_fastapi.shared.constant import Const

class CodeMsgBase(BaseModel):
    code: str = "0"
    msg: str = ""

class Common(CodeMsgBase): # allow rs to be any JSON-serializable structure (dict or list)
    rs: Any = Field(default_factory=dict) # Field는 그냥 값을 담는 그릇이라 보면 됨. 여러 인스턴스가 같은 dict 객체를 공유하는 버그를 피함
    # reply: Optional[Any] = None

def rsObj(obj: Optional[Dict[str, Any]] = {}):
    return {
        "rs": obj
    }
    
def rsError(code=Const.CODE_NOT_OK, msg="", is500=False):
    payload = {
        "code": code,
        "msg": msg
    }
    status_code=status.HTTP_200_OK
    if is500:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR        
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))

# def raiseHttpEx(code=Const.CODE_NOT_OK, msg="", statusCode=status.HTTP_200_OK):
#     # 클라이언트에서 axios 호출시 status.HTTP_200_OK이 아니면 try catch의 catch (ex)로 전달됨. status.HTTP_200_OK이면 try문 안에서 계속됨
#     # raise HTTPException( # headers={ "WWW-Authenticate": "Bearer" } => 옵션
#     #     status_code=statusCode,
#     #     detail={ "code": code, "msg": msg }
#     # )
#     return {
#             "code": "000000000000",
#             "msg": "",
#             "rs": "000000000000",
#             "resp": "@@@@",
#             "repr": "####"
#         }      

# class ControlledHttpException(Exception):
#     """A simple exception class carrying http-like payload.

#     Use this when you want to raise an error that will be caught
#     by ordinary `except Exception as e:` handlers (it subclasses
#     Exception) but still carries a status/code/msg payload for
#     middleware or handlers to inspect.
#     """
#     def __init__(self, code: str = Const.CODE_NOT_OK, msg: str = "", status_code: int = status.HTTP_200_OK):
#         super().__init__(f"{code}: {msg}")
#         self.code = code
#         self.msg = msg
#         self.status_code = status_code

# def raiseHttpEx11(code=Const.CODE_NOT_OK, msg="", statusCode=status.HTTP_200_OK):
#     """Raise a ControlledHttpException instead of FastAPI's HTTPException.

#     This variant is useful when you want the raised object to be a plain
#     Python Exception (so it can be caught by local `except Exception:` blocks)
#     while still carrying structured information (code/msg/status_code).

#     It does NOT send a response; it only raises the exception object.
#     Your route-level try/except can catch it and return the desired JSON
#     payload (for example, `{ "code": "-1", "msg": str(e) }`).
#     """
#     raise ControlledHttpException(code=str(code), msg=str(msg), status_code=statusCode)
