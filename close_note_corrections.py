import re
import pyperclip

def process_text_rule4(text):
    # Swap double quotes with single quotes
    text = text.replace('"', "'")
    text = text.replace('“', "'")
    text = text.replace('”', "'")
    
    # Fix numbers like '4 441' to '4441' by removing spaces between digits
    text = re.sub(r'(?<=\d)\s+(?=\d)', '', text)
    
    # Replace 'behaviour' with 'behavior' (case-insensitive)
    text = re.sub(r'\bbehaviour\b', 'behavior', text, flags=re.IGNORECASE)
    
    text = re.sub(r'\bauthorised\b', 'authorized', text, flags=re.IGNORECASE)
    text = re.sub(r'\borganisation\b', 'organization', text, flags=re.IGNORECASE)
    text = re.sub(r'\brecognised\b', 'recognized', text, flags=re.IGNORECASE)
    
    return text

# Example usage
# input_text = '''4: Activity from user "A, Kathiravan @ Chennai" shows 56 messages sent to balakrishnan.b@iampl.co.in from corporate IP 255.255.255.255. The iampl.co.in domain is regularly used by several employees, and this user has interacted with it on prior dates. The source IP is an organisation egress address and similar alerts were triggered for many users this week. Behaviour therefore appears to be not malicious.'''

user_in = ''
while True:
    user_in = input("Input close note> ")
    if user_in.casefold() == 'q':
        break
    if user_in.casefold() == 'green':
        print('\033[92m')
        continue
    processed_text = process_text_rule4(user_in)
    pyperclip.copy(processed_text)
    print(f'\033[92m\n{processed_text}\n\033[0m')
