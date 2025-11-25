import csv

def extract_domain(full_domain):
    # Split the domain by dots
    parts = full_domain.split('.')
    # Return the second to last part (the main domain)
    return parts[-2]

def parse_csv(file_path):
    unique_domains = set()
    
    with open(file_path, mode='r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            full_domain = row[0]
            if '.com' not in full_domain:
                domain = extract_domain(full_domain)
                unique_domains.add(domain)
    
    return list(unique_domains)

# Example usage
file_path = r'C:\Users\wharris\Downloads\list.csv'
unique_domains = parse_csv(file_path)
print(unique_domains)