import os

def update_templates(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content.replace('Placement &amp; Career Cell', 'Training &amp; Placement Cell')
                new_content = new_content.replace('Placement & Career Cell', 'Training & Placement Cell')
                new_content = new_content.replace('PLACEMENT & CAREER CELL', 'TRAINING & PLACEMENT CELL')
                new_content = new_content.replace('Placement Cell ©', 'Training & Placement Cell ©')
                
                new_content = new_content.replace('<div class="logo-icon">N</div>', '<img src="/static/nitap_logo.png" class="logo-img" alt="NIT AP Logo" style="height: 40px; width: auto;">')
                
                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {filepath}")

update_templates('templates')
