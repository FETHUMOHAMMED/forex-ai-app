# Fix consecutive_healthy counter
content = open('packages/integrity/continuous_scanner.py').read()

# The bug: after first healthy scan sets state=RECOVERING,
# consecutive_healthy doesn't increment on subsequent scans because
# the condition checks self.state == "HALT" but state is now RECOVERING

old = '''        if decision == "READY":
            # Check if we're in recovery mode
            if self.state == "HALT" and self.consecutive_healthy < self.recovery_required:
                self.consecutive_healthy += 1
                remaining = self.recovery_required - self.consecutive_healthy
                print(f"  [RECOVERY] Healthy scan {self.consecutive_healthy}/{self.recovery_required} "
                      f"({remaining} more needed before READY)")
                if self.consecutive_healthy >= self.recovery_required:
                    self.state = "READY"
                    print(f"  [RECOVERED] {self.recovery_required} consecutive healthy scans - READY")
                else:
                    self.state = "RECOVERING"
            else:
                self.state = "READY"
            self.consecutive_failures = 0'''

new = '''        if decision == "READY":
            # Check if we're in recovery mode (was HALT or RECOVERING)
            if self.state in ("HALT", "RECOVERING"):
                self.consecutive_healthy += 1
                remaining = self.recovery_required - self.consecutive_healthy
                print(f"  [RECOVERY] Healthy scan {self.consecutive_healthy}/{self.recovery_required} "
                      f"({remaining} more needed before READY)")
                if self.consecutive_healthy >= self.recovery_required:
                    self.state = "READY"
                    print(f"  [RECOVERED] {self.recovery_required} consecutive healthy scans - READY")
                else:
                    self.state = "RECOVERING"
            else:
                self.state = "READY"
                self.consecutive_healthy = self.recovery_required
            self.consecutive_failures = 0'''

content = content.replace(old, new)
open('packages/integrity/continuous_scanner.py', 'w').write(content)
print('Fixed recovery logic - now requires exactly 3 healthy scans')
