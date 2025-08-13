import re
import pandas as pd

def q_ident(ident: str) -> str:
    """Quote an identifier if it has spaces/special chars or starts with a digit."""
    ident = str(ident)
    if ident.startswith('"') and ident.endswith('"'):
        return ident  # already quoted
    return ident if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', ident) else f'"{ident}"'

def q_table(tname: str) -> str:
    """Quote each part of a possibly qualified table name like schema.table."""
    parts = [p.strip() for p in str(tname).split('.')]
    return '.'.join(q_ident(p) for p in parts)
def build_augmented_sql(datalake_table_name, join_key_input, join_key_datalake, sort_cols, input_dataframe, datalake_dataframe):
    """
    Return a SQL string that:
      - INNER JOINs input_table to the given data-lake table
      - SELECT DISTINCTs only input_table.join_key_input and the specified data-lake sort columns
      - ORDER BY all sort columns in DESC order (in the given order)
      - Fully qualifies all columns and quotes identifiers with spaces/special chars
    """
    # normalize sort_cols
    if isinstance(sort_cols, (list, tuple)):
        sort_list = [str(c) for c in sort_cols if str(c).strip() != ""]
    else:
        sort_list = [str(sort_cols)]

    if not sort_list:
        raise ValueError("sort_cols must contain at least one column name.")

    t_dl = q_table(datalake_table_name)
    jk_input = q_ident(join_key_input)
    jk_dl    = q_ident(join_key_datalake)

    # Print ratio of unique join key values to total row count for both tables
    input_unique_count = input_dataframe[join_key_input].nunique(dropna=False)
    input_total_count = len(input_dataframe)
    dl_unique_count = datalake_dataframe[join_key_datalake].nunique(dropna=False)
    dl_total_count = len(datalake_dataframe)

    is_input_approximately_unique = input_unique_count / input_total_count > 0.8
    is_dl_approximately_unique = dl_unique_count / dl_total_count > 0.8

    if not len(sort_list) == 1:
        raise ValueError("sorting attribute other than one is not supported")

    sort_col = sort_list[0]

    one_to_one_join = is_input_approximately_unique and is_dl_approximately_unique
    one_to_many_join = is_input_approximately_unique and not is_dl_approximately_unique
    many_to_one_join = not is_input_approximately_unique and is_dl_approximately_unique
    many_to_many_join = not is_input_approximately_unique and not is_dl_approximately_unique

    is_datalake_sort_column_numeric = pd.api.types.is_numeric_dtype(datalake_dataframe[sort_list[0]])

    # Handle both one-to-many and many-to-many joins the same way when the sort column is numeric:
    # 1) Aggregate on the data lake grouped by the datalake join key.
    # 2) Join the aggregated table with the input table.
    # 3) Select input join key, then aggregated value, then remaining input columns.
    if (one_to_many_join or many_to_many_join) and is_datalake_sort_column_numeric:
        agg_col_name = f"sum_{sort_col}"
        agg_alias = q_ident(agg_col_name)

        # Build SELECT list: join key first, then aggregate, then remaining input_table columns
        other_input_cols = [c for c in input_dataframe.columns if c != join_key_input]
        remaining_cols = [f"input_table.{q_ident(c)}" for c in other_input_cols]
        select_cols = [f"input_table.{jk_input}", f"agg.{agg_alias}"] + remaining_cols

        # Aggregate on the datalake table only, then join back to input_table
        sql = (
            "WITH agg AS (\n"
            f"  SELECT {t_dl}.{jk_dl} AS {jk_input}, SUM({t_dl}.{q_ident(sort_col)}) AS {agg_alias}\n"
            f"  FROM {t_dl}\n"
            f"  GROUP BY {t_dl}.{jk_dl}\n"
            ")\n"
            "SELECT\n  "
            + ",\n  ".join(select_cols)
            + "\nFROM input_table\n"
            "INNER JOIN agg\n"
            f"  ON input_table.{jk_input} = agg.{jk_input}\n"
            f"ORDER BY agg.{agg_alias} DESC;"
        )
        return sql


    # Show input table join key, then sort attribute, then remaining input table columns
    other_input_cols = [c for c in input_dataframe.columns if c != join_key_input]
    remaining_cols = [f"input_table.{q_ident(c)}" for c in other_input_cols]
    select_cols = [f"input_table.{jk_input}", f"{t_dl}.{q_ident(sort_col)}"] + remaining_cols
    order_by    = f"{t_dl}.{q_ident(sort_col)} DESC"
    sql = (
        "SELECT DISTINCT\n  "
        + ",\n  ".join(select_cols)
        + "\nFROM input_table\n"
        f"INNER JOIN {t_dl}\n"
        f"  ON input_table.{jk_input} = {t_dl}.{jk_dl}\n"
        f"ORDER BY {order_by};"
    )
    return sql