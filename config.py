import yaml
from pathlib import Path

def get_config(config_file='config.yaml'):
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config 
    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot find the {config_file} file")

def update_config(new_settings: dict={}, config_file: str='config.yaml'):
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config 
    except FileNotFoundError:
        raise FileNotFoundError(f"Cannot find the {config_file} file")
    
    for key in new_settings.keys():
        config[key] = new_settings[key]
    
    with open(config_file, 'w') as file:
        yaml.dump(config, file, default_flow_style=False)
        
    return

def get_weights_path(config, epoch: str):
    model_folder = f"{config['datasource']}_{config['model_folder']}"
    model_filename = f"{config['model_basename']}{epoch}.pt"
    return str(Path('.') / model_folder / model_filename)

def get_latest_weight(config):
    model_folder = f"{config['datasource']}_{config['model_folder']}"
    model_filename = f"{config['model_basename']}*"
    weights_files = list(Path(model_folder).glob(model_filename))
    if len(weights_files) == 0:
        return None
    weights_files.sort()
    return str(weights_files[-1])