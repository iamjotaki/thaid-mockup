import os
import io
import time
import uuid
import base64
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from PIL import Image

import mockup_engine as engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ThaiDMockupApp")

app = FastAPI(
    title="ThaiD Mockup AI Studio",
    description="Automated AI Product Photography & Mockup Generation Platform",
    version="1.0.0"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
PRESETS_DIR = os.path.join(BASE_DIR, "assets", "presets")
SAMPLES_DIR = os.path.join(BASE_DIR, "assets", "sample_products")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(PRESETS_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Mount static asset routes
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/presets", StaticFiles(directory=PRESETS_DIR), name="presets")
app.mount("/samples", StaticFiles(directory=SAMPLES_DIR), name="samples")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

class CompositeRequest(BaseModel):
    product_type: str = "sample"          # "sample", "custom_id", or "base64"
    product_id: Optional[str] = "skincare_serum.png"
    product_base64: Optional[str] = None
    scene_type: str = "preset"            # "preset" or "custom"
    scene_id: str = "cafe_marble"
    aspect_ratio: str = "1:1"             # "1:1", "4:5", "9:16"
    scale: float = 0.58
    pos_x: float = 0.50
    pos_y: float = 0.72
    shadow_intensity: float = 0.65
    shadow_type: str = "soft_contact"

class SceneGenerateRequest(BaseModel):
    prompt: str
    style_preset: Optional[str] = "cafe_marble"

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>ThaiD Mockup AI Studio is initializing...</h1>")


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    dashboard_path = os.path.join(STATIC_DIR, "dashboard.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return await serve_index()


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    admin_path = os.path.join(STATIC_DIR, "admin.html")
    if os.path.exists(admin_path):
        with open(admin_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return await serve_index()

@app.get("/api/status")
async def get_status():
    keys = engine.get_gemini_keys()
    presets_count = len([f for f in os.listdir(PRESETS_DIR) if f.endswith(('.jpg', '.png'))])
    samples_count = len([f for f in os.listdir(SAMPLES_DIR) if f.endswith('.png')])
    return {
        "ok": True,
        "service": "ThaiD Mockup AI Studio",
        "domain": "mockup.thaid.online",
        "status": "online",
        "port": 8096,
        "gemini_active": len(keys) > 0,
        "total_presets": len(engine.PRESET_TEMPLATES),
        "cached_presets": presets_count,
        "total_samples": samples_count,
        "supported_aspect_ratios": ["1:1 (Square)", "4:5 (Portrait)", "9:16 (Story/Reels)"],
        "features": [
            "AI Background Removal & Smart Edge Matting",
            "Dual-Layer Contact & Directional Shadow Synthesis",
            "Curated Commercial Luxury Presets (Cafe, Marble, Spa, Beach, Podium)",
            "Custom Scene Prompt Studio with Gemini Enhancement",
            "HD Multi-Format Export (Shopee, Lazada, TikTok, Meta Ads)"
        ]
    }

@app.get("/api/templates")
async def get_templates():
    templates = []
    for t in engine.PRESET_TEMPLATES:
        t_copy = dict(t)
        t_copy["preview_url"] = f"/presets/{t['id']}.jpg"
        templates.append(t_copy)
    return {"ok": True, "templates": templates}

@app.get("/api/samples")
async def get_samples():
    sample_items = [
        {"id": "skincare_serum.png", "name": "เซรั่มหยดแก้วสีอำพัน", "category": "Skincare", "url": "/samples/skincare_serum.png"},
        {"id": "perfume_bottle.png", "name": "ขวดน้ำหอมแก้วคริสตัล", "category": "Fragrance", "url": "/samples/perfume_bottle.png"},
        {"id": "coffee_tumbler.png", "name": "แก้วน้ำทัมเบลอร์สแตนเลสสีดำด้าน", "category": "Drinkware", "url": "/samples/coffee_tumbler.png"},
        {"id": "cosmetic_jar.png", "name": "กระปุกครีมฝาโรสโกลด์", "category": "Cosmetics", "url": "/samples/cosmetic_jar.png"},
        {"id": "supplement_bottle.png", "name": "ขวดยาอาหารเสริมสีขาวพรีเมียม", "category": "Supplements", "url": "/samples/supplement_bottle.png"}
    ]
    return {"ok": True, "samples": sample_items}

@app.post("/api/remove-bg")
async def remove_bg_endpoint(file: UploadFile = File(...)):
    """Upload product image and return transparent cutout PNG"""
    try:
        contents = await file.read()
        raw_img = Image.open(io.BytesIO(contents))
        clean_img = engine.remove_background(raw_img)

        # Save to outputs
        file_id = f"cutout_{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
        out_path = os.path.join(OUTPUTS_DIR, file_id)
        clean_img.save(out_path, "PNG")

        # Also prepare base64 for direct browser preview
        buffer = io.BytesIO()
        clean_img.save(buffer, format="PNG")
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "ok": True,
            "product_id": file_id,
            "url": f"/outputs/{file_id}",
            "base64": f"data:image/png;base64,{b64_str}",
            "width": clean_img.width,
            "height": clean_img.height
        }
    except Exception as e:
        logger.error(f"Error removing bg: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-scene")
async def generate_scene_endpoint(req: SceneGenerateRequest):
    """Generate custom luxury background scene via AI"""
    try:
        if not req.prompt or len(req.prompt.strip()) < 3:
            raise HTTPException(status_code=400, detail="Prompt must be at least 3 characters")
            
        scene_img = engine.generate_custom_scene(req.prompt, req.style_preset)
        
        file_id = f"scene_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
        out_path = os.path.join(OUTPUTS_DIR, file_id)
        scene_img.save(out_path, "JPEG", quality=92)
        
        return {
            "ok": True,
            "scene_id": file_id,
            "url": f"/outputs/{file_id}",
            "prompt": req.prompt
        }
    except Exception as e:
        logger.error(f"Error generating scene: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/composite")
async def composite_endpoint(req: CompositeRequest):
    """
    Composite Product + Shadow + Background Scene into final HD Mockup
    """
    try:
        # 1. Resolve Product Image
        product_img = None
        if req.product_type == "sample" and req.product_id:
            sample_path = os.path.join(SAMPLES_DIR, req.product_id)
            if os.path.exists(sample_path):
                product_img = Image.open(sample_path)
        elif req.product_type == "custom_id" and req.product_id:
            custom_path = os.path.join(OUTPUTS_DIR, req.product_id)
            if os.path.exists(custom_path):
                product_img = Image.open(custom_path)
        elif req.product_type == "base64" and req.product_base64:
            b64_data = req.product_base64.split(",")[-1]
            img_bytes = base64.b64decode(b64_data)
            product_img = Image.open(io.BytesIO(img_bytes))

        if not product_img:
            # Fallback to default sample
            product_img = Image.open(os.path.join(SAMPLES_DIR, "skincare_serum.png"))

        # 2. Resolve Background Scene Image
        bg_img = None
        if req.scene_type == "preset":
            bg_img = engine.get_preset_image(req.scene_id)
        elif req.scene_type == "custom":
            custom_scene_path = os.path.join(OUTPUTS_DIR, req.scene_id)
            if os.path.exists(custom_scene_path):
                bg_img = Image.open(custom_scene_path)
            else:
                bg_img = engine.get_preset_image("cafe_marble")

        if not bg_img:
            bg_img = engine.get_preset_image("cafe_marble")

        # 3. Perform Composite
        result_img = engine.composite_mockup(
            product_img=product_img,
            bg_img=bg_img,
            scale=req.scale,
            pos_x=req.pos_x,
            pos_y=req.pos_y,
            shadow_intensity=req.shadow_intensity,
            shadow_type=req.shadow_type,
            aspect_ratio=req.aspect_ratio
        )

        # 4. Save High-Definition Output
        out_filename = f"mockup_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
        out_path = os.path.join(OUTPUTS_DIR, out_filename)
        result_img.save(out_path, "JPEG", quality=95)

        return {
            "ok": True,
            "filename": out_filename,
            "url": f"/outputs/{out_filename}",
            "aspect_ratio": req.aspect_ratio,
            "dimensions": f"{result_img.width}x{result_img.height}",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"Error compositing mockup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8096, reload=True)
