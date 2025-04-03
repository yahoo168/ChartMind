from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from app.models.user_models import UserRegistrationModel, UserLoginModel
from app.services.user_services import UserAuthService
from app.utils.logging_config import logger
# from app.utils.mongodb_utils import MongoDB
from app.exceptions.user_exceptions import UserAlreadyExistsError, UserCreationError, InvalidCredentialsError

router = APIRouter()

@router.post("/login")
async def login(user: UserLoginModel):
    try:
        user_service = UserAuthService()
        result = await user_service.login_user(username=user.username, password=user.password)
                
        return JSONResponse(status_code=200, content={
            "access_token": result["access_token"],
            "token_type": "bearer",
            "user_id": result["user_id"],
        })
    except InvalidCredentialsError:
        raise HTTPException(status_code=400, detail="帳號密碼錯誤")
    except Exception as e:
        logger.error(f"登录过程中发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="服务器错误，请稍后重试")

@router.post("/register")
async def register(user: UserRegistrationModel):
    try:
        user_service = UserAuthService()
        await user_service.create_user_from_website(user)
        return JSONResponse(status_code=201, content={"message": "注册成功！"})
    except UserAlreadyExistsError:
        raise HTTPException(status_code=400, detail="该用户名已被注册")
    except UserCreationError as e:
        logger.warn(f"UserCreationError: {str(e)}")
        raise HTTPException(status_code=400, detail="注册失败，请稍后重试")
    except Exception as e:
        logger.info(e)
        raise HTTPException(status_code=500, detail="服务器错误，请稍后重")
    
# @router.get("/test")
# async def test():
#     logger.info("測試 API 呼叫")
#     return JSONResponse(status_code=200, content={"message": "API 測試成功"})