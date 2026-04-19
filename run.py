from app.utils.file_loader import load_yaml, save_yaml
from app.transformer.core import transform_spec
from app.aws.deploy import deploy_api

INPUT_FILE = "specs/input/telecon.yaml"
OUTPUT_FILE = "specs/output/telecon_aws.yaml"

def main():
    spec = load_yaml(INPUT_FILE)

    transformed = transform_spec(spec)

    save_yaml(OUTPUT_FILE, transformed)

    api_id = deploy_api(OUTPUT_FILE)

    print(f"✅ API deployed with ID: {api_id}")

if __name__ == "__main__":
    main()
