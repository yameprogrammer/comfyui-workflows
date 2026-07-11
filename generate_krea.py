import os
import json
import random
import time
import urllib.request
import urllib.parse
import argparse

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
        elif class_type == 'CLIPLoader':
            if len(widgets_values) >= 3:
                inputs['clip_name'] = widgets_values[0]
                inputs['type'] = widgets_values[1]
                inputs['device'] = widgets_values[2]
        elif class_type == 'VAELoader':
            if len(widgets_values) >= 1:
                inputs['vae_name'] = widgets_values[0]
        elif class_type == 'EmptyLatentImage':
            if len(widgets_values) >= 3:
                inputs['width'] = widgets_values[0]
                inputs['height'] = widgets_values[1]
                inputs['batch_size'] = widgets_values[2]
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
        elif class_type == 'SaveImage':
            if len(widgets_values) >= 1:
                inputs['filename_prefix'] = widgets_values[0]
                
        # Fill in static values that are not linked
        for k, v in node.get('properties', {}).items():
            if k not in inputs:
                inputs[k] = v
                
        api_data[node_id] = {
            "inputs": inputs,
            "class_type": class_type
        }
    return api_data

def generate_krea_image(prompt_text, steps=8, cfg=1.0, sampler="euler_sde", scheduler="simple", output_filename=None):
    server_address = "127.0.0.1:8188"
    workflow_path = r"F:\ComfyUI_workflows\agent_custom\T2I-krea.json"
    
    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_images", "output_krea.png")
        
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    
    # 1. Load Workflow JSON
    print(f"Loading Krea base workflow: {workflow_path}")
    with open(workflow_path, 'r', encoding='utf-8') as f:
        ui_data = json.load(f)
        
    api_prompt = convert_ui_to_api(ui_data)
    
    # 2. Identify nodes and modify parameters
    positive_prompt_node_id = "5"
    sampler_node_id = "7"
    
    # Modify prompt text
    if positive_prompt_node_id in api_prompt:
        api_prompt[positive_prompt_node_id]['inputs']['text'] = prompt_text
        print(f"Set Prompt: {prompt_text}")
        
    # Modify KSampler parameters (Seed, steps, cfg, sampler, scheduler)
    if sampler_node_id in api_prompt:
        new_seed = random.randint(1, 1125899906842624)
        api_prompt[sampler_node_id]['inputs']['seed'] = new_seed
        api_prompt[sampler_node_id]['inputs']['steps'] = steps
        api_prompt[sampler_node_id]['inputs']['cfg'] = cfg
        api_prompt[sampler_node_id]['inputs']['sampler_name'] = sampler
        api_prompt[sampler_node_id]['inputs']['scheduler'] = scheduler
        api_prompt[sampler_node_id]['inputs']['denoise'] = 1.0
        print(f"Set KSampler Seed: {new_seed}, Steps: {steps}, CFG: {cfg}, Sampler: {sampler}, Scheduler: {scheduler}")
        
    # 3. Queue Prompt
    p = {"prompt": api_prompt}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data, headers={'Content-Type': 'application/json'})
    
    print("Sending Krea prompt request to ComfyUI...")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            prompt_id = res_data['prompt_id']
            print(f"Prompt queued successfully. Prompt ID: {prompt_id}")
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return False
        
    # 4. Poll history for completion
    print("Executing Krea T2I generation (polling)...")
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
        
    # 5. Download Output Image
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
        print(f"Krea T2I image successfully saved to: {output_filename}")
        return True
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="T2I Generation using Krea 2 Turbo model")
    parser.add_argument("--prompt", "-p", type=str, default="Cinematic photo of a Korean woman in a cozy coffee shop, smiling, highly detailed, 8k",
                        help="Prompt describing the scene to generate")
    parser.add_argument("--steps", "-s", type=int, default=8,
                        help="Inference steps (default 8)")
    parser.add_argument("--cfg", "-c", type=float, default=1.0,
                        help="CFG scale (default 1.0)")
    parser.add_argument("--sampler", "-sm", type=str, default="euler_ancestral",
                        help="Sampler name (default euler_ancestral)")
    parser.add_argument("--scheduler", "-sc", type=str, default="simple",
                        help="Scheduler name (default simple)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Path to save output image")
                        
    args = parser.parse_args()
    
    generate_krea_image(
        prompt_text=args.prompt,
        steps=args.steps,
        cfg=args.cfg,
        sampler=args.sampler,
        scheduler=args.scheduler,
        output_filename=args.output
    )
