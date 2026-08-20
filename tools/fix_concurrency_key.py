content = open('packages/integrity/concurrency_test.py').read()

# Fix: executed_positions stores "position" not "position_ticket"
old_live = 'live_positions = [p["position_ticket"] for p in self.live_micro.executed_positions]'
new_live = 'live_positions = [p["position"] for p in self.live_micro.executed_positions]'
content = content.replace(old_live, new_live)

old_demo = 'demo_positions = [p["position_ticket"] for p in self.demo2.executed_positions]'
new_demo = 'demo_positions = [p["position"] for p in self.demo2.executed_positions]'
content = content.replace(old_demo, new_demo)

open('packages/integrity/concurrency_test.py', 'w').write(content)
print('Fixed key name: position_ticket -> position')
