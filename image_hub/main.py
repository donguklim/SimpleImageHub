from fastapi import FastAPI


app = FastAPI()


@app.get('/hello')
async def login() -> dict[str, str]:
    return dict(message='Hello')
