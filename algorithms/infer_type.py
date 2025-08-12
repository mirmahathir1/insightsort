import re
import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype

_NULLS = {"", "na", "n/a", "null", "none", "nan", "nil", "—", "-"}

_float_re = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')
_int_re   = re.compile(r'^[+-]?\d+$')
_pct_re   = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)%$')

_bool_true  = {"true","t","yes","y","1","on"}
_bool_false = {"false","f","no","n","0","off"}

def _clean_num(s: str) -> str:
    # remove thousands separators/underscores and spaces
    return s.replace(",", "").replace("_", "").strip()

def _maybe_null(s: str) -> bool:
    return s.strip().lower() in _NULLS

def _all_match(series: pd.Series, predicate) -> bool:
    for v in series.dropna():
        s = str(v).strip()
        if _maybe_null(s):
            continue
        if not predicate(s):
            return False
    return True

def _try_cast_bool(col: pd.Series) -> pd.Series | None:
    vals = col.dropna().astype(str).str.strip().str.lower()
    if len(vals) == 0:
        return None
    valid = _bool_true | _bool_false | _NULLS
    if not vals.apply(lambda s: s in valid).all():
        return None
    mapping = {**{k: True for k in _bool_true}, **{k: False for k in _bool_false}}
    out = col.astype("string").str.strip().str.lower().map(mapping)
    # preserve null-like tokens
    out = out.where(~col.astype("string").str.strip().str.lower().isin(_NULLS))
    return out.astype("boolean")

def _try_cast_int(col: pd.Series) -> pd.Series | None:
    vals = col.dropna().astype(str).map(str.strip)
    if len(vals) == 0:
        return None
    if not _all_match(vals, lambda s: _maybe_null(s) or _int_re.match(_clean_num(s))):
        return None
    cleaned = col.astype("string").map(lambda s: None if s is pd.NA or _maybe_null(str(s)) else _clean_num(str(s)))
    try:
        return cleaned.astype("Int64")
    except Exception:
        return None

def _try_cast_float(col: pd.Series) -> pd.Series | None:
    vals = col.dropna().astype(str).map(str.strip)
    if len(vals) == 0:
        return None
    # reject if any value looks like a percentage (handled separately)
    if vals.apply(lambda s: _pct_re.match(s)).any():
        return None
    if not _all_match(vals, lambda s: _maybe_null(s) or _float_re.match(_clean_num(s))):
        return None
    cleaned = col.astype("string").map(lambda s: None if s is pd.NA or _maybe_null(str(s)) else _clean_num(str(s)))
    try:
        return cleaned.astype("Float64")
    except Exception:
        return None

def _try_cast_percent(col: pd.Series, scale=True) -> pd.Series | None:
    vals = col.dropna().astype(str).map(str.strip)
    if len(vals) == 0:
        return None
    if not _all_match(vals, lambda s: _maybe_null(s) or _pct_re.match(s)):
        return None
    def parse_pct(s: str):
        if s is pd.NA or _maybe_null(str(s)): 
            return None
        num = _clean_num(str(s).rstrip("%"))
        return float(num) / (100.0 if scale else 1.0)
    try:
        parsed = vals.map(parse_pct)
        out = col.astype("object").map(parse_pct)
        return pd.Series(out, index=col.index, dtype="Float64")
    except Exception:
        return None

def _try_cast_datetime(col: pd.Series, dayfirst=False) -> pd.Series | None:
    vals = col.dropna().astype(str).map(str.strip)
    if len(vals) == 0:
        return None
    # quick heuristic: require at least half of non-null values to parse
    try:
        parsed = pd.to_datetime(vals, errors="coerce", dayfirst=dayfirst, utc=False, infer_datetime_format=True)
        if parsed.notna().mean() >= 0.9:  # 90%+ parseable → treat as datetime
            full = pd.to_datetime(col, errors="coerce", dayfirst=dayfirst, utc=False, infer_datetime_format=True)
            return full  # dtype: datetime64[ns]
    except Exception:
        pass
    return None

def infer_and_cast_df(
    df: pd.DataFrame,
    *,
    percent_scale: bool = True,
    prefer_category: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """
    Inspect string-typed columns and cast to better dtypes (Int64/Float64/boolean),
    but leave date-like columns as plain string.
    """
    out = df.copy()
    dtype_map: dict[str, str] = {}

    for col in out.columns:
        s = out[col]
        # Skip already-typed columns
        if not (is_object_dtype(s) or is_string_dtype(s)):
            dtype_map[col] = str(s.dtype)
            continue

        # Normalize obvious null tokens to NA
        s = s.astype("string")
        s = s.where(~s.str.strip().str.lower().isin(_NULLS))

        # Try casts in an order that minimizes surprising conversions
        for caster in (
            lambda x: _try_cast_bool(x),
            lambda x: _try_cast_percent(x, scale=percent_scale),
            lambda x: _try_cast_int(x),
            lambda x: _try_cast_float(x),
            # datetime casting removed intentionally
        ):
            casted = caster(s)
            if casted is not None:
                out[col] = casted
                dtype_map[col] = str(out[col].dtype)
                break
        else:
            # Optional: low-cardinality strings → category
            if prefer_category and s.nunique(dropna=True) > 0 and s.nunique(dropna=True) <= max(20, len(s) * 0.05):
                out[col] = s.astype("category")
                dtype_map[col] = "category"
            else:
                out[col] = s.astype("string")
                dtype_map[col] = "string"

    return out, dtype_map
