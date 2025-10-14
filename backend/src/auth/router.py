from fastapi import APIRouter, status

from src.auth import exceptions, schemas, service, utils
from src.db.dependencies import DbSession

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup", response_model=schemas.Token, status_code=status.HTTP_201_CREATED
)
async def signup(user_create: schemas.UserCreate, db: DbSession):
    db_user = await service.get_user_by_email(db, email=user_create.email)
    if db_user:
        raise exceptions.USER_ALREADY_EXISTS_EXCEPTION

    user = await service.create_user(db=db, user_create=user_create)
    access_token = utils.create_access_token(data={"sub": user.email})
    return schemas.Token(access_token=access_token)


@router.post("/login", response_model=schemas.Token)
async def login(user_login: schemas.UserLogin, db: DbSession):
    user = await service.authenticate_user(
        db, email=user_login.email, password=user_login.password
    )
    if not user:
        raise exceptions.INCORRECT_CREDENTIALS_EXCEPTION

    access_token = utils.create_access_token(data={"sub": user.email})
    return schemas.Token(access_token=access_token)
