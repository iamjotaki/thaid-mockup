import os
import io
import time
import math
import random
import logging
import urllib.parse
import urllib.request
import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, ImageDraw

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ThaiDMockupEngine")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRESETS_DIR = os.path.join(BASE_DIR, "assets", "presets")
SAMPLES_DIR = os.path.join(BASE_DIR, "assets", "sample_products")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(PRESETS_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Curated Luxury Presets metadata
PRESET_TEMPLATES = [
    {
        "id": "cafe_marble",
        "name": "Luxury Cafe & Marble",
        "name_th": "โต๊ะหินอ่อนคาเฟ่หรู",
        "category": "lifestyle",
        "description": "โต๊ะหินอ่อน Carrara สีขาว ในคาเฟ่หรู มีแสงแดดยามเช้าและโบเก้อบอุ่น",
        "prompt": "luxury white Carrara marble tabletop in upscale cafe, morning golden sunlight, soft warm bokeh background, architectural depth, commercial product photography, 8k, photorealistic",
        "shadow_type": "soft_contact",
        "ambient_color": (245, 235, 225)
    },
    {
        "id": "nature_wood",
        "name": "Minimalist Nature & Oak",
        "name_th": "แท่นไม้โอ๊ค & เงาใบไม้ธรรมชาติ",
        "category": "organic",
        "description": "แท่นไม้โอ๊คธรรมชาติ มีเงาตกกระทบของใบมอนสเตอร่า แสงแดดธรรมชาตินุ่มนวล",
        "prompt": "natural warm oak wooden pedestal, soft tropical monstera leaves cast shadows, bright airy studio lighting, earthy minimalist, 8k, photorealistic",
        "shadow_type": "directional_leaf",
        "ambient_color": (240, 238, 220)
    },
    {
        "id": "luxury_spa",
        "name": "Luxury Zen Spa & Stone",
        "name_th": "หินสปาสีดำ & ผิวน้ำริ้วคลื่น",
        "category": "beauty",
        "description": "หินแม่น้ำสีดำเปียกน้ำ ผิวน้ำกระเพื่อมบางๆ ละอองไอน้ำ และดอกกล้วยไม้เบลอหลัง",
        "prompt": "dark wet zen river stones surface, gentle water ripples, faint aromatic steam mist, exotic orchid flower in background, dim luxury hotel spa mood, 8k, photorealistic",
        "shadow_type": "tight_wet",
        "ambient_color": (40, 50, 55)
    },
    {
        "id": "podium_minimal",
        "name": "Architectural Pastel Podium",
        "name_th": "โพเดียมทรงกระบอกมินิมอล",
        "category": "studio",
        "description": "แท่นโพเดียมคอนกรีตทรงกระบอกสีพาสเทล ผนังปูนเปลือย แสงแดดส่องเป็นมุมคมชัด",
        "prompt": "minimalist cylindrical concrete podium, soft beige pastel plaster wall, hard geometric angled sunbeam shadows, contemporary architectural showcase, 8k, photorealistic",
        "shadow_type": "sharp_geometric",
        "ambient_color": (235, 225, 215)
    },
    {
        "id": "cozy_living",
        "name": "Warm Scandinavian Living",
        "name_th": "มุมห้องสแกนดิเนเวียอบอุ่น",
        "category": "lifestyle",
        "description": "ชั้นไม้สไตล์สแกนดิเนเวีย ผ้าม่านลินินสีครีม แสงไฟอบอุ่นสไตล์ Cozy Home",
        "prompt": "warm Scandinavian light wood sideboard, neutral textured linen drapery, warm interior softbox lighting, clean lifestyle aesthetic, 8k, photorealistic",
        "shadow_type": "diffuse",
        "ambient_color": (245, 238, 225)
    },
    {
        "id": "neon_cyberpunk",
        "name": "Cyberpunk Studio Neon",
        "name_th": "สตูดิโอดำขลับ แสงไฟนีออน",
        "category": "gadget",
        "description": "พื้นกระจกสะท้อนสีดำ แสง Rim Light นีออนสีน้ำเงินและชมพูมาเจนต้า โดดเด่นล้ำสมัย",
        "prompt": "black glossy reflective studio floor, cinematic deep blue and vibrant neon magenta rim lights, dark moody commercial lighting, 8k, photorealistic",
        "shadow_type": "reflective",
        "ambient_color": (30, 20, 45)
    },
    {
        "id": "golden_beach",
        "name": "Golden Hour Beach Dunes",
        "name_th": "หาดทรายขาว & แสงอาทิตย์ตกดิน",
        "category": "outdoor",
        "description": "พื้นทรายขาวละเอียด แสงสีทองยามพระอาทิตย์ตก ละมุนตา สไตล์สินค้าซัมเมอร์",
        "prompt": "fine powdery white sand beach dunes, warm sunset golden hour lighting, gentle ocean sea breeze backdrop in soft focus, 8k, photorealistic",
        "shadow_type": "long_sunset",
        "ambient_color": (250, 220, 180)
    },
    {
        "id": "studio_pastel",
        "name": "High-Key Studio Cyclorama",
        "name_th": "สตูดิโอฉากโค้งโมโนโครม",
        "category": "studio",
        "description": "สตูดิโอฉากโค้งไร้รอยต่อสีพีชพาสเทล แสงสตูดิโอ Softbox ด้านบน สว่างใส สะอาดตา",
        "prompt": "seamless curved pastel peach studio cyclorama wall, soft diffuse commercial top softbox light, clean high-key product showcase, 8k, photorealistic",
        "shadow_type": "soft_drop",
        "ambient_color": (250, 235, 230)
    }
]

# Aspect ratio definitions
ASPECT_RATIOS = {
    "1:1": (1080, 1080),   # Shopee, Lazada, Square IG
    "4:5": (1080, 1350),   # Facebook Feed, IG Portrait
    "9:16": (1080, 1920)   # TikTok Shop, Reels, IG Stories
}

def get_gemini_keys():
    """Retrieve Gemini keys from env or fallback list"""
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and len(env_key) > 10:
        return [k.strip() for k in env_key.split(",") if len(k.strip()) > 10]
    return []

def call_gemini_chat(prompt: str, system_instruction: str = None) -> str:
    """Enhance background generation prompt using Gemini"""
    keys = get_gemini_keys()
    if not keys:
        return prompt

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300}
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    import json
    data = json.dumps(payload).encode("utf-8")
    
    # Try multiple keys with rotation
    for key in random.sample(keys, min(len(keys), 3)):
        for model in ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-2.0-flash"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    cand = res.get("candidates", [])
                    if cand:
                        text = cand[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            return text.strip()
            except Exception as e:
                logger.warning(f"Gemini call error on {model}: {e}")
                continue
    return prompt

def remove_background(image: Image.Image) -> Image.Image:
    """
    Automatic background removal / matting pipeline.
    If image already has transparency, refines edge alpha.
    If solid/near-solid background, detects corner background color,
    computes color delta map, and generates smooth antialiased alpha.
    """
    img = image.convert("RGBA")
    w, h = img.size
    np_img = np.array(img)
    
    # Check if already transparent
    alpha_channel = np_img[:, :, 3]
    if np.min(alpha_channel) < 50:
        # Already has transparent areas. Trim and return
        bbox = img.getbbox()
        if bbox:
            return img.crop(bbox)
        return img

    # Sample corners to find background color
    corners = [
        np_img[0, 0, :3],
        np_img[0, w-1, :3],
        np_img[h-1, 0, :3],
        np_img[h-1, w-1, :3],
        np_img[0, w//2, :3],
        np_img[h-1, w//2, :3]
    ]
    bg_color = np.median(corners, axis=0)

    # Compute Euclidean distance from bg color in RGB
    rgb = np_img[:, :, :3].astype(np.float32)
    diff = np.sqrt(np.sum((rgb - bg_color) ** 2, axis=2))

    # Thresholds: low distance is background, high distance is foreground
    thresh_low = 25.0
    thresh_high = 75.0

    # Smooth transition alpha
    alpha = np.clip((diff - thresh_low) / (thresh_high - thresh_low), 0.0, 1.0) * 255.0
    alpha = alpha.astype(np.uint8)

    # Clean up mask with morphological-like filter via PIL
    alpha_img = Image.fromarray(alpha, mode="L")
    alpha_img = alpha_img.filter(ImageFilter.MedianFilter(size=3))
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.2))

    # Apply alpha back
    np_img[:, :, 3] = np.array(alpha_img)
    result = Image.fromarray(np_img, mode="RGBA")

    # Crop to non-transparent bounding box
    bbox = result.getbbox()
    if bbox:
        # Add 5px padding
        pad = 5
        bbox = (max(0, bbox[0]-pad), max(0, bbox[1]-pad), min(w, bbox[2]+pad), min(h, bbox[3]+pad))
        result = result.crop(bbox)

    return result

def synthesize_shadows(product_img: Image.Image, canvas_w: int, canvas_h: int, 
                       pos_x: float, pos_y: float, scale: float, 
                       shadow_type: str = "soft_contact", intensity: float = 0.65) -> Image.Image:
    """
    Synthesizes hyper-realistic dual-layer shadows:
    1. Ambient Occlusion Contact Shadow: Dark, sharp, tight ellipse directly at base.
    2. Directional Ground Cast Shadow: Skewed, soft, feathered shadow projected on surface.
    """
    shadow_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    prod_w, prod_h = product_img.size
    
    # Target product dimensions on canvas
    target_w = int(canvas_w * scale)
    target_h = int(prod_h * (target_w / prod_w))

    # Center-X, Bottom-Y anchor
    prod_left = int(canvas_w * pos_x - target_w / 2)
    prod_top = int(canvas_h * pos_y - target_h)
    prod_bottom = prod_top + target_h
    base_center_x = int(canvas_w * pos_x)
    base_center_y = prod_bottom

    # 1. Layer: Contact Shadow (Tight Ambient Occlusion Ellipse)
    contact_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    contact_draw = ImageDraw.Draw(contact_layer)

    ao_width = int(target_w * 0.85)
    ao_height = int(target_w * 0.14)
    ao_bbox = [
        base_center_x - ao_width // 2,
        base_center_y - ao_height // 2 - 2,
        base_center_x + ao_width // 2,
        base_center_y + ao_height // 2 - 2
    ]
    ao_alpha = int(220 * intensity)
    contact_draw.ellipse(ao_bbox, fill=(15, 12, 10, ao_alpha))
    contact_layer = contact_layer.filter(ImageFilter.GaussianBlur(radius=max(3, int(target_w * 0.025))))

    # 2. Layer: Directional Cast Shadow (Based on Product Silhouette)
    cast_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    
    # Extract alpha mask of product resized to target
    resized_prod = product_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    alpha = resized_prod.split()[3]
    
    # Create black silhouette
    silhouette = Image.new("RGBA", (target_w, target_h), (20, 18, 16, 255))
    silhouette.putalpha(alpha)

    # Skew and squash silhouette to represent ground plane projection
    # Angle and length based on shadow_type
    if shadow_type == "long_sunset":
        squash_y = 0.35
        offset_x = int(target_w * 0.45)
        offset_y = int(target_h * 0.15)
        blur_rad = int(target_w * 0.08)
        cast_alpha = int(140 * intensity)
    elif shadow_type == "sharp_geometric":
        squash_y = 0.28
        offset_x = int(target_w * 0.25)
        offset_y = int(target_h * 0.05)
        blur_rad = int(target_w * 0.03)
        cast_alpha = int(170 * intensity)
    elif shadow_type == "reflective":
        # Glossy reflection underneath
        squash_y = 0.7
        offset_x = 0
        offset_y = 0
        blur_rad = int(target_w * 0.02)
        cast_alpha = int(90 * intensity)
    else:  # soft_contact, diffuse, directional_leaf
        squash_y = 0.22
        offset_x = int(target_w * 0.15)
        offset_y = int(target_h * 0.04)
        blur_rad = int(target_w * 0.06)
        cast_alpha = int(150 * intensity)

    # Squash silhouette vertically and flip
    shadow_h = max(10, int(target_h * squash_y))
    skewed_shadow = silhouette.resize((target_w, shadow_h), Image.Resampling.BILINEAR)
    if shadow_type == "reflective":
        skewed_shadow = ImageOps.flip(skewed_shadow)

    # Fade shadow towards top of shadow (gradient alpha falloff)
    np_shadow = np.array(skewed_shadow)
    grad = np.linspace(cast_alpha, 0, shadow_h).astype(np.uint8)
    for row in range(shadow_h):
        np_shadow[row, :, 3] = np.clip(np_shadow[row, :, 3].astype(np.float32) * (grad[row] / 255.0), 0, 255).astype(np.uint8)
    
    soft_shadow = Image.fromarray(np_shadow, mode="RGBA")
    soft_shadow = soft_shadow.filter(ImageFilter.GaussianBlur(radius=blur_rad))

    # Paste onto cast_layer
    cast_paste_x = prod_left + offset_x
    cast_paste_y = base_center_y - int(shadow_h * 0.15) + offset_y
    cast_layer.paste(soft_shadow, (cast_paste_x, cast_paste_y), soft_shadow)

    # Merge contact and cast shadows
    shadow_layer = Image.alpha_composite(shadow_layer, cast_layer)
    shadow_layer = Image.alpha_composite(shadow_layer, contact_layer)
    return shadow_layer

def composite_mockup(product_img: Image.Image, bg_img: Image.Image, 
                     scale: float = 0.58, pos_x: float = 0.5, pos_y: float = 0.72,
                     shadow_intensity: float = 0.65, shadow_type: str = "soft_contact",
                     aspect_ratio: str = "1:1") -> Image.Image:
    """
    Main Compositing Engine:
    - Crops/pads background to target aspect ratio (1:1, 4:5, 9:16)
    - Positions product at (pos_x, pos_y)
    - Generates & composites realistic dual-layer contact & cast shadows
    - Performs ambient lighting adjustment on product
    - Blends everything into high-definition commercial output
    """
    target_size = ASPECT_RATIOS.get(aspect_ratio, (1080, 1080))
    canvas_w, canvas_h = target_size

    # 1. Prepare Background Image (Cover Fit)
    bg_w, bg_h = bg_img.size
    bg_ratio = bg_w / bg_h
    target_ratio = canvas_w / canvas_h

    if bg_ratio > target_ratio:
        new_h = canvas_h
        new_w = int(canvas_h * bg_ratio)
    else:
        new_w = canvas_w
        new_h = int(canvas_w / bg_ratio)

    resized_bg = bg_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    crop_x = (new_w - canvas_w) // 2
    crop_y = (new_h - canvas_h) // 2
    canvas = resized_bg.crop((crop_x, crop_y, crop_x + canvas_w, crop_y + canvas_h)).convert("RGBA")

    # 2. Extract Clean Product with Alpha
    product_rgba = remove_background(product_img)

    # 3. Calculate Product Placement
    prod_orig_w, prod_orig_h = product_rgba.size
    target_prod_w = int(canvas_w * scale)
    target_prod_h = int(prod_orig_h * (target_prod_w / prod_orig_w))

    # Keep product within reasonable vertical bounds
    if target_prod_h > int(canvas_h * 0.75):
        target_prod_h = int(canvas_h * 0.75)
        target_prod_w = int(prod_orig_w * (target_prod_h / prod_orig_h))

    resized_product = product_rgba.resize((target_prod_w, target_prod_h), Image.Resampling.LANCZOS)

    paste_x = int(canvas_w * pos_x - target_prod_w / 2)
    paste_y = int(canvas_h * pos_y - target_prod_h)

    # 4. Synthesize Shadows
    shadow_layer = synthesize_shadows(
        product_rgba, canvas_w, canvas_h, 
        pos_x, pos_y, scale, 
        shadow_type=shadow_type, intensity=shadow_intensity
    )

    # 5. Ambient Light Grading on Product
    # Sample ambient tone around ground/placement area on background
    sample_rect = (
        max(0, paste_x),
        max(0, paste_y),
        min(canvas_w, paste_x + target_prod_w),
        min(canvas_h, paste_y + target_prod_h + 30)
    )
    sample_patch = canvas.crop(sample_rect).convert("RGB")
    stat = ImageOps.posterize(sample_patch, 2)
    stat_np = np.array(sample_patch)
    mean_color = np.mean(stat_np, axis=(0, 1))  # [R, G, B]
    
    # Apply soft ambient tint (5% mix)
    tint_layer = Image.new("RGBA", (target_prod_w, target_prod_h), 
                           (int(mean_color[0]), int(mean_color[1]), int(mean_color[2]), 18))
    
    # Only tint non-transparent pixels
    product_with_tint = resized_product.copy()
    tint_layer.putalpha(product_with_tint.split()[3].point(lambda a: int(a * 0.08)))
    product_with_tint = Image.alpha_composite(product_with_tint, tint_layer)

    # 6. Composite Layers: Background -> Shadow -> Product
    canvas = Image.alpha_composite(canvas, shadow_layer)
    canvas.paste(product_with_tint, (paste_x, paste_y), product_with_tint)

    # 7. Convert to RGB High Quality
    final_output = canvas.convert("RGB")
    return final_output

def generate_custom_scene(prompt: str, style_preset_id: str = None) -> Image.Image:
    """
    Generate custom luxury background scene using AI (Gemini prompt enrichment + Image Gen)
    """
    # 1. Enrich prompt with Gemini if available
    sys_prompt = (
        "You are an expert commercial product photographer. Convert the user's scene description "
        "into a detailed, photorealistic prompt for generating an empty product photography backdrop. "
        "Ensure the scene has a clear flat surface (tabletop, podium, marble, floor) in the lower half "
        "for placing a product, with beautiful commercial lighting (depth of field, soft bokeh, 8k, ultra-detailed). "
        "Do NOT place any products or text in the center."
    )
    enhanced_prompt = call_gemini_chat(prompt, system_instruction=sys_prompt)
    if not enhanced_prompt or len(enhanced_prompt) < 10:
        enhanced_prompt = prompt + ", commercial product photography empty backdrop, luxury surface, soft natural lighting, depth of field, 8k"

    # 2. Fetch image via Pollinations Flux API
    seed = random.randint(100, 999999)
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(enhanced_prompt)}?width=1024&height=1024&nologo=true&seed={seed}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            img = Image.open(io.BytesIO(data))
            return img
    except Exception as e:
        logger.error(f"Error generating custom scene: {e}")
        # Fallback to default preset
        return get_preset_image("cafe_marble")

def get_preset_image(preset_id: str) -> Image.Image:
    """Load pre-rendered preset background from disk or create dynamic fallback"""
    preset_file = os.path.join(PRESETS_DIR, f"{preset_id}.jpg")
    if os.path.exists(preset_file):
        try:
            return Image.open(preset_file)
        except Exception:
            pass
    
    # If file not found yet, create dynamic luxury gradient backdrop
    img = Image.new("RGB", (1024, 1024), (240, 235, 230))
    draw = ImageDraw.Draw(img)
    # Draw luxury gradient floor and wall
    for y in range(600):
        c = int(245 - (y / 600) * 20)
        draw.line([(0, y), (1024, y)], fill=(c, c, c-5))
    # Horizon line
    draw.line([(0, 600), (1024, 600)], fill=(210, 205, 200), width=2)
    # Floor
    for y in range(600, 1024):
        c = int(225 + ((y - 600) / 424) * 20)
        draw.line([(0, y), (1024, y)], fill=(c, c-2, c-6))
    return img

def create_sample_products_if_missing():
    """Generates 5 realistic sample transparent PNG products for quick demo"""
    samples = [
        ("skincare_serum.png", "Serum Dropper Bottle"),
        ("perfume_bottle.png", "Luxury Perfume Bottle"),
        ("coffee_tumbler.png", "Matte Black Tumbler"),
        ("cosmetic_jar.png", "Rose Gold Cream Jar"),
        ("supplement_bottle.png", "White Health Bottle")
    ]
    
    for filename, name in samples:
        path = os.path.join(SAMPLES_DIR, filename)
        if os.path.exists(path):
            continue
            
        img = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if filename == "skincare_serum.png":
            # Amber bottle body
            draw.rounded_rectangle([130, 240, 270, 520], radius=18, fill=(160, 90, 40, 240))
            # Glass highlight
            draw.rounded_rectangle([140, 250, 160, 510], radius=8, fill=(255, 200, 150, 80))
            # Gold neck
            draw.rectangle([170, 180, 230, 240], fill=(212, 175, 55, 255))
            # Black rubber dropper tip
            draw.ellipse([180, 100, 220, 185], fill=(30, 30, 30, 255))
            # Label
            draw.rectangle([145, 320, 255, 440], fill=(245, 242, 235, 245))
            draw.line([(160, 350), (240, 350)], fill=(40, 40, 40, 200), width=3)
            draw.line([(170, 370), (230, 370)], fill=(120, 120, 120, 180), width=2)
            draw.line([(180, 390), (220, 390)], fill=(120, 120, 120, 180), width=2)
            
        elif filename == "perfume_bottle.png":
            # Crystal glass bottle
            draw.rounded_rectangle([110, 200, 290, 490], radius=12, fill=(230, 240, 245, 180))
            # Gold liquid inside
            draw.rounded_rectangle([125, 240, 275, 475], radius=8, fill=(240, 195, 90, 210))
            # Spray nozzle
            draw.rectangle([185, 150, 215, 200], fill=(220, 220, 225, 255))
            # Cap
            draw.rounded_rectangle([165, 90, 235, 150], radius=6, fill=(25, 25, 25, 255))
            # Perfume Label
            draw.rectangle([150, 310, 250, 410], fill=(255, 255, 255, 240))
            draw.line([(165, 340), (235, 340)], fill=(20, 20, 20, 220), width=3)
            draw.line([(175, 360), (225, 360)], fill=(100, 100, 100, 180), width=2)

        elif filename == "coffee_tumbler.png":
            # Matte black tumbler body
            draw.polygon([(140, 180), (260, 180), (240, 520), (160, 520)], fill=(32, 33, 36, 255))
            # Rim highlight
            draw.line([(148, 190), (165, 510)], fill=(80, 80, 85, 100), width=4)
            # Steel lid
            draw.rounded_rectangle([135, 130, 265, 180], radius=8, fill=(180, 185, 190, 255))
            draw.ellipse([185, 110, 215, 135], fill=(32, 33, 36, 255))

        elif filename == "cosmetic_jar.png":
            # Glass jar body
            draw.rounded_rectangle([100, 300, 300, 480], radius=24, fill=(240, 242, 245, 220))
            # Cream inside
            draw.rounded_rectangle([115, 330, 285, 465], radius=16, fill=(255, 248, 235, 240))
            # Rose gold lid
            draw.rounded_rectangle([90, 220, 310, 305], radius=14, fill=(225, 155, 140, 255))
            draw.line([(100, 250), (300, 250)], fill=(255, 220, 210, 180), width=4)

        else:  # supplement_bottle.png
            # White matte pill bottle
            draw.rounded_rectangle([125, 200, 275, 500], radius=20, fill=(248, 249, 250, 255))
            # Blue cap
            draw.rounded_rectangle([150, 120, 250, 200], radius=8, fill=(0, 113, 227, 255))
            # Label
            draw.rectangle([130, 270, 270, 430], fill=(235, 245, 255, 255))
            draw.line([(150, 310), (250, 310)], fill=(0, 113, 227, 240), width=4)
            draw.line([(155, 340), (245, 340)], fill=(100, 110, 120, 200), width=2)
            draw.line([(160, 365), (240, 365)], fill=(100, 110, 120, 200), width=2)
            
        img.save(path, "PNG")
        logger.info(f"Generated sample product: {path}")

# Initialize samples on import
create_sample_products_if_missing()
