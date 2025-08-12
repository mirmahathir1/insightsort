import cli_only
from algorithms import table_description
data_lake = cli_only.load_datalake_tables('datalakes/employee_datalake')

table_description.generate_all_table_descriptions()


def sort_list(input_list):
	"""Sorts a list in ascending order and returns the sorted list."""
	return sorted(input_list)

