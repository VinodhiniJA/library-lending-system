
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.books import router as books_router
from routers.loans import router as loans_router
from routers.fines import router as fines_router
from routers.reservations import router as reservations_router
from routers import dashboard
from routers import settings
from routers import registration_payment
from routers import password_reset


app = FastAPI(
    title="Library Lending Management System",
    description=(
        "Backend API for managing books, loans, "
        "reservations and fines"
    )
)


# =====================================
# ANGULAR CORS CONFIGURATION
# =====================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =====================================
# REGISTER API ROUTERS
# =====================================

app.include_router(auth_router)
app.include_router(books_router)
app.include_router(loans_router)
app.include_router(fines_router)
app.include_router(reservations_router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(registration_payment.router)
app.include_router(password_reset.router)

@app.get("/")
def home():
    return {
        "message": "Library Lending Management API"
    }
