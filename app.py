from flask import Flask, request, send_file
from PIL import Image, ImageEnhance, ImageOps, ImageFont, ImageDraw
from io import BytesIO
import base64
from datetime import datetime
import os

app = Flask(__name__)

def apply_bw_high_contrast(img):
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageOps.colorize(img, black="#1c1c1c", white="#fcecc1")
    return img.convert("RGB")

def apply_sepia(img):
    img = img.convert("RGB")
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = pixels[x, y]
            tr = int(0.393 * r + 0.769 * g + 0.189 * b)
            tg = int(0.349 * r + 0.686 * g + 0.168 * b)
            tb = int(0.272 * r + 0.534 * g + 0.131 * b)
            pixels[x, y] = (min(tr, 255), min(tg, 255), min(tb, 255))
    return img

def apply_color_boost(img):
    return ImageEnhance.Color(img).enhance(2.0)

def apply_cool_tone(img):
    r, g, b = img.split()
    r = r.point(lambda i: max(0, i - 20))
    b = b.point(lambda i: min(255, i + 30))
    return Image.merge("RGB", (r, g, b))

def create_photobooth_strip(images, bgcolor="black", selected_filter="bw_high_contrast"):
    width, height = 400, 400
    border = 5
    gap = 10
    date_height = 100

    total_height = (height * len(images)) + (gap * (len(images) - 1)) + (border * 2) + date_height
    strip = Image.new("RGB", (width + border * 2, total_height), bgcolor)
    filter_map = {
        "bw_high_contrast": apply_bw_high_contrast,
        "sepia": apply_sepia,
        "color_boost": apply_color_boost,
        "cool_tone": apply_cool_tone,
        "no_filter": lambda img: img
    }
    filter_func = filter_map.get(selected_filter, lambda img: img)

    for i, img in enumerate(images):
        img = img.convert("RGB").resize((width, height))
        frame = filter_func(img)
        top = border + i * (height + gap)
        strip.paste(frame, (border, top))

    draw = ImageDraw.Draw(strip)
    date_str = datetime.now().strftime("%B %d, %Y")
    font_path = "fonts/Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        raise FileNotFoundError("Font file not found at: fonts/Roboto-Regular.ttf")

    font = ImageFont.truetype(font_path, 20)
    text_color = "white" if bgcolor == "black" else "black"
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (strip.width - text_width) // 2
    y = total_height - date_height + (date_height - text_height) // 2
    draw.text((x, y), date_str, font=font, fill=text_color)

    return strip


@app.route('/')
def index():
    return '''
 <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>photobooth :)</title>

    <link href="https://fonts.googleapis.com/css2?family=Comic+Neue&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Ribeye&display=swap" rel="stylesheet">

    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.css" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.5.13/cropper.min.js"></script>


    <style>
        body {
            font-family: 'Ribeye', cursive;
            background-color: #BADFF3;
            color: #222;
            text-align: center;
            padding: 30px;
        }

        h2 {
            font-size: 3rem;
            margin-bottom: 10px;
            color: #3f51b5;
            text-shadow: 1px 1px 2px #ccc;
        }

        #camera {
            border: 5px solid #3f51b5;
            border-radius: 10px;
            margin: 15px auto;
            display: block;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
        }

        #captures {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 6px;
        }

        #captures img {
            border: 3px solid #3f51b5;
            border-radius: 4px;
            width: 100px;
            height: 100px;
            object-fit: cover;
            box-shadow: 2px 2px 6px rgba(0, 0, 0, 0.3);
        }

        h4{
        you can either upload images (one by one) or capture them}

        button, input[type="submit"] {
            font-family: 'Comic Neue', cursive;
            background-color: #3f51b5;
            color: white;
            padding: 6px 14px;
            margin: 10px;
            border: none;
            border-radius: 6px;
            font-size: 0.9rem;
            text-transform: uppercase;
            cursor: pointer;
            box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            font-weight: bold;
            letter-spacing: 1px;
            transition: background-color 0.2s ease;
        }

        button:hover, input[type="submit"]:hover {
            background-color: #2c3ea7;
        }

        select, input[type="file"] {
            margin-top: 10px;
            padding: 8px;
            border: 2px solid #3f51b5;
            border-radius: 5px;
            background-color: white;
            color: #3f51b5;
            font-weight: bold;
        }

        form {
            margin-top: 20px;
        }

        label {
            font-size: 1.2rem;
            margin-right: 10px;
            color: #3f51b5;
        }

        #cropModal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: #000000cc;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }

        #cropModal > div {
            background: white;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }

        #cropModal img {
            max-width: 100%;
            max-height: 80vh;
        }

        #cropModal {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.85);
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

#cropModal .modal-content {
    background: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    max-width: 90vw;
}

#cropImage {
    width: 400px;
    height: 400px;
    object-fit: cover;
    border: 2px solid black;
}

    </style>
</head>
<body>
    <h2>photobooth :)</h2>
    <h4> you can either upload images (one by one) or capture them </h4>

    <label>number of photos?</label>
    <select id="photoCountSelector" onchange="setPhotoCount()">
        <option value="4">4</option>
        <option value="3">3</option>
        <option value="2">2</option>
    </select>

    <video id="camera" autoplay playsinline width="400" height="400" style="object-fit: cover;"></video><br>
    <button onclick="capture()">capture</button>

    <br><br>
    <input type="file" id="uploadInput" accept="image/*" multiple><br><br>


    <div id="captures"></div>

    <form id="photoForm" method="POST" action="/generate">
      <label>Background:</label>
<select name="bgcolor" id="bgcolor">
    <option value="black" selected>Black</option>
    <option value="white">White</option>
</select>
<label for="filter">Filter:</label>
    <select name="filter">
        <option value="bw_high_contrast">BW High Contrast</option>
        <option value="sepia">Sepia</option>
        <option value="color_boost">Color Boost</option>
        <option value="cool_tone">Cool Tone</option>
        <option value="no_filter">No Filter</option>
    </select>
        <br><input type="submit" value="Create Strip" id="submitBtn">
        <button type="button" onclick="resetImages()">reset</button>
    </form>

    <!-- Cropping Modal -->
    <div id="cropModal">
        <div class="modal-content">
    <img id="cropImage" />
    <br><br>
    <button onclick="cropAndSave()">Crop</button>
    <button onclick="closeCropper()">Cancel</button>
  </div>
</div>

   <script>
let count = 0;
let total = 4;

const video = document.getElementById('camera');
const uploadInput = document.getElementById('uploadInput');
const capturesDiv = document.getElementById('captures');
const submitBtn = document.getElementById('submitBtn');
const form = document.getElementById('photoForm');

navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;
    })
    .catch(() => {
        alert("Could not access camera.");
    });

function setPhotoCount() {
    total = parseInt(document.getElementById('photoCountSelector').value);
    resetImages();
    generateHiddenInputs();
}
window.setPhotoCount = setPhotoCount;

function generateHiddenInputs() {
    form.querySelectorAll('input[name^="img"]').forEach(el => el.remove());
    for (let i = 1; i <= total; i++) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = `img${i}`;
        form.appendChild(input);
    }
}

function getImgInputs() {
    return Array.from(form.querySelectorAll('input[name^="img"]'));
}

function capture() {
    if (count >= total) return alert(`Limit reached (${total} photos)`);

    const canvas = document.createElement('canvas');
    canvas.width = 400;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, 400, 400);
    const dataURL = canvas.toDataURL('image/jpeg');
    addImage(dataURL);
}
window.capture = capture;

function addImage(dataURL) {
    if (count >= total) return;

    const img = document.createElement('img');
    img.src = dataURL;
    img.width = 100;
    capturesDiv.appendChild(img);

    getImgInputs()[count].value = dataURL;
    count++;
    if (count === total) submitBtn.disabled = false;
}

function resetImages() {
    count = 0;
    capturesDiv.innerHTML = '';
    getImgInputs().forEach(input => input.value = '');
    submitBtn.disabled = true;
}
window.resetImages = resetImages;
let cropper;

function showCropper(imgSrc) {
    const cropImage = document.getElementById('cropImage');
    cropImage.src = imgSrc;
    document.getElementById('cropModal').style.display = 'flex';

    setTimeout(() => {
        cropper = new Cropper(cropImage, {
            aspectRatio: 1,
            viewMode: 1,
            dragMode: 'move',
            autoCropArea: 1,
            cropBoxResizable: false,
            cropBoxMovable: false,
            background: false,
            zoomable: true,
            ready() {
                cropper.setCropBoxData({
                    width: 400,
                    height: 400
                });
            }
        });
    }, 100);
}
window.showCropper = showCropper;

function closeCropper() {
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
    document.getElementById('cropModal').style.display = 'none';
}
window.closeCropper = closeCropper;

function cropAndSave() {
    if (!cropper) return;

    const canvas = cropper.getCroppedCanvas({ width: 400, height: 400 });
    const dataURL = canvas.toDataURL('image/jpeg');
    closeCropper();
    addImage(dataURL);
}
window.cropAndSave = cropAndSave;

uploadInput.addEventListener('change', () => {
    const files = Array.from(uploadInput.files);
    if (files.length + count > total) {
        alert(`You can only use ${total} images total.`);
        return;
    }

    const reader = new FileReader();
    reader.onload = e => showCropper(e.target.result);
    reader.readAsDataURL(files[0]);

    uploadInput.value = '';
});

generateHiddenInputs();
</script>

</body>
</html>
    '''
@app.route('/generate', methods=['POST'])
def generate_strip():
    data_urls = [v for k, v in request.form.items() if k.startswith('img') and v]

    if not (2 <= len(data_urls) <= 4):
        return "Please provide between 2 and 4 images.", 400

    images = []
    for data_url in data_urls:
        if "," not in data_url:
            return "Invalid image data", 400
        header, encoded = data_url.split(",", 1)
        img_data = base64.b64decode(encoded)
        img = Image.open(BytesIO(img_data))
        images.append(img)
        bgcolor = request.form.get('bgcolor', 'black')
        selected_filter = request.form.get('filter', 'bw_high_contrast') 
    result = create_photobooth_strip(images, bgcolor=bgcolor, selected_filter=selected_filter) 

    img_io = BytesIO()
    result.save(img_io, 'JPEG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg', as_attachment=True,
        download_name='photostrip.jpg')

if __name__ == '__main__':
    app.run(debug=True)
