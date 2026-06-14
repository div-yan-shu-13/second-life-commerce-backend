from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import routing, grading, prevention

app = FastAPI(
    title="Second Life Commerce API",
    description=(
        "AI-powered returns management and sustainable resale platform. "
        "Provides intelligent product routing, vision-based quality grading, "
        "and predictive return prevention."
    ),
    version="1.0.0",
)

# CORS — allow all origins for hackathon (your teammate's UI can call freely)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(routing.router)
app.include_router(grading.router)
app.include_router(prevention.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Second Life Commerce API",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "routing": "/api/v1/routing/decide",
            "grading": "/api/v1/grading/assess",
            "prevention": "/api/v1/prevention/score",
            "docs": "/docs",
        },
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
