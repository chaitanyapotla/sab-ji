import uvicorn
import datetime
from fastapi import FastAPI, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@postgres/postgres"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

plans = {"FREE", "TRIAL", "LITE_1M", "PRO_1M", "LITE_6M", "PRO_6M"}
plan_cost = {"FREE": 0.0, "TRIAL": 0.0, "LITE_1M": 100.0, "PRO_1M": 200.0, "LITE_6M": 500.0, "PRO_6M": 900.0}
plan_validity = {"FREE": "Infinite", "TRIAL": 7, "LITE_1M": 30, "PRO_1M": 30, "LITE_6M": 180, "PRO_6M": 180}


class UserModel(Base):
    __tablename__ = "userdetails"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, unique=True, index=True)


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, unique=True, index=True)
    plan_id = Column(String, )
    start_date = Column(Date)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()


class UserSchema(BaseModel):
    user_name: str

    class Config:
        orm_mode = True


class SubscriptionSchema(BaseModel):
    user_name: str
    plan_id: str
    start_date: str
    amount: str

    class Config:
        orm_mode = True


@app.put("/user/{user_name}", response_model=UserSchema)
async def create_user(user_name, db: Session = Depends(get_db)):
    _user = UserModel(
        user_name=user_name
    )
    db.add(_user)
    db.commit()
    db.refresh(_user)
    return _user


@app.get("/user/{user_name}", response_model=UserSchema)
async def get_user(user_name: str, db: Session = Depends(get_db)):
    _user = db.query(UserModel).filter_by(user_name=user_name).first()
    return _user


@app.post("/subscription", status_code=200)
def new_subscription(subscription=SubscriptionSchema, db: Session = Depends(get_db)):
    status = "SUCCESS"
    amount = 0.0
    try:
        check_for_date(subscription.start_date)
        _subscription = check_for_plan(subscription)
        db.add(_subscription)
        db.commit()
        db.refresh(_subscription)
        amount = plan_cost[subscription.plan_id]
        return {"status": status, "amount": "-" + str(amount)}
    except Exception as e:
        Response.status_code = status.HTTP_400_BAD_REQUEST
        return {"status": str(e), "amount": "-" + str(amount)}


def check_for_plan(subscription):
    if subscription.plan_id in plans:
        _subscription = SubscriptionSchema(
            user_name=subscription.user_name, plan_id=subscription.plan_id, start_date=subscription.start_date
        )
        return _subscription
    else:
        raise ValueError("Invalid Plan ID")


def check_for_date(start_date):
    try:
        datetime.datetime.strptime(start_date, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")


@app.get("/subscription/{user_name}/{date}", response_model=SubscriptionSchema)
async def get_subscription(user_name: str, date: str, response: Response):
    try:
        if date:
            check_for_date(date)
            return get_all_subscription(user_name, date)
        else:
            return get_all_subscription(user_name)
    except ValueError as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return str(e)
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return str(e)


def get_all_subscription(user_name, start_date=None):
    db = get_db()
    subscriptions = []
    if start_date:
        _subscriptions = db.query(SubscriptionModel).filter_by(user_name=user_name).filter_by(start_date=start_date)
        for _subscription in _subscriptions:
            subscription = {"plan_id": _subscription.plan_id,
                            "days_left": get_days_left(_subscription.plan_id, _subscription.start_date)}
            subscriptions.push(subscription)
    else:
        _subscriptions = db.query(SubscriptionModel).filter_by(user_name=user_name)
        for _subscription in _subscriptions:
            subscription = {"plan_id": _subscription.plan_id, "start_date": _subscription.start_date,
                            "valid_till": get_valid_till(_subscription.plan_id, _subscription.start_date)}
            subscriptions.push(subscription)
    return subscriptions


def get_valid_till(plan_id, start_date):
    number_of_days = plan_validity[plan_id]
    valid_till = (
                datetime.datetime.strptime(start_date, "%Y-%m-%d") + datetime.timedelta(days=number_of_days)).strftime(
        "%Y-%m-%d")
    return valid_till


def get_days_left(plan_id, start_date):
    number_of_days = plan_validity[plan_id]
    current_date = datetime.today().strftime('%Y-%m-%d')
    difference = abs((datetime.strptime(start_date, "%Y-%m-%d") - current_date).days)
    if difference <= number_of_days:
        days_left = number_of_days - difference
    else:
        days_left = "Expired"
    return days_left


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=19093)
