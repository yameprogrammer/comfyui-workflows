import json
import urllib.request
import urllib.parse
import time
import random
import sys
import argparse
import os
import shutil

def convert_ui_to_api(ui_data):
    api_data = {}
    links = {l[0]: l for l in ui_data.get('links', [])}
    
    for node in ui_data.get('nodes', []):
        node_id = str(node['id'])
        class_type = node['type']
        inputs = {}
        
        # Link inputs
        for inp in node.get('inputs', []):
            name = inp['name']
            link_id = inp.get('link')
            if link_id is not None and link_id in links:
                link = links[link_id]
                origin_node_id = str(link[1])
                origin_output_index = link[2]
                inputs[name] = [origin_node_id, origin_output_index]
                
        # Widget inputs mapping
        widgets_values = node.get('widgets_values', [])
        if not widgets_values:
            widgets_values = []
            
        if class_type == 'CLIPLoader':
            if len(widgets_values) >= 3:
                inputs['clip_name'] = widgets_values[0]
                inputs['type'] = widgets_values[1]
                inputs['device'] = widgets_values[2]
        elif class_type == 'VAELoader':
            if len(widgets_values) >= 1:
                inputs['vae_name'] = widgets_values[0]
        elif class_type == 'UNETLoader':
            if len(widgets_values) >= 2:
                inputs['unet_name'] = widgets_values[0]
                inputs['weight_dtype'] = widgets_values[1]
        elif class_type == 'ModelSamplingAuraFlow':
            if len(widgets_values) >= 1:
                inputs['shift'] = widgets_values[0]
        elif class_type == 'KSampler':
            if len(widgets_values) >= 7:
                inputs['seed'] = widgets_values[0]
                inputs['steps'] = widgets_values[2]
                inputs['cfg'] = widgets_values[3]
                inputs['sampler_name'] = widgets_values[4]
                inputs['scheduler'] = widgets_values[5]
                inputs['denoise'] = widgets_values[6]
        elif class_type == 'Save Image (LoraManager)':
            if len(widgets_values) >= 2:
                inputs['filename_prefix'] = widgets_values[0]
                inputs['file_format'] = widgets_values[1]
        elif class_type == 'Lora Loader (LoraManager)':
            if len(widgets_values) >= 3:
                inputs['text'] = widgets_values[1]
        elif class_type == 'Prompt (LoraManager)':
            if len(widgets_values) >= 2:
                inputs['text'] = widgets_values[1]
        elif class_type == 'CLIPTextEncode':
            if len(widgets_values) >= 1:
                inputs['text'] = widgets_values[0]
        elif class_type == 'TriggerWord Toggle (LoraManager)':
            if len(widgets_values) >= 3:
                inputs['group_mode'] = widgets_values[0]
                inputs['default_active'] = widgets_values[1]
                inputs['allow_strength_adjustment'] = widgets_values[2]
        elif class_type == 'LoadImage':
            if len(widgets_values) >= 1:
                inputs['image'] = widgets_values[0]
                inputs['upload'] = "image"
        elif class_type == 'VAEEncode':
            pass
                
        api_data[node_id] = {
            "inputs": inputs,
            "class_type": class_type
        }
    return api_data

def generate_i2i_image(input_image_path, prompt_text, denoise_val=0.45, cfg_val=1.0, model_type="real", output_filename=None):
    server_address = "127.0.0.1:8188"
    workflow_path = r"F:\ComfyUI_workflows\agent_custom\I2I-moody.json"
    comfyui_input_dir = r"F:\ComfyUI_windows_portable\ComfyUI\input"
    
    # 1. Check if input image exists
    if not os.path.exists(input_image_path):
        print(f"Error: Input image not found at {input_image_path}")
        return False
        
    # 2. Copy input image to ComfyUI input folder
    temp_input_name = "temp_i2i_input.png"
    target_input_path = os.path.join(comfyui_input_dir, temp_input_name)
    try:
        shutil.copy2(input_image_path, target_input_path)
        print(f"Copied source image to ComfyUI input directory: {target_input_path}")
    except Exception as e:
        print(f"Error copying input image to ComfyUI input folder: {e}")
        return False
        
    # 3. Model Mapping
    model_mapping = {
        "real": "ZImageTurbo\\moodyRealMix_zitV6DPO.safetensors",
        "pro": "ZImageTurbo\\moodyProMix_zitV12DPO.safetensors",
        "wild": "ZImageTurbo\\moodyWildMixZIBZID_v01.safetensors"
    }
    selected_model = model_mapping.get(model_type.lower(), model_mapping["real"])
    
    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", f"output_i2i_{model_type}.png")
        
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
    # 4. Load base I2I workflow
    print(f"Loading I2I workflow: {workflow_path}")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        ui_data = json.load(f)
        
    api_prompt = convert_ui_to_api(ui_data)
    
    # 5. Update parameters dynamically
    prompt_node_id = None
    sampler_node_id = None
    unet_node_id = None
    load_image_node_id = None
    
    for node_id, node in api_prompt.items():
        if node['class_type'] == 'Prompt (LoraManager)' or node['class_type'] == 'CLIPTextEncode':
            prompt_node_id = node_id
        elif node['class_type'] == 'KSampler':
            sampler_node_id = node_id
        elif node['class_type'] == 'UNETLoader':
            unet_node_id = node_id
        elif node['class_type'] == 'LoadImage':
            load_image_node_id = node_id
            
    # Set edit instruction prompt
    if prompt_node_id:
        api_prompt[prompt_node_id]['inputs']['text'] = prompt_text
        print(f"Set Prompt: {prompt_text}")
        
    # Set UNet Model
    if unet_node_id:
        api_prompt[unet_node_id]['inputs']['unet_name'] = selected_model
        api_prompt[unet_node_id]['inputs']['weight_dtype'] = "default"
        print(f"Set UNet Model ({model_type}): {selected_model}")
        
    # Set KSampler parameters (Seed, Denoise, CFG)
    if sampler_node_id:
        new_seed = random.randint(1, 1125899906842624)
        api_prompt[sampler_node_id]['inputs']['seed'] = new_seed
        api_prompt[sampler_node_id]['inputs']['denoise'] = denoise_val
        api_prompt[sampler_node_id]['inputs']['cfg'] = cfg_val
        api_prompt[sampler_node_id]['inputs']['sampler_name'] = "euler"
        api_prompt[sampler_node_id]['inputs']['scheduler'] = "normal"
        print(f"Set KSampler Seed: {new_seed}, Denoise: {denoise_val}, CFG: {cfg_val}, Sampler: euler, Scheduler: normal")
        
    # Set input image filename for LoadImage
    if load_image_node_id:
        api_prompt[load_image_node_id]['inputs']['image'] = temp_input_name
        print(f"Set LoadImage source file: {temp_input_name}")
        
    # 6. Queue prompt
    p = {"prompt": api_prompt}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data, headers={'Content-Type': 'application/json'})
    
    print("Sending I2I prompt request to ComfyUI...")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            prompt_id = res_data['prompt_id']
            print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return False
        
    # 7. Wait for completion
    print(f"Executing Image-to-Image editing (polling)...")
    while True:
        try:
            with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
                history = json.loads(response.read().decode('utf-8'))
                if prompt_id in history:
                    print("Generation completed!")
                    outputs = history[prompt_id].get('outputs', {})
                    break
        except Exception as e:
            pass
        time.sleep(1)
        
    # 8. Extract output image filename
    image_filename = None
    image_subfolder = None
    image_type = None
    
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            for img in node_output['images']:
                image_filename = img['filename']
                image_subfolder = img.get('subfolder', '')
                image_type = img.get('type', 'output')
                break
                
    if not image_filename:
        print("Error: Output image not found in ComfyUI history.")
        return False
        
    # 9. Download output image
    print(f"Downloading image: {image_filename}")
    view_url = f"http://{server_address}/view?filename={urllib.parse.quote(image_filename)}&subfolder={urllib.parse.quote(image_subfolder)}&type={image_type}"
    try:
        urllib.request.urlretrieve(view_url, output_filename)
        print(f"Edited image successfully saved to: {output_filename}")
        return True
    except Exception as e:
        print(f"Error downloading edited image: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image-to-Image editing using customized Moody models on ComfyUI")
    parser.add_argument("--input", "-i", type=str, required=True,
                        help="Path to the input source image")
    parser.add_argument("--prompt", "-p", type=str, required=True,
                        help="Text prompt for image editing instruction")
    parser.add_argument("--denoise", "-d", type=float, default=0.45,
                        help="Denoise value (0.0 to 1.0, default 0.45)")
    parser.add_argument("--cfg", "-c", type=float, default=1.0,
                        help="CFG scale (default 1.0)")
    parser.add_argument("--model", "-m", type=str, choices=["real", "pro", "wild"], default="real",
                        help="Choose moody model type (real, pro, wild)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Absolute path for the output edited image file")
    
    args = parser.parse_args()
    
    generate_i2i_image(
        input_image_path=args.input,
        prompt_text=args.prompt,
        denoise_val=args.denoise,
        cfg_val=args.cfg,
        model_type=args.model,
        output_filename=args.output
    )
