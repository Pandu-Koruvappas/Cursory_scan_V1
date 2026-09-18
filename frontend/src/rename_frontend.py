import re

with open('App.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

# API Endpoints
text = text.replace('/generate-trd', '/generate-functional-spec')
text = text.replace('/download-trd', '/download-spec')

# Variable names
text = text.replace('trdData', 'specData')
text = text.replace('trdRes', 'specRes')
text = text.replace('trdResult', 'specResult')
text = text.replace('setTrd', 'setFunctionalSpec')

# UI Labels
text = text.replace('Tech Spec', 'Functional Spec')
text = text.replace('Technical Spec', 'Functional Spec')
text = text.replace('Spec Architect', 'Functional Architect')
text = text.replace('TRD GENERATION', 'FUNCTIONAL SPEC GENERATION')
text = text.replace('TRD Generation', 'Functional Spec Generation')
text = text.replace('TRD', 'Functional Spec')

# Object keys
text = text.replace('trd:', 'functional_spec:')
text = text.replace('.trd', '.functional_spec')
text = text.replace("['trd'", "['functional_spec'")
text = text.replace("'trd'", "'functional_spec'")
text = text.replace('"trd"', '"functional_spec"')
text = text.replace('trd_preview', 'spec_preview')
text = text.replace('trd-panel', 'spec-panel')

# Fix state variable usage
text = re.sub(r'\btrd\b', 'functional_spec', text)

with open('App.jsx', 'w', encoding='utf-8') as f:
    f.write(text)
