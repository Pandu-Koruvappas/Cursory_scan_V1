import os

class TemplateService:
    def __init__(self, base_dir=".agents/skills"):
        # The service expects to be run from the backend directory
        self.base_dir = base_dir

    def load_skill_prompt(self, skill_name: str) -> str:
        """
        Loads the main SKILL.md file for a given agent and automatically
        injects all templates found in its templates/ directory into the prompt.
        """
        skill_dir = os.path.join(self.base_dir, skill_name)
        skill_file = os.path.join(skill_dir, "SKILL.md")
        
        if not os.path.exists(skill_file):
            return ""
            
        with open(skill_file, "r", encoding="utf-8") as f:
            prompt = f.read()
            
        # Append templates
        templates_dir = os.path.join(skill_dir, "templates")
        if os.path.exists(templates_dir):
            prompt += "\n\n--- TEMPLATES ---\n"
            for filename in os.listdir(templates_dir):
                file_path = os.path.join(templates_dir, filename)
                if os.path.isfile(file_path):
                    with open(file_path, "r", encoding="utf-8") as tf:
                        prompt += f"\nTemplate: {filename}\n```\n{tf.read()}\n```\n"
                        
        return prompt
