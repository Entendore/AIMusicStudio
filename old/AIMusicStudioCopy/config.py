"""Configuration loading, saving, and environment variable setup."""
import yaml
import os

def load_config(config_path="config.yaml"):
    try:
        with open(config_path, "r") as f: return yaml.safe_load(f)
    except FileNotFoundError:
        return {
            'system': {
                'cache_dir': 'E:\\cacheAI', 
                'ckpt_dir': 'E:\\cacheAI',
                # Path where you ran "git clone https://github.com/HeartMuLa/heartlib.git"
                'heartlib_repo_dir': 'E:\\YoutubeProjects\\AIMusicStudio\\heartlib' 
            },
            'hardware': {'device': 'cuda'},
            'plugins': {'active_plugin': 'heartlib'}, 
            'settings': {'output_dir': 'output'}
        }

def save_config(config, config_path="config.yaml"):
    with open(config_path, "w") as f: yaml.dump(config, f, default_flow_style=False)

def setup_environment(config):
    cache_path = os.path.abspath(config.get('system', {}).get('cache_dir', "E:\\cacheAI"))
    if not os.path.exists(cache_path):
        try: os.makedirs(cache_path, exist_ok=True)
        except OSError: cache_path = os.path.join(os.getcwd(), "models_cache")

    os.environ['HF_HOME'] = cache_path
    os.environ['TORCH_HOME'] = cache_path
    os.environ['XDG_CACHE_HOME'] = cache_path