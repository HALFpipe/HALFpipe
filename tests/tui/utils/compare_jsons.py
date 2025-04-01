import json
import re


def normalize_placeholders(path):
    """
    Replace equivalent placeholders in the given path.
    """
    placeholder_map = {"subject": "sub", "atlas": "desc", "map": "desc", "seed": "desc"}

    for full, short in placeholder_map.items():
        path = re.sub(rf"{{({full}|{short})}}", f"{{{short}}}", path)  # Normalize to correct equivalent

    return path


def load_and_normalize_json(file_path):
    """
    Load JSON from a file and normalize paths within it, while ignoring specified keys.
    """
    ignore_keys = {"halfpipe_version", "schema_version", "timestamp"}

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        normalized_data = [normalize_entry(entry, ignore_keys) for entry in data]
        return sorted(normalized_data, key=json.dumps)  # Sort for order independence

    return normalize_entry(data, ignore_keys)


def normalize_entry(entry, ignore_keys):
    """
    Normalize a single JSON entry, replacing placeholders in paths and removing ignored keys.
    """
    if isinstance(entry, dict):
        return {
            k: normalize_placeholders(v) if k == "path" and isinstance(v, str) else normalize_entry(v, ignore_keys)
            for k, v in entry.items()
            if k not in ignore_keys
        }
    elif isinstance(entry, list):
        return sorted([normalize_entry(e, ignore_keys) for e in entry], key=json.dumps)
    return entry


def save_json(data, output_file):
    """
    Save JSON data to a file.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def compare_json_files(file1, file2):
    """
    Compare two JSON files after normalizing paths and ignoring order of entries.
    """
    json1 = load_and_normalize_json(file1)
    json2 = load_and_normalize_json(file2)
    if json1 == json2:
        return True
    else:
        save_json(json1, "./normalized_resaved_spec.json")
        save_json(json2, "./normalized_reference_spec.json")
    return json1 == json2
