import numpy as np
import pandas as pd
from datetime import datetime

def sanitize_for_serialization(obj):
    """
    Recursively convert objects to msgpack-serializable types.
    Specifically targets numpy types and converts them to native Python types.
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_serialization(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_serialization(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return sanitize_for_serialization(obj.tolist())
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    elif isinstance(obj, pd.Series):
        return sanitize_for_serialization(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return sanitize_for_serialization(obj.to_dict(orient="records"))
    elif pd.isna(obj) if not isinstance(obj, (list, dict, np.ndarray)) else False:
        return None
    return obj
