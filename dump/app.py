import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
import os
import subprocess
import logging
import random

logging.basicConfig(level=logging.INFO)

class Config:
    GOAPI_KEY = '80f54b240b859c3a7812e55ce46ecb27a5deeb82abd34553ace2938c7490e59c'
    OPENAI_API_KEY = 'sk-proj-EtnRjZB5Wdw2kZCgPUO1T3BlbkFJI7f0IxQsqjljD6fMsKZg'
    GOAPI_URL = 'https://api.goapi.com/sd/txt2img'
    OPENAI_URL = 'https://api.openai.com/v1/chat/completions'

config = Config()

executor = ThreadPoolExecutor(max_workers=10)


PROMPT_THEMES = [
    "Describe a futuristic cityscape",
    "Write a short story about time travel",
    "Create a poem inspired by the ocean at night",
    # we can add more prompts
]

def main():

    prompt_theme = random.choice(PROMPT_THEMES)
    prompts = generate_prompts(prompt_theme)
    
    if not prompts:
        logging.error("Error generating prompts. Please try again.")
        return

    logging.info(f"Generated prompts: {prompts}")

    images = []
    for prompt in prompts:
        images.extend(generate_images(prompt, 5))

    if images:
        video_url = create_video(images)
        if video_url:
            logging.info(f"Video created successfully: {video_url}")
        else:
            logging.error("Error creating video.")
    else:
        logging.error("Error generating images. Please try again.")

def generate_prompts(prompt_theme):
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Generate creative prompts based on the following input."},
            {"role": "user", "content": prompt_theme}
        ],
        "max_tokens": 50,
        "n": 5
    }
    
    try:
        response = requests.post(config.OPENAI_URL, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()
        if 'choices' not in response_data or len(response_data['choices']) == 0:
            logging.error(f"Error in response: {response_data}")
            return []
        
        prompts = [choice['message']['content'].strip() for choice in response_data['choices']]
        return prompts
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return []
    except Exception as e:
        logging.error(f"Error: {e}")
        return []

def generate_images(prompt, num_images):
    images = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(call_goapi_stable_diffusion, prompt) for _ in range(num_images)]
        for future in as_completed(futures):
            image = future.result()
            if image:
                images.append(image)
    return images

def call_goapi_stable_diffusion(prompt):
    headers = {
        "X-API-KEY": config.GOAPI_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "model_id": "midjourney",
        "width": 512,
        "height": 512
    }
    
    try:
        logging.info(f"Sending request to SDXL endpoint with data: {data}")
        response = requests.post(config.GOAPI_URL, headers=headers, json=data)
        logging.info(f"Response status code: {response.status_code}")
        response.raise_for_status()
        
        response_data = response.json()
        if 'output' not in response_data or len(response_data['output']) == 0:
            logging.error(f"Error in response: {response_data}")
            return None
        
        image_url = response_data['output'][0]
        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_data = base64.b64encode(image_response.content).decode('utf-8')
        image = f"data:image/png;base64,{image_data}"
        
        return image
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        if response and response.status_code != 404:
            logging.error(f"Response content: {response.content.decode()}")
        return None
    except Exception as e:
        logging.error(f"Error: {e}")
        return None


def create_video(images):
    image_files = []
    for i, image_data in enumerate(images):
        image_file = f"image_{i}.png"
        with open(image_file, "wb") as f:
            f.write(base64.b64decode(image_data.split(',')[1]))
        image_files.append(image_file)
    
    video_file = 'output.mp4'
    command = ['ffmpeg', '-y', '-r', '1', '-i', 'image_%d.png', '-vcodec', 'libx264', '-crf', '25', '-pix_fmt', 'yuv420p', video_file]
    
    logging.info(f"Running FFmpeg command: {' '.join(command)}")
    
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e}")
        return None
    
    for image_file in image_files:
        os.remove(image_file)
    
    return video_file

if __name__ == '__main__':
    main()
