import os
import requests

ride_id = "b49d0897-247e-4499-b54c-b7bbd0acf6b6"
image_url = "https://lqrpuscache.loqueue.accesso.com/api/api/guest/rides/b49d0897-247e-4499-b54c-b7bbd0acf6b6/images?v=5ea82c9def9a711d134137bc0206aae1"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://your-app-url.com",  # Optional: mimic the origin
    # "Authorization": "Bearer YOUR_TOKEN"  # Uncomment if needed
}

output_dir = os.path.join("static", "images")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, f"{ride_id}.jpg")

try:
    print(f"[INFO] Downloading image for ride ID {ride_id}...")
    response = requests.get(image_url, headers=headers, timeout=10)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"[SUCCESS] Image saved to {output_path}")

except Exception as e:
    print(f"[ERROR] Failed to download image: {e}")
