import requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, redirect, url_for
import base64

app = Flask(__name__)

goapi_key = 'your api key'
goapi_url = 'https://api.midjourneyapi.xyz/sd/txt2img'

executor = ThreadPoolExecutor(max_workers=10) 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    prompt = request.form['prompt_name']
    images = generate_images(prompt, 5)
    if images:
        return render_template('results.html', images=images)
    else:
        return render_template('index.html', error="Error generating images. Please try again.")

def generate_images(prompt, num_images):
    images = []
    with executor as pool:
        futures = [pool.submit(call_goapi_stable_diffusion, prompt) for _ in range(num_images)]
        for future in futures:
            image = future.result()
            if image:
                images.append(image)
    return images

def call_goapi_stable_diffusion(prompt):
    headers = {
        "X-API-KEY": goapi_key,
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "model_id": "midjourney",
        "width": "512",
        "height": "512"
    }
    
    try:
        response = requests.post(goapi_url, headers=headers, json=data)
        response.raise_for_status()
        
        response_data = response.json()
        if 'output' not in response_data:
            print(f"Error in response: {response_data}")
            return None
        
        image_url = response_data['output'][0]
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_data = base64.b64encode(image_response.content).decode('utf-8')
        image = f"data:image/png;base64,{image_data}"
        
        return image
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True)
