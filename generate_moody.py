import json
import urllib.request
import urllib.parse
import time
import random
import sys
import argparse
import os

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
        elif class_type == 'EmptySD3LatentImage':
            if len(widgets_values) >= 3:
                inputs['width'] = widgets_values[0]
                inputs['height'] = widgets_values[1]
                inputs['batch_size'] = widgets_values[2]
        elif class_type == 'Prompt (LoraManager)':
            if len(widgets_values) >= 2:
                inputs['text'] = widgets_values[1]
        elif class_type == 'Save Image (LoraManager)':
            if len(widgets_values) >= 2:
                inputs['filename_prefix'] = widgets_values[0]
                inputs['file_format'] = widgets_values[1]
        elif class_type == 'Lora Loader (LoraManager)':
            if len(widgets_values) >= 3:
                inputs['text'] = widgets_values[1]
        elif class_type == 'TriggerWord Toggle (LoraManager)':
            if len(widgets_values) >= 3:
                inputs['group_mode'] = widgets_values[0]
                inputs['default_active'] = widgets_values[1]
                inputs['allow_strength_adjustment'] = widgets_values[2]
                
        api_data[node_id] = {
            "inputs": inputs,
            "class_type": class_type
        }
    return api_data

def generate_image(prompt_text, model_type="real", output_filename=None):
    server_address = "127.0.0.1:8188"
    workflow_path = r"F:\ComfyUI_workflows\agent_custom\T2I-moody.json"
    
    # 1. Model Mapping
    model_mapping = {
        "real": "ZImageTurbo\\moodyRealMix_zitV6DPO.safetensors",
        "pro": "ZImageTurbo\\moodyProMix_zitV12DPO.safetensors",
        "wild": "ZImageTurbo\\moodyWildMixZIBZID_v01.safetensors"
    }
    
    selected_model = model_mapping.get(model_type.lower(), model_mapping["real"])
    
    if output_filename is None:
        output_filename = os.path.join(r"F:\ComfyUI_workflows\agent_custom", f"output_{model_type}.png")
        
    print(f"Loading base workflow: {workflow_path}")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        ui_data = json.load(f)
        
    api_prompt = convert_ui_to_api(ui_data)
    
    # 2. Update parameters dynamically
    prompt_node_id = None
    sampler_node_id = None
    unet_node_id = None
    
    for node_id, node in api_prompt.items():
        if node['class_type'] == 'Prompt (LoraManager)':
            prompt_node_id = node_id
        elif node['class_type'] == 'KSampler':
            sampler_node_id = node_id
        elif node['class_type'] == 'UNETLoader':
            unet_node_id = node_id
            
    # Swap prompt text
    if prompt_node_id:
        api_prompt[prompt_node_id]['inputs']['text'] = prompt_text
        print(f"Set Prompt: {prompt_text}")
        
    # Swap UNet model
    if unet_node_id:
        api_prompt[unet_node_id]['inputs']['unet_name'] = selected_model
        # Since it's a full-precision model (unlike fp8-e4m3fn), default is recommended
        api_prompt[unet_node_id]['inputs']['weight_dtype'] = "default"
        print(f"Set UNet Model ({model_type}): {selected_model}")
        
    # Set random seed
    if sampler_node_id:
        new_seed = random.randint(1, 1125899906842624)
        api_prompt[sampler_node_id]['inputs']['seed'] = new_seed
        print(f"Set KSampler Seed: {new_seed}")
        
    # 3. Queue prompt
    p = {"prompt": api_prompt}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data, headers={'Content-Type': 'application/json'})
    
    print("Sending prompt request to ComfyUI...")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            prompt_id = res_data['prompt_id']
            print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return False
        
    # 4. Wait for completion
    print(f"Generating image with {model_type.upper()} model (polling)...")
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
        
    # 5. Extract output image filename
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
        
    # 6. Download image
    print(f"Downloading image: {image_filename}")
    view_url = f"http://{server_address}/view?filename={urllib.parse.quote(image_filename)}&subfolder={urllib.parse.quote(image_subfolder)}&type={image_type}"
    try:
        urllib.request.urlretrieve(view_url, output_filename)
        print(f"Image successfully saved to: {output_filename}")
        return True
    except Exception as e:
        print(f"Error downloading output image: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate image using customized Moody models on ComfyUI")
    parser.add_argument("--prompt", "-p", type=str, 
                        default="Cinematic photo of a Korean woman in a cozy coffee shop, soft dramatic window lighting, realistic skin textures, highly detailed, film grain, 8k resolution",
                        help="Text prompt for image generation")
    parser.add_argument("--model", "-m", type=str, choices=["real", "pro", "wild"], default="real",
                        help="Choose moody model type (real: moodyRealMix, pro: moodyProMix, wild: moodyWildMix)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Absolute path for the output image file")
    
    args = parser.parse_args()
    
    generate_image(prompt_text=args.prompt, model_type=args.model, output_filename=args.output)
