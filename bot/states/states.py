from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    date = State()
    time = State()
    comment = State()
    confirm = State()


class ReviewStates(StatesGroup):
    rating = State()
    text = State()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
