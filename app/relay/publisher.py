import json

def publish(event):
    print("📤 Publishing Event:")
    print(json.dumps(event, indent=2))