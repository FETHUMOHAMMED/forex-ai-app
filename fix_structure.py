with open("institutional/institutional_structure.py", "r", encoding="utf-8") as f:
    content = f.read()

old = "        self.structure_score = structure_score"
new = """        self.structure_score = structure_score
        # Compatibility aliases for old code
        self.continuation_probability = continuation_prob
        self.trend_quality = "UNKNOWN"
        self.expansion_state = "UNKNOWN"
        self.institutional_cycle = "UNKNOWN\""""

content = content.replace(old, new)

with open("institutional/institutional_structure.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
