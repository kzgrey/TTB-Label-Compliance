import os
import uuid
import random
import shutil
import argparse
from PIL import Image, ImageDraw, ImageFont
import textwrap

# Compliance modes
MODES = ["clean_pass", "semantic_pass", "hard_fail", "needs_review"]

APPLICATION_TEMPLATE = """TTB ID: {ttbid}
VENDOR: {company}
ADDRESS: {address}
BRAND NAME: {brand}
CLASS/TYPE: {class_type}
NET CONTENTS: {net_contents}
ALCOHOL CONTENT: {abv}

GOVERNMENT WARNING: {warning}"""

def generate_fake_data():
    import random
    
    brands = ["SILVER OAK", "WILD CREEK", "OLD RELIABLE", "BLACK BARREL", "MOUNTAIN PEAK", "RIVER BEND"]
    companies = ["Silver Oak Distillers LLC", "Wild Creek Spirits Inc.", "Reliable Beverages Co.", "Peak Distillery LLC"]
    addresses = ["123 Distiller Way, NY, 10001", "456 Bourbon St, KY, 40202", "789 Vineyard Rd, CA, 94558"]
    class_types = ["STRAIGHT BOURBON WHISKEY", "VODKA", "LONDON DRY GIN", "TEQUILA BLANCO", "OTHER SPECIALTIES & PROPRIETARIES"]
    
    brand = random.choice(brands)
    class_type = random.choice(class_types)
    company = random.choice(companies)
    address = random.choice(addresses)
    
    # Random ABV between 30 and 50
    abv = str(random.randint(30, 50))
    
    # Random TTBID format
    ttbid = "".join([str(random.randint(0, 9)) for _ in range(14)])
    
    return {
        "ttbid": ttbid,
        "company": company,
        "address": address,
        "brand": brand,
        "class_type": class_type,
        "net_contents": "750 MILLILITERS",
        "abv": abv,
        "warning": "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems."
    }

def generate_label_image(output_path, data, mode):
    import random

    # 1. Variability in Canvas Size
    dimensions = [(600, 800), (800, 600), (700, 700), (500, 900)]
    width, height = random.choice(dimensions)

    # 2. Variability in Color Palettes
    palettes = [
        {"bg": (250, 240, 230), "border": (139, 0, 0), "text": (30, 30, 30)}, # Cream / Burgundy
        {"bg": (30, 30, 30), "border": (212, 175, 55), "text": (245, 245, 245)}, # Charcoal / Gold
        {"bg": (255, 255, 255), "border": (0, 51, 102), "text": (0, 0, 0)}, # White / Navy
        {"bg": (240, 248, 255), "border": (46, 139, 87), "text": (20, 40, 20)}, # Alice Blue / Sea Green
        {"bg": (253, 245, 230), "border": (105, 105, 105), "text": (50, 50, 50)}, # Old Lace / Dim Gray
    ]
    palette = random.choice(palettes)
    bg_color = palette["bg"]
    border_color = palette["border"]
    text_color = palette["text"]

    # Create a blank canvas
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts with sizes
    try:
        font_brand = ImageFont.load_default(size=48)
        font_class = ImageFont.load_default(size=24)
        font_details = ImageFont.load_default(size=20)
        font_warning = ImageFont.load_default(size=14)
    except Exception:
        font_brand = font_class = font_details = font_warning = ImageFont.load_default()

    # Modify data based on mode for the image
    img_data = data.copy()
    
    if mode == "semantic_pass":
        img_data["brand"] = "Sortilege"
        img_data["net_contents"] = "750 ml"
    elif mode == "hard_fail":
        img_data["abv"] = "45"
    elif mode == "needs_review":
        img_data["warning"] = "GOVERNMENT WARNING: Please drink responsibly."
        img_data["brand"] = "SORT\\!EGE"

    # 3. Variability in Borders
    border_style = random.choice(["double", "single", "thick", "none"])
    if border_style in ["double", "single", "thick"]:
        b_width = 8 if border_style == "thick" else 4
        draw.rectangle([20, 20, width-20, height-20], outline=border_color, width=b_width)
        if border_style == "double":
            draw.rectangle([35, 35, width-35, height-35], outline=border_color, width=2)

    # Helper function to center text
    def draw_centered_text(y, text, font, fill=text_color):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (width - text_w) / 2
        draw.text((x, y), text, font=font, fill=fill)

    # 4. Variability in Text Layout (Spacing and Positions)
    y_brand = random.randint(60, 150)
    draw_centered_text(y_brand, img_data["brand"], font_brand)
    
    y_class = y_brand + random.randint(60, 100)
    draw_centered_text(y_class, img_data["class_type"], font_class)

    # Optional Divider
    if random.choice([True, False]):
        div_y = y_class + 50
        draw.line([(width/2)-100, div_y, (width/2)+100, div_y], fill=border_color, width=random.choice([1, 3]))

    # ABV and Net Contents
    details_y = y_class + random.randint(100, 200)
    abv_text = f"ALC. BY VOL. {img_data['abv']}%"
    net_text = f"{img_data['net_contents']}"

    layout_style = random.choice(["split", "stacked_center", "stacked_left"])
    if layout_style == "split":
        # Split left/right
        draw.text((80, details_y), abv_text, font=font_details, fill=text_color)
        bbox = draw.textbbox((0, 0), net_text, font=font_details)
        draw.text((width - 80 - (bbox[2] - bbox[0]), details_y), net_text, font=font_details, fill=text_color)
    elif layout_style == "stacked_center":
        draw_centered_text(details_y, abv_text, font=font_details)
        draw_centered_text(details_y + 40, net_text, font=font_details)
    else: # stacked_left
        draw.text((80, details_y), abv_text, font=font_details, fill=text_color)
        draw.text((80, details_y + 40), net_text, font=font_details, fill=text_color)

    # 5. Government Warning (Bottom)
    warning_box_y = height - random.randint(150, 250)
    
    # Optional Warning Box
    if random.choice([True, False]):
        draw.rectangle([40, warning_box_y, width-40, height-40], outline=text_color, width=2)
    
    if "warning" in img_data:
        # Wrap the warning text dynamically based on width
        lines = textwrap.wrap(img_data["warning"], width=int(width / 9))
        y_offset = warning_box_y + 15
        align_center = random.choice([True, False])
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_warning)
            line_w = bbox[2] - bbox[0]
            x_warn = (width - line_w) / 2 if align_center else 50
            draw.text((x_warn, y_offset), line, font=font_warning, fill=text_color)
            y_offset += 20

    # Save image
    img.save(output_path)

def generate_sample(output_dir, mode):
    sample_id = str(uuid.uuid4())
    sample_dir = os.path.join(output_dir, sample_id)
    os.makedirs(sample_dir, exist_ok=True)
    
    # Generate fake application data
    data = generate_fake_data()
    
    # Generate label image
    img_path = os.path.join(sample_dir, "label.png")
    generate_label_image(img_path, data, mode)
    
    # Write templated application text
    app_path = os.path.join(sample_dir, "application.txt")
    app_text = APPLICATION_TEMPLATE.format(**data)
    with open(app_path, 'w') as f:
        f.write(app_text)
    
    # Write metadata info
    meta_path = os.path.join(sample_dir, "metadata.json")
    with open(meta_path, 'w') as f:
        f.write(f'{{"mode": "{mode}"}}\n')
    
    print(f"Generated sample {sample_id} | Mode: {mode}")

def main():
    parser = argparse.ArgumentParser(description="Generate sample labels and applications.")
    parser.add_argument("--count", type=int, default=1, help="Number of samples to generate")
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    output_dir = os.path.join(project_root, "data", "generated")

    print(f"Generating {args.count} sample(s) into {output_dir}...")
    for _ in range(args.count):
        mode = random.choice(MODES)
        generate_sample(output_dir, mode)
    print("Done!")

if __name__ == "__main__":
    main()
