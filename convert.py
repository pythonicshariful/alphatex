from PIL import Image
import os
import shutil

source_image = r"C:\Users\USER\.gemini\antigravity-ide\brain\35f1f20e-64c8-4746-bf69-e4c73b768a72\hero_wide_jpg_1782285366760.png"
dest_image = r"g:\Personal\Illyen\static\images\hero_wide.webp"

try:
    img = Image.open(source_image)
    img.save(dest_image, 'WEBP')
    print("Converted successfully to WebP")
except Exception as e:
    print(f"Error converting to webp: {e}")
    shutil.copy2(source_image, r"g:\Personal\Illyen\static\images\hero_wide.png")
    print("Copied as PNG instead")
