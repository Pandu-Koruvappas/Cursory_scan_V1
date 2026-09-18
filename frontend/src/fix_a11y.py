import os
import re

def fix_jsx(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # S6848 & S1082: Add role='button', tabIndex={0}, and onKeyDown to non-interactive elements with onClick
    def repl_onclick(m):
        tag_start = m.group(1) # e.g. <div className="foo"
        onclick = m.group(2)   # e.g. onClick={() => ...}
        
        # Check if it's already an interactive element
        if tag_start.startswith("<button") or tag_start.startswith("<a ") or tag_start.startswith("<form") or tag_start.startswith("<input"):
            return m.group(0)
            
        rest = " "
        if "role=" not in tag_start:
            rest += 'role="button" '
        if "tabIndex=" not in tag_start:
            rest += 'tabIndex={0} '
        if "onKeyDown=" not in tag_start:
            rest += 'onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.click(); }} '
            
        return f'{tag_start}{rest}{onclick}'

    content = re.sub(r'(<[a-zA-Z0-9]+\b[^>]*?)\b(onClick=\{[^}]+\})', repl_onclick, content)

    # S1082: Mouse events should have corresponding keyboard events
    # onMouseOver -> onFocus, onMouseOut -> onBlur
    content = re.sub(r'onMouseOver=(\{[^\}]+\})(?![^>]*onFocus=)', r'onMouseOver=\1 onFocus=\1', content)
    content = re.sub(r'onMouseOut=(\{[^\}]+\})(?![^>]*onBlur=)', r'onMouseOut=\1 onBlur=\1', content)

    # S6772: Spacing between inline elements should be explicit. 
    # Usually this means adding {' '} instead of spaces between tags like <span> <span>
    # This is hard to do safely with regex, but we will leave it for now or try to fix specific instances.
    
    # S6853: Label elements should have a text label and an associated control
    # Adding htmlFor="" or nesting. We'll just leave it or handle it manually.

    # S8786: \Z is useless escape in javascript string/regex
    content = content.replace(r'\Z', r'$')
    content = content.replace(r'\*', r'*')

    if original != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Fixed {path}')

for root, _, files in os.walk('c:/Users/VMADMIN/Videos/SURYA/baagent/frontend/src'):
    for f in files:
        if f.endswith('.jsx'):
            fix_jsx(os.path.join(root, f))
