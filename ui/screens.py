from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import time
import os
import requests

#my modules
from kiosk_py.ui import controller
from kiosk_py.services import api_client
from kiosk_py.nfc_utils import reader, writer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = 'your-secret-key'  # Add this near the top of screens.py
print(f"[DEBUG] Flask static folder: {app.static_folder}")

@app.context_processor
def inject_timestamp():
    return {'timestamp': int(time.time())}

def download_and_cache_images(attractions, static_folder):
    if not os.path.exists(static_folder):
        os.makedirs(static_folder)

    for attraction in attractions:
        ride_id = attraction.get('id')
        image_url = attraction.get('image')

        if not ride_id or not image_url:
            continue

        file_path = os.path.join(static_folder, f"{ride_id}.jpg")

        if os.path.exists(file_path):
            print(f"[CACHE] Image already exists for {ride_id}")
            continue

        try:
            print(f"[DOWNLOAD] Fetching image for {ride_id} from {image_url}")
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
            }
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"[SUCCESS] Image saved to {file_path}")

        except Exception as e:
            print(f"[ERROR] Failed to download image for {ride_id}: {e}")

@app.route('/')
def home():
    return render_template("welcome.html", time=time)

@app.route('/', endpoint='welcome')
def welcome():
    controller.display_welcome_screen()
    return render_template('welcome.html')

"""@app.route('/tap', endpoint='tap_card')
def tap_card():
    try:
        device_id = controller.handle_card_tap()
        print(f"[DEBUG] Simulated device ID: {device_id}")
        api_client.login()
        attractions = api_client.fetch_attractions()

        # Download images
        download_and_cache_images(attractions, static_folder=os.path.join(app.static_folder, 'images'))

        # Update image paths to local static URLs
        for attraction in attractions:
            attraction['image'] = url_for('static', filename=f"images/{attraction['id']}.jpg")
            print(f"[DEBUG] {attraction['name']} image URL: {attraction['image']}")

        return render_template('select.html', attractions=attractions)


    except RuntimeError as e:
        print(f"[ERROR] {e}")
        return render_template('error.html', message=str(e))"""


@app.route('/replace_prompt', methods=['GET', 'POST'])
def replace_prompt():
    reservation = controller.existing_reservation

    if request.method == 'POST':
        choice = request.form.get('choice')
        if choice == 'yes':
            return redirect(url_for('select_ride'))
        else:
            controller.last_tag = None # Allow re-tapping the same card
            return redirect(url_for('welcome'))

    return render_template('replace_prompt.html', reservation=reservation)


@app.route("/select", endpoint='select_ride')
def select_ride():
    attractions = api_client.fetch_attractions()

    download_and_cache_images(attractions, static_folder=os.path.join(app.static_folder, 'images'))

    for attraction in attractions:
        attraction['image'] = url_for('static', filename=f"images/{attraction['id']}.jpg")
        print(f"[DEBUG] Image URL for {attraction['name']}: {attraction['image']}")

    return render_template("select.html", attractions=attractions)

@app.route('/reserve/<ride_id>', methods=['get'])
def reserve(ride_id):
    try:
        result = controller.make_reservation(ride_id)
        session['selected_ride'] = result # ✅ Store for /write_card
        print("[DEBUG] Reservation result:", result)
        return render_template('success.html', reservation=result)
    except Exception as e:
        print(f"[ERROR] Reservation failed: {e}")
        return render_template('error.html', message=str(e))
    

@app.route('/write_card', methods=['POST'])
def write_card():
    try:
        ride = session.get("selected_ride")
        if not ride:
            return jsonify(success=False, message="No reservation in session")

        tag = reader.wait_for_card()
        writer.write_reservation_to_card(ride) #tag?

        return jsonify(success=True)

    except Exception as e:
        print(f"[ERROR] Failed to write to card: {e}")
        return jsonify(success=False, message=str(e))


@app.route("/success", endpoint='success')
def success():
    ride = session.get("selected_ride")
    if not ride:
        return redirect("/select")
    return render_template("success.html", reservation=ride)

@app.route('/confirm')
def confirm():
    return render_template("confirm.html")

