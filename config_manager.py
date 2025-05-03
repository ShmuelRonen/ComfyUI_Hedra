import os
import json

class HedraConfig:
    def __init__(self):
        # Get the directory of this file
        self.node_dir = os.path.dirname(os.path.realpath(__file__))
        self.config_file = os.path.join(self.node_dir, "config.json")
        
        # Create default config if it doesn't exist
        if not os.path.exists(self.config_file):
            self.create_default_config()
    
    def create_default_config(self):
        """Create a default config file with placeholders"""
        default_config = {
            "api_key": "put_your_hedra_api_key_here"
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created default config file at: {self.config_file}")
        except Exception as e:
            print(f"Error creating config file: {e}")
    
    def get_api_key(self):
        """Get the API key from config"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('api_key', '')
        except Exception as e:
            print(f"Error reading config file: {e}")
            return ''
    
    def save_api_key(self, api_key):
        """Save API key to config"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            config['api_key'] = api_key
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            return True
        except Exception as e:
            print(f"Error saving API key: {e}")
            return False