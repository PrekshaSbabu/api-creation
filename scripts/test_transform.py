import sys
import traceback
from pathlib import Path
import yaml

# adjust import path if necessary
from transformer.core import transform_spec

SAMPLE = r"c:\Users\prath\Downloads\sample_ibm.yaml"

try:
    text = Path(SAMPLE).read_text(encoding='utf-8')
    spec = yaml.safe_load(text)
    transformed = transform_spec(spec)
    print(yaml.dump(transformed, sort_keys=False))
except Exception as e:
    print("ERROR during transform:")
    traceback.print_exc()
    sys.exit(1)
