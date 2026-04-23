from utils.file_loader import load_yaml, save_yaml
from transformer.core import transform_spec
import os
import argparse
from typing import Optional, Dict, Any
from utils.ai import review_and_comment_yaml


def run_transform(input_path: Optional[str] = None,
                  output_path: Optional[str] = None,
                  spec: Optional[Dict[str, Any]] = None,
                  deploy: bool = False) -> Dict[str, Any]:
    """
    Run the transform pipeline.

    Either `spec` (a dict) or `input_path` must be provided. If `spec` is
    provided, it will be used directly. `output_path` defaults to
    "specs/output/run_output.yaml" when not provided.

    If `deploy` is True, the function will attempt to import and call
    `aws.deploy.deploy_api(output_path)` (kept optional for safety).

    Returns a dict with keys: 'output_path', 'api_id' (or None), 'transformed'.
    """
    if spec is None and input_path is None:
        raise ValueError("Either spec or input_path must be provided")

    if spec is None:
        spec = load_yaml(input_path)

    transformed = transform_spec(spec)

    out = output_path or os.path.join("specs", "output", "run_output.yaml")
    # ensure parent dir exists
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # remove internal metadata before saving final spec
    from copy import deepcopy

    to_save = deepcopy(transformed)
    to_save.pop("_meta", None)
    save_yaml(out, to_save)

    # Also save a companion file that preserves internal metadata (_meta)
    try:
        meta_out = out.replace('.yaml', '_with_meta.yaml')
        save_yaml(meta_out, transformed)
    except Exception:
        # non-fatal
        pass

    # run AI review (optional) and save reviewed output next to the transformed file
    try:
        reviewed = review_and_comment_yaml(yaml_text=__import__("yaml").dump(transformed, sort_keys=False))
        if reviewed:
            reviewed_path = out.replace('.yaml', '_reviewed.yaml')
            with open(reviewed_path, 'w', encoding='utf-8') as f:
                f.write(reviewed)
    except Exception:
        # failing the AI review should not break the transform
        pass

    api_id = None
    if deploy:
        # import lazily to keep AWS dependency optional
        from aws.deploy import deploy_api

        api_id = deploy_api(out)

    return {"output_path": out, "api_id": api_id, "transformed": transformed}


def _cli():
    parser = argparse.ArgumentParser(description="Run transform on an API spec")
    parser.add_argument("input", help="Input YAML spec path")
    parser.add_argument("-o", "--output", help="Output YAML path", default=None)
    parser.add_argument("--deploy", action="store_true", help="Deploy to AWS API Gateway after transform")

    args = parser.parse_args()
    result = run_transform(input_path=args.input, output_path=args.output, deploy=args.deploy)

    print(f"Saved transformed spec to: {result['output_path']}")
    if result["api_id"]:
        print(f"✅ API deployed with ID: {result['api_id']}")


if __name__ == "__main__":
    _cli()
