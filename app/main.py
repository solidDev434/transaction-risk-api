from fastapi import FastAPI

# Routers

app = FastAPI()


@app.get("/health")
async def read_health():
    return {"status": "healthy"}
