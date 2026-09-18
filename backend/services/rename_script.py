import re

with open('orchestrator.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('from agents.trd_gen import TRDGenAgent', 'from agents.functional_spec import FunctionalSpecAgent')
text = text.replace('self.trd_agent = TRDGenAgent()', 'self.functional_spec_agent = FunctionalSpecAgent()')
text = text.replace('self.trd_agent.generate_trd', 'self.functional_spec_agent.generate_spec')
text = text.replace('run_trd_generation', 'run_functional_spec_generation')
text = text.replace('TRD', 'Functional Spec')
text = text.replace('trd_content', 'functional_spec_content')
text = text.replace('trd_agent', 'functional_spec_agent')
text = text.replace('project.trd = trd', 'project.functional_spec = functional_spec')

# Safely replace isolated "trd" 
text = re.sub(r'\btrd\b', 'functional_spec', text)

with open('orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(text)
