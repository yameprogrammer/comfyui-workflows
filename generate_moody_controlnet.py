import os
import json
import random
import time
import urllib.request
import urllib.parse
import argparse
import shutil

def convert_ui_to_api(ui_data):
    """Converts ComfyUI UI format to API prompt format dynamically."""
    api_data = {}
    links = {}
    
    # Map links for easy lookup
    for link in ui_data.get('links', []):
        links[link[0]] = link
        
    for node in ui_data.get('nodes', []):
        node_id = str(node['id'])
        class_type = node['type']
        widgets_values = node.get('widgets_values', [])
        
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
                
        # Widget inputs
        if class_type == 'UNETLoader':
            if len(widgets_values) >= 2:
                inputs['unet_name'] = widgets_values[0]
                inputs['weight_dtype'] = widgets_values[1]
        elif class_type == 'VAELoader':
            if len(widgets_values) >= 1:
                inputs['vae_name'] = widgets_values[0]
        elif class_type == 'CLIPLoader':
            if len(widgets_values) >= 3:
                inputs['clip_name'] = widgets_values[0]
                inputs['type'] = widgets_values[1]
                inputs['device'] = widgets_values[2]
        elif class_type == 'ModelSamplingAuraFlow':
            if len(widgets_values) >= 1:
                inputs['shift'] = widgets_values[0]
        elif class_type == 'CLIPTextEncode':
            if len(widgets_values) >= 1:
                inputs['text'] = widgets_values[0]
        elif class_type == 'KSampler':
            if len(widgets_values) >= 7:
                inputs['seed'] = widgets_values[0]
                inputs['steps'] = widgets_values[2]
                inputs['cfg'] = widgets_values[3]
                inputs['sampler_name'] = widgets_values[4]
                inputs['scheduler'] = widgets_values[5]
                inputs['denoise'] = widgets_values[6]
        elif class_type == 'LoadImage':
            if len(widgets_values) >= 1:
                inputs['image'] = widgets_values[0]
        elif class_type == 'ControlNetLoader':
            if len(widgets_values) >= 1:
                inputs['control_net_name'] = widgets_values[0]
        elif class_type == 'FL_ZImageControlNetPatch':
            if len(widgets_values) >= 2:
                inputs['name'] = widgets_values[0]
                inputs['auto_config'] = widgets_values[1]
        elif class_type == 'ZImageFunControlnet':
            if len(widgets_values) >= 1:
                inputs['strength'] = widgets_values[0]
        elif class_type == 'Save Image (LoraManager)':
            if len(widgets_values) >= 2:
                inputs['filename_prefix'] = widgets_values[0]
                inputs['file_format'] = widgets_values[1]
                
        # Fill in static values that are not linked
        for k, v in node.get('properties', {}).items():
            if k not in inputs:
                inputs[k] = v
                
        api_data[node_id] = {
            "inputs": inputs,
            "class_type": class_type
        }
    return api_data

def generate_controlnet_image(input_image_path, control_image_path, prompt_text, denoise_val=0.70, cfg_val=3.5, control_strength=0.75, model_type="real", output_filename=None):
    server_address = "127.0.0.1:8188"
    workflow_path = r"F:\ComfyUI_workflows\agent_custom\I2I-ControlNet-moody.json"
    comfyui_input_dir = r"F:\ComfyUI_windows_portable\ComfyUI\input"
    
    # 1. Check inputs
    if not os.path.exists(input_image_path):
        print(f"Error: Face reference image not found at {input_image_path}")
        return False
    if not os.path.exists(control_image_path):
        print(f"Error: Control/Pose reference image not found at {control_image_path}")
        return False
        
    # 2. Copy reference images to ComfyUI input folder
    temp_input_name = "temp_i2i_input.png"
    temp_control_name = "temp_control_input.png"
    
    try:
        # Copy face reference image directly
        shutil.copy2(input_image_path, os.path.join(comfyui_input_dir, temp_input_name))
        
        # Preprocess control image using OpenCV Canny edge detector to extract outlines
        import cv2
        img = cv2.imread(control_image_path, cv2.IMREAD_GRAYSCALE)
        edges = cv2.Canny(img, 100, 200)
        # Convert single channel to RGB for ComfyUI node compatibility
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        cv2.imwrite(os.path.join(comfyui_input_dir, temp_control_name), edges_rgb)
        
        print("Successfully processed control image via Canny and copied reference images to ComfyUI input folder.")
    except Exception as e:
        print(f"Error copying/processing reference images: {e}")
        return False
        
    # 3. Model Mapping
    model_mapping = {
        "real": "ZImageTurbo\\moodyRealMix_zitV6DPO.safetensors",
        "pro": "ZImageTurbo\\moodyProMix_zitV12DPO.safetensors",
        "wild": "ZImageTurbo\\moodyWildMixZIBZID_v01.safetensors"
    }
    selected_model = model_mapping.get(model_type.lower(), model_mapping["real"])
    
    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", f"output_controlnet_{model_type}.png")
        
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    
    # 4. Load Workflow JSON
    print(f"Loading ControlNet workflow: {workflow_path}")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        ui_data = json.load(f)
        
    api_prompt = convert_ui_to_api(ui_data)
    
    # 5. Identify nodes and modify parameters
    prompt_node_id = None
    sampler_node_id = None
    unet_node_id = None
    input_image_node_id = None
    control_image_node_id = None
    apply_controlnet_node_id = None
    
    for node_id, node in api_prompt.items():
        if node['class_type'] == 'CLIPTextEncode':
            prompt_node_id = node_id
        elif node['class_type'] == 'KSampler':
            sampler_node_id = node_id
        elif node['class_type'] == 'UNETLoader':
            unet_node_id = node_id
        elif node['class_type'] == 'LoadImage':
            # We have two LoadImage nodes: ID 54 and ID 60
            if node_id == "54":
                input_image_node_id = node_id
            elif node_id == "60":
                control_image_node_id = node_id
        elif node['class_type'] == 'ApplyControlNet':
            apply_controlnet_node_id = node_id
            
    # Modify prompt text
    if prompt_node_id:
        api_prompt[prompt_node_id]['inputs']['text'] = prompt_text
        print(f"Set Prompt: {prompt_text}")
        
    # Modify UNet model
    if unet_node_id:
        api_prompt[unet_node_id]['inputs']['unet_name'] = selected_model
        api_prompt[unet_node_id]['inputs']['weight_dtype'] = "default"
        print(f"Set UNet Model ({model_type}): {selected_model}")
        
    # Modify LoadImage filenames
    if input_image_node_id:
        api_prompt[input_image_node_id]['inputs']['image'] = temp_input_name
    if control_image_node_id:
        api_prompt[control_image_node_id]['inputs']['image'] = temp_control_name
        
    # Modify ApplyControlNet strength
    if apply_controlnet_node_id:
        api_prompt[apply_controlnet_node_id]['inputs']['strength'] = control_strength
        print(f"Set ControlNet Strength: {control_strength}")
        
    # Modify KSampler parameters (Seed, Denoise, CFG)
    if sampler_node_id:
        new_seed = random.randint(1, 1125899906842624)
        api_prompt[sampler_node_id]['inputs']['seed'] = new_seed
        api_prompt[sampler_node_id]['inputs']['denoise'] = denoise_val
        api_prompt[sampler_node_id]['inputs']['cfg'] = cfg_val
        api_prompt[sampler_node_id]['inputs']['sampler_name'] = "euler"
        api_prompt[sampler_node_id]['inputs']['scheduler'] = "normal"
        print(f"Set KSampler Seed: {new_seed}, Denoise: {denoise_val}, CFG: {cfg_val}, Sampler: euler, Scheduler: normal")
        
    # 6. Queue Prompt
    p = {"prompt": api_prompt}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data, headers={'Content-Type': 'application/json'})
    
    print("Sending ControlNet prompt request to ComfyUI...")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            prompt_id = res_data['prompt_id']
            print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return False
        
    # 7. Poll history for completion
    print("Executing ControlNet image editing (polling)...")
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
        
    # 8. Download Output Image
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
        print("Error: Output image not found in history.")
        return False
        
    print(f"Downloading image: {image_filename}")
    view_url = f"http://{server_address}/view?filename={urllib.parse.quote(image_filename)}&subfolder={urllib.parse.quote(image_subfolder)}&type={image_type}"
    try:
        urllib.request.urlretrieve(view_url, output_filename)
        print(f"ControlNet image successfully saved to: {output_filename}")
        return True
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ControlNet-assisted Image-to-Image editing on Moody models")
    parser.add_argument("--input", "-i", type=str, required=True,
                        help="Path to the source character/face image")
    parser.add_argument("--control", "-c_img", type=str, required=True,
                        help="Path to the pose/control reference image")
    parser.add_argument("--prompt", "-p", type=str, required=True,
                        help="Prompt describing the scene and modifications")
    parser.add_argument("--denoise", "-d", type=float, default=0.70,
                        help="Denoise value (default 0.70 for strong face preservation)")
    parser.add_argument("--cfg", "-c", type=float, default=3.5,
                        help="CFG scale (default 3.5)")
    parser.add_argument("--strength", "-s", type=float, default=0.75,
                        help="ControlNet strength (default 0.75)")
    parser.add_argument("--model", "-m", type=str, choices=["real", "pro", "wild"], default="real",
                        help="Moody model type (real, pro, wild)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Path to save output image")
                        
    args = parser.parse_args()
    
    generate_controlnet_image(
        input_image_path=args.input,
        control_image_path=args.control,
        prompt_text=args.prompt,
        denoise_val=args.denoise,
        cfg_val=args.cfg,
        control_strength=args.strength,
        model_type=args.model,
        output_filename=args.output
    )
