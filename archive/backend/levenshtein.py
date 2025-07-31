from Levenshtein import distance as levenshtein_distance

def calculate_levenshtein_distance(list1, list2):
    '''CALCULATES LEVENSHTEIN DISTANCE BETWEEN TWO LISTS'''
    return levenshtein_distance(list1, list2)

# 1. Alphabetical Order
alphabetical_order = ["Accessories", "Apparel", "Electronics", "Fitness", "Furniture", "Home Goods", "Kitchen"]

# 2. Reverse Alphabetical Order
reverse_alphabetical_order = ["Kitchen", "Home Goods", "Furniture", "Fitness", "Electronics", "Apparel", "Accessories"]

# 3. Popularity-Based (Note: Providing an example order here since actual frequency is not given)
popularity_based = ["Electronics", "Apparel", "Home Goods", "Furniture", "Fitness", "Accessories", "Kitchen"]

# 4. Thematic Grouping
thematic_grouping = ["Electronics", "Kitchen", "Furniture", "Accessories", "Fitness", "Home Goods", "Apparel"]

# 5. Custom Order (Example)
custom_order = ["Furniture", "Electronics", "Kitchen", "Apparel", "Accessories", "Fitness", "Home Goods"]

# Target List
electronics_to_fitness = ["Electronics", "Furniture", "Home Goods", "Kitchen", "Accessories", "Apparel", "Fitness"]

# Printing distances
print("Levenshtein - Alphabetical Order:", calculate_levenshtein_distance(electronics_to_fitness, alphabetical_order))
print("Levenshtein - Reverse Alphabetical Order:", calculate_levenshtein_distance(electronics_to_fitness, reverse_alphabetical_order))
# print("Levenshtein - Popularity-Based:", calculate_levenshtein_distance(electronics_to_fitness, popularity_based))
print("Levenshtein - Thematic Grouping:", calculate_levenshtein_distance(electronics_to_fitness, thematic_grouping))
# print("Levenshtein - Custom Order:", calculate_levenshtein_distance(electronics_to_fitness, custom_order))
