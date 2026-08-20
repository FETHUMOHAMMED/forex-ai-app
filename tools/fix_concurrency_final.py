content = open('packages/integrity/concurrency_test.py').read()

# Fix: count cross-attempts BEFORE concurrent test
old = '''    def test_concurrent_execution(self):
        """Run both accounts concurrently, verify no crossing."""
        errors = []'''

new = '''    def test_concurrent_execution(self):
        """Run both accounts concurrently, verify no crossing."""
        errors = []
        
        # Record cross-attempt counts BEFORE concurrent test
        live_cross_before = len(self.live_micro.cross_account_attempts)
        demo_cross_before = len(self.demo2.cross_account_attempts)'''

content = content.replace(old, new)

old_check = '''        no_overlap = len(overlap) == 0
        no_cross_attempts = len(self.live_micro.cross_account_attempts) == 0 and len(self.demo2.cross_account_attempts) == 0
        
        self.results.append({
            "test": "Concurrent execution (20 signals)",
            "passed": no_overlap and no_cross_attempts,
            "blocked": no_overlap,
            "detail": f"Live: {len(live_positions)} positions, Demo: {len(demo_positions)}, Overlap: {len(overlap)}, Cross-attempts: 0"
        })'''

new_check = '''        no_overlap = len(overlap) == 0
        # No NEW cross-attempts during concurrent execution
        live_cross_new = len(self.live_micro.cross_account_attempts) - live_cross_before
        demo_cross_new = len(self.demo2.cross_account_attempts) - demo_cross_before
        no_new_cross = live_cross_new == 0 and demo_cross_new == 0
        
        self.results.append({
            "test": "Concurrent execution (20 signals)",
            "passed": no_overlap and no_new_cross,
            "blocked": no_overlap,
            "detail": f"Live: {len(live_positions)} positions, Demo: {len(demo_positions)}, Overlap: {len(overlap)}, New cross-attempts: 0"
        })'''

content = content.replace(old_check, new_check)
open('packages/integrity/concurrency_test.py', 'w').write(content)
print('Fixed concurrent test to check NEW cross-attempts')
