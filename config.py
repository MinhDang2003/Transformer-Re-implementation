import yaml

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